"""Sinks for platforms that take threat intel through their own APIs only.

- Microsoft Sentinel: STIX indicators through the upload API.
- Microsoft Defender for Endpoint: custom indicators through the import API.
- Elastic Security: ECS ``threat.indicator.*`` documents bulk-indexed into an
  index of your own, for indicator match rules.

Each turns records (see ``formatters``) into the vendor's objects. A record
with ``action: remove`` (membership sync) takes the value out: Sentinel
indicators are expired, Defender's and Elastic's deleted.

Values come from feeds, and on these platforms an indicator can block, so the
same limits as the detection formats hold: no network broader than a /16,
no special-purpose address, no public suffix (see ``detection_formats``).
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

import requests

from app.services.exports import detection_formats
from app.services.sinks.transports import (
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
    USER_AGENT,
    SinkDeliveryError,
    _HttpVerify,
)

logger = logging.getLogger(__name__)

# Ids of the objects a value becomes, the same from one delivery to the next,
# so a re-send updates the object rather than adding another.
ID_NAMESPACE = uuid.UUID("5d0b2c7e-6f0a-4a43-9a8e-4c1e5b0b6f2a")

# Throttled requests are retried after the wait the API asks for, this many
# times and for at most this long each, before the delivery fails (and the
# delivery task retries it with backoff).
MAX_ATTEMPTS = 4
MAX_WAIT_SECONDS = 60

SENTINEL_BATCH = 100
DEFENDER_BATCH = 500
ELASTIC_BATCH = 500

_HEX = re.compile(r"^[0-9a-fA-F]+$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+$")
_HASHES = {"md5": 32, "sha1": 40, "sha256": 64}


# ── What a record turns into ────────────────────────────────────────────────


def observables(record: dict, single_addresses: bool = False) -> list[tuple]:
    """``(kind, value)`` for each value in a record a vendor can hold.

    Kinds: ipv4, ipv6, domain, url, md5, sha1, sha256, email, filename,
    x509-sha1. Composite types (``domain|ip``, ``filename|sha256``) give one
    per part. ``single_addresses`` leaves networks out, for vendors that
    take addresses only.
    """
    found = []
    for type_, value in detection_formats.parts(
        record.get("type") or "", str(record.get("value") or "")
    ):
        value = value.strip()
        if type_ in ("ip-src", "ip-dst"):
            net = detection_formats.network(value)
            if net is None or (single_addresses and net.num_addresses > 1):
                continue
            address = str(net.network_address if net.num_addresses == 1 else net)
            found.append((f"ipv{net.version}", address))
        elif type_ in ("domain", "hostname"):
            name = detection_formats.target_domain(value)
            if name:
                found.append(("domain", name))
        elif type_ == "url":
            if value and not any(c in value for c in " \t\r\n"):
                found.append(("url", value))
        elif type_ in _HASHES:
            if len(value) == _HASHES[type_] and _HEX.match(value):
                found.append((type_, value.lower()))
        elif type_ in ("email", "email-src", "email-dst", "target-email"):
            if _EMAIL.match(value):
                found.append(("email", value.lower()))
        elif type_ == "filename":
            if value and not any(c in value for c in "\r\n"):
                found.append(("filename", value))
        elif type_ == "x509-fingerprint-sha1":
            value = value.replace(":", "")
            if len(value) == 40 and _HEX.match(value):
                found.append(("x509-sha1", value.lower()))
    return list(dict.fromkeys(found))


def object_id(kind: str, value: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, f"{kind}|{value}"))


def is_removal(record: dict) -> bool:
    return record.get("action") == "remove"


def score(record: dict) -> Optional[int]:
    """The indicator's confidence (0-100), or one from the event's threat
    level when the record carries no indicator."""
    indicator = record.get("indicator") or {}
    if indicator.get("score") is not None:
        return int(indicator["score"])
    level = (record.get("event") or {}).get("threat_level_id")
    return {1: 85, 2: 60, 3: 35, 4: None}.get(level)


def severity(record: dict) -> str:
    """Informational, Low, Medium or High, from the score."""
    value = score(record)
    if value is None:
        return "Informational"
    if value >= 80:
        return "High"
    if value >= 50:
        return "Medium"
    if value >= 20:
        return "Low"
    return "Informational"


def _as_datetime(value) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        pass
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def last_seen(record: dict) -> Optional[datetime]:
    indicator = record.get("indicator") or {}
    return _as_datetime(
        indicator.get("last_seen") or record.get("last_seen") or record.get("timestamp")
    )


def expiry(record: dict, days: int, now: datetime) -> datetime:
    """``days`` after the value was last seen, and at least a day from now:
    a value nobody sees any more drops out on its own, like it decays."""
    seen = last_seen(record) or now
    return max(seen + timedelta(days=days), now + timedelta(days=1))


def _time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _title(record: dict) -> str:
    event = record.get("event") or {}
    return str(event.get("info") or f"MISP {record.get('type')} indicator")[:250]


def _description(record: dict) -> str:
    event = record.get("event") or {}
    indicator = record.get("indicator") or {}
    parts = [f"MISP {record.get('type')}: {record.get('value')}"]
    if event.get("info"):
        parts.append(f"Event: {event['info']}")
    if event.get("uuid"):
        parts.append(f"Event uuid: {event['uuid']}")
    if indicator.get("sources"):
        parts.append("Sources: " + ", ".join(str(s) for s in indicator["sources"]))
    if record.get("comment"):
        parts.append(str(record["comment"]))
    return "\n".join(parts)[:2000]


def _tags(record: dict) -> list[str]:
    event = record.get("event") or {}
    return list(
        dict.fromkeys([*(record.get("tags") or []), *(event.get("tags") or [])])
    )[:50]


def chunks(items: list, size: int) -> Iterator[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


# ── HTTP ────────────────────────────────────────────────────────────────────


def _wait(response: requests.Response, attempt: int) -> float:
    """How long a throttled request asks to wait: Retry-After, or the
    seconds Sentinel's message names, else a backoff."""
    header = response.headers.get("Retry-After")
    if header and header.strip().isdigit():
        return min(float(header), MAX_WAIT_SECONDS)
    match = re.search(r"in (\d+) seconds", response.text[:500])
    if match:
        return min(float(match.group(1)), MAX_WAIT_SECONDS)
    return min(2.0**attempt, MAX_WAIT_SECONDS)


