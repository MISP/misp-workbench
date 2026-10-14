"""External dynamic lists (EDLs): what firewalls and proxies fetch.

Palo Alto, Fortinet, Check Point, Cisco and Squid fetch a plain-text list
of IPs, domains, URLs or hashes from a URL on a schedule, and usually can't
send an Authorization header. An EDL is one detection profile's values of
one kind, written the way a vendor reads them:

- **built**, not queried per request: every ``refresh_minutes`` into
  storage, served from there with its sha256 as ETag. A build is a run of
  the profile, so an approval gate's held changes stay out (profile_gate);
- **capped** at the vendor's size limit (or the list's own), keeping the
  highest scored indicators;
- **served at /edl/{token}**: each token is for one list only, read-only,
  revocable, optionally expiring and limited to addresses. Only its sha256
  is stored, and every use is audited.
"""

import hashlib
import ipaddress
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.models import edl as edl_models
from app.schemas import edl as edl_schemas

logger = logging.getLogger(__name__)

TOKEN_PREFIX = "edl_"
PREVIEW_LINES = 50
REFRESH_LOCK = "edls:refresh:lock"

# Indicator types each kind of list takes. A composite one (ip-dst|port,
# domain|ip, filename|md5) gives the part the list wants.
LIST_TYPES = {
    "ip": ["ip-src", "ip-dst", "ip-src|port", "ip-dst|port", "domain|ip"],
    "domain": ["domain", "hostname", "domain|ip"],
    "url": ["url"],
    "hash": [
        "md5",
        "sha1",
        "sha256",
        "filename|md5",
        "filename|sha1",
        "filename|sha256",
    ],
}

# What each vendor fetches, and its size limit by default.
VENDORS = {
    "paloalto": {
        "name": "Palo Alto Networks PAN-OS",
        "list_types": ["ip", "domain", "url"],
        "max_entries": 50_000,
    },
    "fortinet": {
        "name": "Fortinet FortiGate threat feed",
        "list_types": ["ip", "domain", "url", "hash"],
        # 128 x 1024 lines per external resource.
        "max_entries": 131_072,
    },
    "checkpoint": {
        "name": "Check Point network feed",
        "list_types": ["ip", "domain"],
        "max_entries": None,
    },
    "cisco": {
        "name": "Cisco Secure Firewall security intelligence feed",
        "list_types": ["ip", "domain", "url"],
        "max_entries": None,
    },
    "squid": {
        "name": "Squid ACL file",
        "list_types": ["ip", "domain", "url"],
        "max_entries": None,
    },
    "plain": {
        "name": "Plain list, one value per line",
        "list_types": ["ip", "domain", "url", "hash"],
        "max_entries": None,
    },
}

# PAN-OS reads * and ^ in a URL list as wildcards, and refuses longer entries.
PANOS_URL_MAX = 255
HASH_LENGTHS = (32, 40, 64)
_HEX = re.compile(r"^[0-9a-f]+$")
_LABEL = re.compile(r"^(?!-)[a-z0-9_-]{1,63}(?<!-)$")
# POSIX extended regex metacharacters, escaped for Squid's url_regex.
_ERE_SPECIAL = set(".[]()*+?{}|^$\\")


class EdlNotFound(Exception):
    pass


# ── Vendor formats ────────────────────────────────────────────────────────


def _part(list_type: str, type_: str, value: str) -> str:
    """The part of a (composite) value a list wants."""
    if "|" not in type_:
        return value
    first, _, second = value.partition("|")
    if type_ == "domain|ip":
        return second if list_type == "ip" else first
    if type_.startswith("filename|"):
        return second
    # ip-dst|port, ip-src|port
    return first


def _ip(value: str) -> Optional[str]:
    try:
        network = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError:
        return None
    if network.prefixlen == network.max_prefixlen:
        return str(network.network_address)
    return str(network)


def _domain(value: str) -> Optional[str]:
    domain = value.strip().lower().rstrip(".")
    if domain.startswith("*."):
        domain = domain[2:]
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = domain.split(".")
    if len(domain) > 253 or len(labels) < 2:
        return None
    if not all(_LABEL.match(label) for label in labels):
        return None
    # A bare address isn't a domain.
    if _ip(domain):
        return None
    return domain