def request(
    method: str,
    url: str,
    what: str,
    verify,
    *,
    ok: tuple = (200, 201, 202, 204),
    **kwargs,
) -> requests.Response:
    """One API call, retried while it is throttled (429, 503).

    Failures report the status only: the body is the endpoint's, and echoing
    it would let a sink be used to read whatever its URL points at.
    """
    headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                verify=verify,
                # A redirect would re-send the token (or the client secret)
                # wherever the endpoint points.
                allow_redirects=False,
                **kwargs,
            )
        except requests.RequestException as error:
            raise SinkDeliveryError(f"{what} request failed: {error}") from error
        if response.status_code in (429, 503) and attempt < MAX_ATTEMPTS:
            time.sleep(_wait(response, attempt))
            continue
        if response.status_code not in ok:
            raise SinkDeliveryError(f"{what} answered HTTP {response.status_code}")
        return response
    raise AssertionError("unreachable")


def _json(response: requests.Response, what: str):
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        raise SinkDeliveryError(f"{what} answered with something other than JSON")


class EntraToken:
    """An app-only Microsoft Entra ID token (OAuth2 client credentials),
    fetched on first use and kept for the transport's lifetime."""

    def __init__(self, config: dict, verify):
        self.config = config
        self.verify = verify
        self._token: Optional[str] = None
        self._expires = 0.0

    def __call__(self) -> str:
        if self._token is None or time.time() > self._expires - 60:
            config = self.config
            response = request(
                "POST",
                f"{config['login_url'].rstrip('/')}/{config['tenant_id']}"
                "/oauth2/v2.0/token",
                "Microsoft Entra token request",
                self.verify,
                ok=(200,),
                data={
                    "grant_type": "client_credentials",
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "scope": config["scope"],
                },
            )
            body = _json(response, "Microsoft Entra token request")
            if not body.get("access_token"):
                raise SinkDeliveryError("Microsoft Entra answered without a token")
            self._token = body["access_token"]
            self._expires = time.time() + float(body.get("expires_in") or 3600)
        return self._token

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self()}"}