def _url(value: str) -> Optional[tuple[str, str]]:
    """``(scheme, the rest)`` of a URL: host lowercased, fragment dropped,
    a path of at least ``/``."""
    raw = value.strip()
    if not raw or any(c.isspace() for c in raw):
        return None
    if "://" not in raw:
        raw = f"http://{raw}"
    try:
        parts = urlsplit(raw)
        host = parts.hostname
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not host:
        return None
    netloc = host.lower() + (f":{port}" if port else "")
    rest = netloc + (parts.path or "/")
    if parts.query:
        rest += f"?{parts.query}"
    return parts.scheme.lower(), rest


def _hash(value: str) -> Optional[str]:
    digest = value.strip().lower()
    if len(digest) in HASH_LENGTHS and _HEX.match(digest):
        return digest
    return None


def _ere_escape(text: str) -> str:
    return "".join(f"\\{c}" if c in _ERE_SPECIAL else c for c in text)


def entries(
    vendor: str, list_type: str, type_: str, value: str, include_subdomains: bool
) -> list[str]:
    """The lines one indicator becomes in a vendor's list (none when the
    vendor can't take it)."""
    raw = _part(list_type, type_ or "", str(value or ""))
    if list_type == "ip":
        ip = _ip(raw)
        return [ip] if ip else []
    if list_type == "hash":
        digest = _hash(raw)
        return [digest] if digest else []
    if list_type == "domain":
        domain = _domain(raw)
        if not domain:
            return []
        if vendor == "squid":
            # dstdomain: a leading dot covers the domain and its subdomains.
            return [f".{domain}" if include_subdomains else domain]
        if include_subdomains and vendor in ("fortinet", "plain"):
            return [domain, f"*.{domain}"]
        # PAN-OS covers subdomains with its list's own setting.
        return [domain]
    url = _url(raw)
    if not url:
        return []
    scheme, rest = url
    if vendor == "paloalto":
        if any(c in rest for c in "*^") or len(rest) > PANOS_URL_MAX:
            return []
        return [rest]
    if vendor == "fortinet":
        return [rest]
    if vendor == "squid":
        return [f"^https?://{_ere_escape(rest)}"]
    return [f"{scheme}://{rest}"]


def limit_of(edl) -> int:
    return (
        edl.max_entries or VENDORS[edl.vendor]["max_entries"] or edl_schemas.MAX_ENTRIES
    )


def vendors() -> list[dict]:
    return [{"vendor": key, **info} for key, info in VENDORS.items()]


# ── Visibility and CRUD ───────────────────────────────────────────────────


def sees_all(user) -> bool:
    """Admins see and manage every organisation's lists."""
    return "*" in list(getattr(getattr(user, "role", None), "scopes", None) or [])


def visible(db: Session, user) -> list:
    query = db.query(edl_models.Edl)
    if not sees_all(user):
        query = query.filter(edl_models.Edl.org_id == user.org_id)
    return query.order_by(edl_models.Edl.name).all()


def get_edl(db: Session, user, edl_id: int):
    edl = db.get(edl_models.Edl, edl_id)
    if edl is None or not (sees_all(user) or edl.org_id == user.org_id):
        raise EdlNotFound(edl_id)
    return edl


def _now() -> datetime:
    return datetime.now(timezone.utc)