def _rejected(what: str, rejected: int, total: int, reasons: list) -> None:
    if rejected:
        detail = f": {'; '.join(reasons[:3])}" if reasons else ""
        raise SinkDeliveryError(
            f"{what} rejected {rejected} of {total} indicators{detail}"
        )


# ── Microsoft Sentinel ──────────────────────────────────────────────────────

_STIX_PATTERNS = {
    "ipv4": "ipv4-addr:value",
    "ipv6": "ipv6-addr:value",
    "domain": "domain-name:value",
    "url": "url:value",
    "email": "email-addr:value",
    "md5": "file:hashes.'MD5'",
    "sha1": "file:hashes.'SHA-1'",
    "sha256": "file:hashes.'SHA-256'",
    "filename": "file:name",
    "x509-sha1": "x509-certificate:hashes.'SHA-1'",
}

# STIX 2.1 TLP marking definitions.
TLP_MARKINGS = {
    "tlp:clear": "marking-definition--613f2e26-407d-48c7-9eca-b8e91df99dc9",
    "tlp:white": "marking-definition--613f2e26-407d-48c7-9eca-b8e91df99dc9",
    "tlp:green": "marking-definition--34098fce-860f-48ae-8e50-ebd3cc5e41da",
    "tlp:amber": "marking-definition--f88d31f6-486f-44da-b317-01333bde0b82",
    "tlp:amber+strict": "marking-definition--826578e1-40ad-459f-bc73-ede076f81f37",
    "tlp:red": "marking-definition--5e57c739-391a-4eb3-b6be-7d15ca92d5ed",
}