def active(token, now: Optional[datetime] = None) -> bool:
    now = now or _now()
    return token.revoked_at is None and (
        token.expires_at is None or _aware(token.expires_at) > now
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def active_tokens(db: Session, edl_ids: list[int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    now = _now()
    for token in db.query(edl_models.EdlToken).filter(
        edl_models.EdlToken.edl_id.in_(edl_ids or [-1])
    ):
        if active(token, now):
            counts[token.edl_id] = counts.get(token.edl_id, 0) + 1
    return counts


def check_profile(db: Session, profile_id: int) -> None:
    from app.repositories import detection_profiles

    if detection_profiles.get_profile(db, profile_id) is None:
        raise ValueError(f"No detection profile {profile_id}")


def create_edl(db: Session, data: edl_schemas.EdlCreate, user):
    check_profile(db, data.profile_id)
    edl = edl_models.Edl(
        **data.model_dump(),
        org_id=user.org_id,
        created_by=user.id,
        created_at=_now(),
    )
    db.add(edl)
    db.commit()
    db.refresh(edl)
    return edl


def update_edl(db: Session, edl, data: edl_schemas.EdlUpdate):
    patch = data.model_dump(exclude_unset=True)
    for key in ("name", "profile_id", "list_type", "vendor", "refresh_minutes"):
        if key in patch and patch[key] is None:
            raise ValueError(f"{key} can't be empty")
    edl_schemas.check_vendor(
        patch.get("vendor", edl.vendor), patch.get("list_type", edl.list_type)
    )
    if "profile_id" in patch:
        check_profile(db, patch["profile_id"])
    for key, value in patch.items():
        setattr(edl, key, value)
    edl.updated_at = _now()
    db.commit()
    db.refresh(edl)
    return edl


def delete_edl(db: Session, edl) -> None:
    from app.services.exports_storage import delete_export

    if edl.storage_key:
        try:
            delete_export(edl.storage_key)
        except Exception:
            logger.warning("could not delete EDL %s's artifact", edl.id, exc_info=True)
    db.delete(edl)
    db.commit()


def using_profile(db: Session, profile_id: int) -> list:
    return (
        db.query(edl_models.Edl)
        .filter(edl_models.Edl.profile_id == profile_id)
        .order_by(edl_models.Edl.name)
        .all()
    )


# ── Building ──────────────────────────────────────────────────────────────


SCORE_ORDER = [
    {"score": {"order": "desc", "missing": "_last"}},
    {"uuid.keyword": "asc"},
]


def _hits(edl) -> Iterator[list[dict]]:
    """The profile's released indicators of the list's types, best scored
    first. Preparing the export releases the profile's changes (a run)."""
    from app.repositories import detection_profiles, stream_exports

    profile = detection_profiles.load(edl.profile_id)
    export = stream_exports.prepare_attribute_export(
        "*", "ndjson", index=stream_exports.INDICATORS_INDEX, profile=profile
    )
    query = {
        "bool": {
            "filter": [
                export.query,
                {"terms": {"type.keyword": LIST_TYPES[edl.list_type]}},
            ]
        }
    }
    pages = stream_exports.iter_pit_pages(
        export.client,
        stream_exports.INDICATORS_INDEX,
        query,
        source=["type", "value", "score"],
        sort=SCORE_ORDER,
    )
    return stream_exports._released_pages(export, pages)


def render(edl, pages: Iterator[list[dict]]) -> tuple[list[str], int]:
    """The list's lines, each once, up to its limit; and how many more
    there were."""
    limit = limit_of(edl)
    lines: list[str] = []
    seen: set = set()
    truncated = 0
    for hits in pages:
        for hit in hits:
            source = hit.get("_source", hit)
            for line in entries(
                edl.vendor,
                edl.list_type,
                source.get("type"),
                source.get("value"),
                edl.include_subdomains,
            ):
                if line in seen:
                    continue
                seen.add(line)
                if len(lines) < limit:
                    lines.append(line)
                else:
                    truncated += 1
    return lines, truncated


def build(db: Session, edl) -> None:
    """Rebuild a list into storage; a failure is recorded on it, and the
    last good list keeps being served."""
    from app.services.exports_storage import store_export

    try:
        lines, truncated = render(edl, _hits(edl))
        content = "".join(f"{line}\n" for line in lines).encode("utf-8")
        edl.storage_key = store_export(f"edl-{edl.id}.txt", content)
        edl.checksum = hashlib.sha256(content).hexdigest()
        edl.entry_count = len(lines)
        edl.truncated = truncated
        edl.build_error = None
    except Exception as error:
        logger.exception("EDL %s failed to build", edl.id)
        db.rollback()
        edl = db.get(edl_models.Edl, edl.id)
        if edl is None:
            return
        edl.build_error = str(error) or error.__class__.__name__
    edl.built_at = _now()
    db.commit()
    if edl.truncated:
        logger.info(
            "EDL %s holds %s entries; %s lower scored ones left out",
            edl.id,
            edl.entry_count,
            edl.truncated,
        )


def due(db: Session, now: Optional[datetime] = None) -> list:
    now = now or _now()
    return [
        edl
        for edl in db.query(edl_models.Edl).filter(edl_models.Edl.enabled.is_(True))
        if edl.built_at is None
        or _aware(edl.built_at) + timedelta(minutes=edl.refresh_minutes) <= now
    ]


def refresh_due(db: Session) -> int:
    """Rebuild the lists due, one run at a time."""
    from app.services.redis import get_redis_client

    redis = get_redis_client()
    if not redis.set(REFRESH_LOCK, "1", nx=True, ex=3600):
        return 0
    try:
        built = 0
        for edl in due(db):
            build(db, edl)
            built += 1
        return built
    finally:
        redis.delete(REFRESH_LOCK)


def preview(edl) -> dict:
    from app.repositories.profile_membership import lines_of
    from app.services.exports_storage import open_export

    lines: list[str] = []
    if edl.storage_key and edl.entry_count:
        chunks = open_export(edl.storage_key)
        try:
            for line in lines_of(chunks):
                lines.append(line.decode("utf-8"))
                if len(lines) >= PREVIEW_LINES:
                    break
        finally:
            close = getattr(chunks, "close", None)
            if close:
                close()
    return {
        "lines": lines,
        "entry_count": edl.entry_count or 0,
        "truncated": edl.truncated or 0,
        "built_at": edl.built_at,
    }


# ── Tokens ────────────────────────────────────────────────────────────────


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(db: Session, edl, data: edl_schemas.EdlTokenCreate, user):
    """A new token for one list; returns it with its value, shown once."""
    value = TOKEN_PREFIX + secrets.token_urlsafe(32)
    token = edl_models.EdlToken(
        edl_id=edl.id,
        name=data.name,
        prefix=value[: len(TOKEN_PREFIX) + 8],
        token_hash=hash_token(value),
        allowed_ips=data.allowed_ips,
        expires_at=data.expires_at,
        created_by=user.id,
        created_at=_now(),
    )
    db.add(token)
    db.flush()
    return token, value


def tokens_of(db: Session, edl) -> list:
    return (
        db.query(edl_models.EdlToken)
        .filter(edl_models.EdlToken.edl_id == edl.id)
        .order_by(edl_models.EdlToken.created_at.desc())
        .all()
    )


def get_token(db: Session, edl, token_id: int):
    token = db.get(edl_models.EdlToken, token_id)
    if token is None or token.edl_id != edl.id:
        raise EdlNotFound(token_id)
    return token


def revoke_token(db: Session, token) -> None:
    if token.revoked_at is None:
        token.revoked_at = _now()


def find_token(db: Session, value: str):
    """The token row for a presented token, or None."""
    if not value.startswith(TOKEN_PREFIX) or len(value) > 128:
        return None
    return (
        db.query(edl_models.EdlToken)
        .filter(edl_models.EdlToken.token_hash == hash_token(value))
        .first()
    )


def refused(token, ip: Optional[str], now: Optional[datetime] = None) -> Optional[str]:
    """Why a token can't fetch its list now (revoked, expired, address),
    or None."""
    now = now or _now()
    if token.revoked_at is not None:
        return "revoked"
    if token.expires_at is not None and _aware(token.expires_at) <= now:
        return "expired"
    if token.allowed_ips:
        try:
            address = ipaddress.ip_address(ip or "")
        except ValueError:
            return "address"
        if not any(
            address in ipaddress.ip_network(network, strict=False)
            for network in token.allowed_ips
        ):
            return "address"
    return None


def record_use(token, ip: Optional[str]) -> None:
    token.last_used_at = _now()
    token.last_used_ip = ip
    token.use_count = (token.use_count or 0) + 1