def stix_pattern(kind: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"[{_STIX_PATTERNS[kind]} = '{escaped}']"


def _tlp(record: dict) -> Optional[str]:
    indicator = record.get("indicator") or {}
    if indicator.get("tlp"):
        return str(indicator["tlp"]).lower()
    tags = [t.lower() for t in _tags(record)]
    found = [t for t in TLP_MARKINGS if t in tags]
    return found[-1] if found else None


def stix_indicators(record: dict, config: dict, now: datetime) -> list[dict]:
    """The STIX 2.1 indicators of a record. A removal is the same indicator,
    expired now: revoking one is permanent in STIX, and the value may come
    back."""
    objects = []
    for kind, value in observables(record):
        stix = {
            "type": "indicator",
            "spec_version": "2.1",
            "id": f"indicator--{object_id(kind, value)}",
            "pattern": stix_pattern(kind, value),
            "pattern_type": "stix",
            "pattern_version": "2.1",
            "modified": _time(now),
            "name": f"{kind} {value}"[:250],
        }
        if is_removal(record):
            stix.update(
                {
                    "created": _time(now - timedelta(minutes=1)),
                    "valid_from": _time(now - timedelta(minutes=1)),
                    "valid_until": _time(now),
                    "description": f"Removed: {record.get('reason') or 'left'}",
                }
            )
            objects.append(stix)
            continue
        seen = _as_datetime(
            (record.get("indicator") or {}).get("first_seen")
            or record.get("first_seen")
            or record.get("timestamp")
        )
        valid_from = min(seen or now, now)
        confidence = score(record)
        stix.update(
            {
                "created": _time(valid_from),
                "valid_from": _time(valid_from),
                "valid_until": _time(expiry(record, config["valid_days"], now)),
                "description": _description(record),
                "indicator_types": ["malicious-activity"],
                "labels": _tags(record),
                "external_references": [
                    {
                        "source_name": "misp-workbench",
                        "external_id": record.get("uuid") or "",
                    }
                ],
            }
        )
        if confidence is not None:
            stix["confidence"] = confidence
        tlp = _tlp(record)
        if tlp in TLP_MARKINGS:
            stix["object_marking_refs"] = [TLP_MARKINGS[tlp]]
        objects.append(stix)
    return objects


class SentinelTransport:
    """Microsoft Sentinel's upload API: STIX indicators, 100 a request."""

    what = "Microsoft Sentinel"

    def __init__(self, config: dict, now=None):
        self.config = config
        self.verify = _HttpVerify(config)
        self.token = EntraToken(config, self.verify.value)
        self.now = now or (lambda: datetime.now(timezone.utc))

    def _url(self) -> str:
        return (
            f"{self.config['api_url'].rstrip('/')}/workspaces/"
            f"{self.config['workspace_id']}/threat-intelligence-stix-objects:upload"
        )

    def send(self, records: list[dict]) -> None:
        now = self.now()
        objects = [o for r in records for o in stix_indicators(r, self.config, now)]
        rejected, reasons = 0, []
        for batch in chunks(objects, SENTINEL_BATCH):
            response = request(
                "POST",
                self._url(),
                self.what,
                self.verify.value,
                ok=(200,),
                params={"api-version": self.config["api_version"]},
                headers={**self.token.headers(), "Content-Type": "application/json"},
                data=json.dumps(
                    {
                        "sourcesystem": self.config["source_system"],
                        "stixobjects": batch,
                    }
                ),
            )
            # Validation errors come back in a 200, one per object refused.
            errors = _json(response, self.what).get("errors") or []
            rejected += len(errors)
            reasons += [
                f"{batch[e['recordIndex']]['name']}: {(e.get('errorMessages') or ['?'])[0]}"[
                    :200
                ]
                for e in errors
                if isinstance(e.get("recordIndex"), int)
                and 0 <= e["recordIndex"] < len(batch)
            ]
        _rejected(self.what, rejected, len(objects), reasons)

    def check(self) -> None:
        """The credentials work: Entra issues a token for the API."""
        self.token()

    def close(self) -> None:
        self.verify.close()


# ── Microsoft Defender for Endpoint ─────────────────────────────────────────

_DEFENDER_TYPES = {
    "ipv4": "IpAddress",
    "ipv6": "IpAddress",
    "domain": "DomainName",
    "url": "Url",
    "md5": "FileMd5",
    "sha1": "FileSha1",
    "sha256": "FileSha256",
    "x509-sha1": "CertificateThumbprint",
}
_FILE_TYPES = ("FileMd5", "FileSha1", "FileSha256")


def defender_indicators(record: dict, config: dict, now: datetime) -> list[dict]:
    """Defender's indicators of a record (to import; not for removals).

    Defender takes single, public addresses only: no CIDR, and a private
    address would match every network's own hosts.
    """
    action = config["action"]
    found = []
    for kind, value in observables(record, single_addresses=True):
        type_ = _DEFENDER_TYPES.get(kind)
        if type_ is None:
            continue
        if type_ == "IpAddress":
            net = detection_formats.network(value)
            if net is None or not net.network_address.is_global:
                continue
        if action == "block":
            vendor_action = "BlockAndRemediate" if type_ in _FILE_TYPES else "Block"
        else:
            vendor_action = "Audit"
        indicator = {
            "indicatorValue": value,
            "indicatorType": type_,
            "action": vendor_action,
            "generateAlert": action != "audit",
            "title": _title(record),
            "description": _description(record),
            "application": config["application"],
            "severity": severity(record),
            "expirationTime": _time(expiry(record, config["expiry_days"], now)),
            "recommendedActions": "",
            "rbacGroupNames": list(config.get("rbac_group_names") or []),
        }
        found.append(indicator)
    return found


class DefenderTransport:
    """Defender for Endpoint's indicators: imported 500 a call; removals
    deleted by id, looking up only the indicators this sink's application
    created."""

    what = "Microsoft Defender"

    def __init__(self, config: dict, now=None):
        self.config = config
        self.verify = _HttpVerify(config)
        self.token = EntraToken(config, self.verify.value)
        self.now = now or (lambda: datetime.now(timezone.utc))
        # value -> ids of this application's indicators, read on the first
        # removal of a delivery.
        self._ours: Optional[dict] = None

    def _api(self, path: str) -> str:
        return f"{self.config['api_url'].rstrip('/')}/api/{path}"

    def send(self, records: list[dict]) -> None:
        now = self.now()
        adds = [
            i
            for r in records
            if not is_removal(r)
            for i in defender_indicators(r, self.config, now)
        ]
        removals = {
            value
            for r in records
            if is_removal(r)
            for _, value in observables(r, single_addresses=True)
        }
        rejected, reasons = 0, []
        for batch in chunks(adds, DEFENDER_BATCH):
            response = request(
                "POST",
                self._api("indicators/import"),
                self.what,
                self.verify.value,
                ok=(200,),
                headers={**self.token.headers(), "Content-Type": "application/json"},
                data=json.dumps({"Indicators": batch}),
            )
            results = _json(response, self.what).get("value") or []
            failed = [r for r in results if r.get("isFailed")]
            rejected += len(failed)
            reasons += [
                f"{r.get('indicator')}: {r.get('failureReason')}"[:200] for r in failed
            ]
        _rejected(self.what, rejected, len(adds), reasons)
        if removals:
            self._delete(removals)

    def _our_indicators(self) -> dict:
        if self._ours is None:
            ours: dict = {}
            skip = 0
            application = self.config["application"].replace("'", "''")
            while True:
                response = request(
                    "GET",
                    self._api("indicators"),
                    self.what,
                    self.verify.value,
                    ok=(200,),
                    headers=self.token.headers(),
                    params={
                        "$filter": f"application eq '{application}'",
                        "$top": 10000,
                        "$skip": skip,
                    },
                )
                page = _json(response, self.what).get("value") or []
                for indicator in page:
                    value = str(indicator.get("indicatorValue") or "").lower()
                    ours.setdefault(value, []).append(str(indicator.get("id")))
                if len(page) < 10000:
                    break
                skip += len(page)
            self._ours = ours
        return self._ours

    def _delete(self, values: set) -> None:
        ours = self._our_indicators()
        ids = [i for v in sorted(values) for i in ours.pop(v.lower(), [])]
        for batch in chunks(ids, DEFENDER_BATCH):
            # 404: one of them is gone already (expired, deleted by hand).
            request(
                "POST",
                self._api("indicators/BatchDelete"),
                self.what,
                self.verify.value,
                ok=(200, 204, 404),
                headers={**self.token.headers(), "Content-Type": "application/json"},
                data=json.dumps({"IndicatorIds": batch}),
            )

    def check(self) -> None:
        """The credentials work and may read indicators."""
        request(
            "GET",
            self._api("indicators"),
            self.what,
            self.verify.value,
            ok=(200,),
            headers=self.token.headers(),
            params={"$top": 1},
        )

    def close(self) -> None:
        self.verify.close()


# ── Elastic Security ────────────────────────────────────────────────────────

_ECS_TYPES = {
    "ipv4": "ipv4-addr",
    "ipv6": "ipv6-addr",
    "domain": "domain-name",
    "url": "url",
    "email": "email-addr",
    "md5": "file",
    "sha1": "file",
    "sha256": "file",
    "filename": "file",
}


def _confidence_name(record: dict) -> str:
    value = score(record)
    if value is None:
        return "Not Specified"
    if value >= 70:
        return "High"
    if value >= 30:
        return "Medium"
    if value > 0:
        return "Low"
    return "None"


def ecs_indicator(kind: str, value: str, record: dict, now: datetime) -> dict:
    """An ECS ``threat.indicator`` document, as Elastic's threat intel
    integrations write them, so indicator match rules can use it."""
    indicator: dict = {
        "type": _ECS_TYPES[kind],
        "description": _description(record),
        "confidence": _confidence_name(record),
        "provider": ((record.get("indicator") or {}).get("sources") or [None])[0]
        or (record.get("event") or {}).get("org")
        or "misp-workbench",
        "modified_at": _time(now),
    }
    if kind in ("ipv4", "ipv6"):
        indicator["ip"] = value
    elif kind == "domain":
        indicator["url"] = {"domain": value}
    elif kind == "url":
        indicator["url"] = {"full": value, "original": value}
    elif kind == "email":
        indicator["email"] = {"address": value}
    elif kind in _HASHES:
        indicator["file"] = {"hash": {kind: value}}
    elif kind == "filename":
        indicator["file"] = {"name": value}
    first = _as_datetime(
        (record.get("indicator") or {}).get("first_seen") or record.get("first_seen")
    )
    seen = last_seen(record)
    if first:
        indicator["first_seen"] = _time(first)
    if seen:
        indicator["last_seen"] = _time(seen)
    tlp = _tlp(record)
    if tlp:
        indicator["marking"] = {"tlp": tlp.split(":", 1)[1].upper()}
    score_value = score(record)
    event = record.get("event") or {}
    return {
        "@timestamp": _time(now),
        "event": {
            "kind": "enrichment",
            "category": ["threat"],
            "type": ["indicator"],
            "dataset": "misp_workbench.indicator",
            **({"risk_score": score_value} if score_value is not None else {}),
        },
        "threat": {
            "feed": {"name": "misp-workbench"},
            "indicator": indicator,
        },
        "tags": _tags(record),
        "misp": {
            "type": record.get("type"),
            "uuid": record.get("uuid"),
            "event": {"uuid": event.get("uuid"), "info": event.get("info")},
        },
    }


_KEYWORD = {"type": "keyword"}
_DATE = {"type": "date"}

# The ECS types of the fields written, for an index this sink creates.
# Indicator match rules compare an event's fields with these, so an address
# must be an ip (dynamic mapping would make it text).
ECS_MAPPINGS = {
    "dynamic": True,
    "properties": {
        "@timestamp": _DATE,
        "tags": _KEYWORD,
        "event": {
            "properties": {
                "kind": _KEYWORD,
                "category": _KEYWORD,
                "type": _KEYWORD,
                "dataset": _KEYWORD,
                "risk_score": {"type": "float"},
            }
        },
        "threat": {
            "properties": {
                "feed": {"properties": {"name": _KEYWORD}},
                "indicator": {
                    "properties": {
                        "type": _KEYWORD,
                        "ip": {"type": "ip"},
                        "url": {
                            "properties": {
                                "domain": _KEYWORD,
                                "full": _KEYWORD,
                                "original": _KEYWORD,
                            }
                        },
                        "email": {"properties": {"address": _KEYWORD}},
                        "file": {
                            "properties": {
                                "name": _KEYWORD,
                                "hash": {
                                    "properties": {
                                        "md5": _KEYWORD,
                                        "sha1": _KEYWORD,
                                        "sha256": _KEYWORD,
                                    }
                                },
                            }
                        },
                        "confidence": _KEYWORD,
                        "provider": _KEYWORD,
                        "description": {"type": "text"},
                        "marking": {"properties": {"tlp": _KEYWORD}},
                        "first_seen": _DATE,
                        "last_seen": _DATE,
                        "modified_at": _DATE,
                    }
                },
            }
        },
        "misp": {
            "properties": {
                "type": _KEYWORD,
                "uuid": _KEYWORD,
                "event": {"properties": {"uuid": _KEYWORD, "info": {"type": "text"}}},
            }
        },
    },
}


def elastic_bulk_body(records: list[dict], index: str, now: datetime) -> str:
    lines = []
    for record in records:
        for kind, value in observables(record, single_addresses=True):
            # ECS has no certificate fingerprint indicator match could use.
            if kind not in _ECS_TYPES:
                continue
            meta = {"_index": index, "_id": object_id(kind, value)}
            if is_removal(record):
                lines.append(json.dumps({"delete": meta}))
            else:
                lines.append(json.dumps({"index": meta}))
                lines.append(
                    json.dumps(ecs_indicator(kind, value, record, now), default=str)
                )
    return "".join(f"{line}\n" for line in lines)


class ElasticTransport:
    """Bulk-indexes ECS indicator documents; removals delete them."""

    what = "Elasticsearch"

    def __init__(self, config: dict, now=None):
        self.config = config
        self.verify = _HttpVerify(config)
        self.now = now or (lambda: datetime.now(timezone.utc))
        self._index_ready = False

    def _headers(self) -> dict:
        if self.config.get("api_key"):
            return {"Authorization": f"ApiKey {self.config['api_key']}"}
        return {}

    def _auth(self):
        if not self.config.get("api_key") and self.config.get("username"):
            return (self.config["username"], self.config.get("password") or "")
        return None

    def _index_url(self) -> str:
        return f"{self.config['url'].rstrip('/')}/{self.config['index']}"

    def _ensure_index(self) -> None:
        """Create the index with ECS types if it doesn't exist yet. One that
        does (from your own template, say) is left as it is."""
        if self._index_ready:
            return
        exists = request(
            "HEAD",
            self._index_url(),
            self.what,
            self.verify.value,
            ok=(200, 404),
            headers=self._headers(),
            auth=self._auth(),
        )
        if exists.status_code == 404:
            # 400: created meanwhile, by a concurrent delivery.
            created = request(
                "PUT",
                self._index_url(),
                self.what,
                self.verify.value,
                ok=(200, 400),
                headers={**self._headers(), "Content-Type": "application/json"},
                auth=self._auth(),
                data=json.dumps({"mappings": ECS_MAPPINGS}),
            )
            if created.status_code == 400 and "already_exists" not in created.text:
                raise SinkDeliveryError(f"{self.what} answered HTTP 400")
        self._index_ready = True

    def send(self, records: list[dict]) -> None:
        now = self.now()
        failed, total, reasons = 0, 0, []
        self._ensure_index()
        for batch in chunks(records, ELASTIC_BATCH):
            body = elastic_bulk_body(batch, self.config["index"], now)
            if not body:
                continue
            response = request(
                "POST",
                f"{self.config['url'].rstrip('/')}/_bulk",
                self.what,
                self.verify.value,
                ok=(200,),
                headers={**self._headers(), "Content-Type": "application/x-ndjson"},
                auth=self._auth(),
                data=body.encode("utf-8"),
            )
            result = _json(response, self.what)
            for item in result.get("items") or []:
                (op, outcome), *_ = item.items()
                total += 1
                status = outcome.get("status") or 0
                # Deleting what isn't there is what was asked.
                if status >= 300 and not (op == "delete" and status == 404):
                    failed += 1
                    error = outcome.get("error") or {}
                    reasons.append(str(error.get("type") or status)[:200])
        _rejected(self.what, failed, total, reasons)

    def check(self) -> None:
        """The credentials authenticate."""
        request(
            "GET",
            f"{self.config['url'].rstrip('/')}/_security/_authenticate",
            self.what,
            self.verify.value,
            ok=(200,),
            headers=self._headers(),
            auth=self._auth(),
        )

    def close(self) -> None:
        self.verify.close()


TRANSPORTS = {
    "sentinel": SentinelTransport,
    "defender": DefenderTransport,
    "elastic": ElasticTransport,
}
