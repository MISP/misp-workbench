"""Change preview and approval gate: see what a profile's next run changes,
and keep large or risky changes out of its outputs until approved.

A profile's *runs* are those of the outputs that send its members as a set:
exports and feeds referencing it, and sinks keeping in step with it. A run
only sends what the profile *released* (a member set kept in Redis, like a
sink's, see profile_membership). Before each, ``ready`` compares what the
profile selects now with that, and releases the changes its gate lets
through. What trips the gate is *held*, kept out of the release:

- additions carrying a risk flag the gate holds on: those additions;
- too many additions, or a spike: all of the run's additions;
- too many removals: all of its removals (they stay in the outputs).

The rest goes out, so outputs never go stale over one risky change.
Reviewers are notified; approving releases what was held and runs the
outputs. A hold that no longer applies is lifted.

Every release and hold is recorded (``profile_releases``), with the change
preview at the time, which gives the trend of recent runs. Lookups,
restSearch and sinks sending published events judge one value at a time, as
it comes; they aren't runs and nothing is held from them.
"""

import hashlib
import logging
import re
import statistics
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

from sqlalchemy.orm import Session

from app.models import profile_release as release_models
from app.repositories import detection_profiles, profile_membership
from app.schemas import detection_profile as profile_schemas
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

LOCK_SECONDS = 15 * 60
LOCK_WAIT_SECONDS = 10 * 60
SAMPLE = 10
TOP_SOURCES = 20
# Runs the usual additions are the median of, and the least a spike adds.
SPIKE_HISTORY = 10
SPIKE_MIN = 20
KEEP_RELEASES = 200

# Warninglists by what they say about a value. Matched on list names.
POPULAR = re.compile(
    r"\btop\b|tranco|umbrella|majestic|alexa|crux|1million|most-used", re.I
)
SHARED = re.compile(
    r"cloud|cdn|\baws\b|amazon|azure|akamai|fastly|hosting|datacenter|"
    r"digitalocean|hetzner|\bovh\b|linode|vultr|leaseweb|rackspace|scaleway|"
    r"godaddy|oracle|alibaba|tencent|huawei|\bibm\b|\bgcp\b|github|office 365|"
    r"zscaler|imperva|stackpath|sucuri|bunny|cachefly|cdn77|gcore|coreweave|"
    r"salesforce|ipfs|shortener|link in bio|dynamic dns|parking",
    re.I,
)


class ChangesMoved(Exception):
    """The changes aren't those a reviewer saw: approve them again."""


class GateBusy(Exception):
    """Another run is releasing the profile's changes."""


def baseline_key(profile_id: int) -> str:
    return profile_membership.state_key(f"profile:{profile_id}")


def gate_of(raw) -> profile_schemas.ProfileGate:
    if isinstance(raw, profile_schemas.ProfileGate):
        return raw
    return profile_schemas.ProfileGate.model_validate(raw or {})


@contextmanager
def _lock(profile_id: int, wait_seconds: int) -> Iterator[bool]:
    redis = get_redis_client()
    key = f"{baseline_key(profile_id)}:lock"
    deadline = time.monotonic() + wait_seconds
    while not redis.set(key, "1", nx=True, ex=LOCK_SECONDS):
        if time.monotonic() >= deadline:
            yield False
            return
        time.sleep(1)
    try:
        yield True
    finally:
        redis.delete(key)


# ── The preview ───────────────────────────────────────────────────────────


def new_sources(days: int) -> dict[str, str]:
    """Feeds and servers added less than ``days`` ago: source key -> name."""
    from app.database import SessionLocal
    from app.models import feed as feed_models
    from app.models import server as server_models

    since = datetime.now(timezone.utc) - timedelta(days=days)
    found = {}
    with SessionLocal() as db:
        for kind, model in (
            ("feed", feed_models.Feed),
            ("server", server_models.Server),
        ):
            for row in db.query(model).filter(model.created_at >= since):
                found[f"{kind}:{row.id}"] = row.name
    return found


def risk_flags(
    indicator: dict, gate: profile_schemas.ProfileGate, new: dict[str, str]
) -> list[tuple[str, str]]:
    """Why an addition is risky: (flag, detail) pairs."""
    flags = []
    hits = indicator.get("warninglist_hits") or []
    popular = [h for h in hits if POPULAR.search(h)]
    shared = [h for h in hits if h not in popular and SHARED.search(h)]
    other = [h for h in hits if h not in popular and h not in shared]
    for flag, lists in (
        ("popular_domain", popular),
        ("shared_infrastructure", shared),
        ("warninglisted", other),
    ):
        if lists:
            flags.append((flag, ", ".join(lists)))
    keys = indicator.get("source_keys") or []
    # Reported only by new sources: one an established source also reports
    # isn't new to anyone.
    if keys and all(k in new for k in keys):
        flags.append(("new_source", ", ".join(new[k] for k in keys)))
    score = indicator.get("score")
    if score is not None and score < gate.low_score:
        flags.append(("low_score", f"score {score}"))
    return flags


def _sample(indicator: dict, detail: Optional[str] = None) -> dict:
    return {
        "uuid": indicator.get("uuid"),
        "type": indicator.get("type"),
        "value": indicator.get("value"),
        "score": indicator.get("score"),
        "detail": detail,
    }


def fingerprint(diff) -> str:
    """Which indicators a diff adds and removes, as a digest: approving
    releases those changes only, not ones that came after the preview."""
    redis = get_redis_client()
    digest = hashlib.sha256()
    for label, key in ((b"+", diff.added_key), (b"-", diff.removed_key)):
        members = sorted(
            m.decode() if isinstance(m, bytes) else m
            for m in redis.sscan_iter(key, count=1000)
        )
        digest.update(label)
        for member in members:
            if member != profile_membership.SENTINEL:
                digest.update(member.encode() + b"\n")
    return digest.hexdigest()


def summarise(
    diff, gate: profile_schemas.ProfileGate, flagged: Optional[set] = None
) -> dict:
    """The change preview of a computed diff. ``flagged`` collects the
    additions carrying a risk flag the gate holds on."""
    redis = get_redis_client()
    new = new_sources(gate.new_source_days)
    added_by_type: Counter = Counter()
    added_by_source: Counter = Counter()
    source_names: dict[str, str] = {}
    risks: dict[str, dict] = {}
    added_sample: list = []
    for batch in diff.added_indicators():
        for indicator in batch:
            added_by_type[indicator.get("type")] += 1
            for source in indicator.get("sources") or []:
                key = (
                    f"{source['type']}:{source['id']}"
                    if source.get("type") in ("feed", "server")
                    else source.get("type") or "unknown"
                )
                source_names.setdefault(key, source.get("name") or key)
            for key in indicator.get("source_keys") or []:
                added_by_source[key] += 1
            for flag, detail in risk_flags(indicator, gate, new):
                if flagged is not None and flag in gate.hold_on_risk:
                    flagged.add(indicator["uuid"])
                risk = risks.setdefault(flag, {"count": 0, "sample": []})
                risk["count"] += 1
                if len(risk["sample"]) < SAMPLE:
                    risk["sample"].append(_sample(indicator, detail))
            if len(added_sample) < SAMPLE * 2:
                added_sample.append(_sample(indicator))

    removed_by_type: Counter = Counter()
    removed_by_reason: Counter = Counter()
    removed_sample: list = []
    for batch in diff.removals():
        for removal in batch:
            removed_by_type[removal.get("type") or "unknown"] += 1
            removed_by_reason[removal["reason"]] += 1
            if len(removed_sample) < SAMPLE * 2:
                removed_sample.append(_sample(removal, removal["reason"]))

    previous = 0
    if not diff.first:
        previous = max(redis.scard(diff.previous_key) - 1, 0)
    return {
        "first": diff.first,
        "members": diff.members,
        "previous_members": previous,
        "added": diff.added,
        "removed": diff.removed,
        "added_by_type": dict(added_by_type.most_common()),
        "added_by_source": [
            {"key": k, "name": source_names.get(k, k), "count": n}
            for k, n in added_by_source.most_common(TOP_SOURCES)
        ],
        "removed_by_type": dict(removed_by_type.most_common()),
        "removed_by_reason": dict(removed_by_reason.most_common()),
        "risks": risks,
        "added_sample": added_sample,
        "removed_sample": removed_sample,
    }


def usual_added(db: Session, profile_id: int) -> Optional[float]:
    """The median additions of the last runs that let changes through."""
    rows = (
        db.query(release_models.ProfileRelease.added)
        .filter(
            release_models.ProfileRelease.profile_id == profile_id,
            release_models.ProfileRelease.status.in_(("released", "approved")),
        )
        .order_by(release_models.ProfileRelease.created_at.desc())
        .limit(SPIKE_HISTORY)
        .all()
    )
    if len(rows) < 3:
        return None
    return float(statistics.median(r.added for r in rows))


def _count(n: int, noun: str) -> str:
    return f"{n:,} {noun}{'' if n == 1 else 's'}"


def plan(
    summary: dict, gate: profile_schemas.ProfileGate, usual: Optional[float]
) -> dict:
    """What the gate holds: ``reasons`` (empty: nothing), and whether that is
    every addition (``all_added``, too many or a spike: the volume itself is
    the anomaly), only the flagged ones, and every removal."""
    held = {"reasons": [], "all_added": False, "removed": False}
    if not gate.enabled or summary["first"]:
        return held
    reasons = held["reasons"]
    added, removed = summary["added"], summary["removed"]
    if gate.max_additions is not None and added > gate.max_additions:
        reasons.append(f"{_count(added, 'addition')}, more than {gate.max_additions:,}")
        held["all_added"] = True
    if gate.max_removals is not None and removed > gate.max_removals:
        reasons.append(f"{_count(removed, 'removal')}, more than {gate.max_removals:,}")
        held["removed"] = True
    for flag in gate.hold_on_risk:
        count = (summary["risks"].get(flag) or {}).get("count", 0)
        if count:
            reasons.append(
                f"{_count(count, 'addition')} flagged {flag.replace('_', ' ')}"
            )
    if (
        gate.spike_factor
        and usual is not None
        and added >= SPIKE_MIN
        and added > gate.spike_factor * max(usual, 1)
    ):
        reasons.append(
            f"{added:,} additions, {added / max(usual, 1):.1f}× the usual {usual:,.0f}"
        )
        held["all_added"] = True
    return held


def hold_reasons(
    summary: dict, gate: profile_schemas.ProfileGate, usual: Optional[float]
) -> list[str]:
    """Why the gate holds some of these changes; empty when it lets all of
    them through."""
    return plan(summary, gate, usual)["reasons"]


def _keep_out(diff, held: dict, flagged: set) -> tuple[int, int]:
    """Take what the gate holds out of the diff's release: (additions,
    removals) held."""
    kept_added = kept_removed = 0
    if held["all_added"]:
        kept_added = diff.added
        diff.withhold_added()
    elif held["reasons"] and flagged:
        kept_added = len(flagged)
        ids = list(flagged)
        for start in range(0, len(ids), 1000):
            diff.withhold(ids[start : start + 1000])
    if held["removed"]:
        kept_removed = diff.removed
        diff.retain_removed()
    return kept_added, kept_removed


def _diff(profile: dict, rules=None):
    return profile_membership.Diff(
        f"profile:{profile['id']}",
        rules if rules is not None else profile["rules"],
        detection_profiles.context(),
        baseline_key(profile["id"]),
    )


# ── Releases ──────────────────────────────────────────────────────────────


def active_hold(db: Session, profile_id: int):
    """The profile's current hold, if any: what its outputs don't get yet."""
    return (
        db.query(release_models.ProfileRelease)
        .filter(
            release_models.ProfileRelease.profile_id == profile_id,
            release_models.ProfileRelease.status == "held",
        )
        .order_by(release_models.ProfileRelease.id.desc())
        .first()
    )


def held_profiles(db: Session) -> set[int]:
    """Profiles holding changes back from their outputs."""
    return {
        profile_id
        for (profile_id,) in db.query(release_models.ProfileRelease.profile_id)
        .filter(release_models.ProfileRelease.status == "held")
        .distinct()
    }


def _record(
    db: Session,
    profile_id: int,
    status: str,
    summary: dict,
    reasons: Optional[list] = None,
    user_id: Optional[int] = None,
):
    now = datetime.now(timezone.utc)
    row = release_models.ProfileRelease(
        profile_id=profile_id,
        status=status,
        members=summary["members"],
        added=summary["added"],
        removed=summary["removed"],
        reasons=reasons or [],
        summary=summary,
        user_id=user_id,
        created_at=now,
    )
    db.add(row)
    db.flush()
    stale = (
        db.query(release_models.ProfileRelease.id)
        .filter(release_models.ProfileRelease.profile_id == profile_id)
        .order_by(release_models.ProfileRelease.id.desc())
        .offset(KEEP_RELEASES)
        .all()
    )
    if stale:
        db.query(release_models.ProfileRelease).filter(
            release_models.ProfileRelease.id.in_([r.id for r in stale])
        ).delete(synchronize_session=False)
    return row


def _lift(db: Session, profile_id: int) -> None:
    row = active_hold(db, profile_id)
    if row is not None:
        row.status = "lifted"
        row.updated_at = datetime.now(timezone.utc)


def _hold(
    db: Session,
    profile: dict,
    summary: dict,
    reasons: list[str],
    kept: tuple[int, int],
) -> None:
    """Record what is held (``kept``: additions, removals): update the
    current hold, or start one and notify the reviewers."""
    held = {**summary, "added": kept[0], "removed": kept[1]}
    row = active_hold(db, profile["id"])
    if row is not None:
        row.summary = summary
        row.reasons = reasons
        row.members, row.added, row.removed = (
            summary["members"],
            kept[0],
            kept[1],
        )
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        return
    row = _record(db, profile["id"], "held", held, reasons)
    row.summary = summary
    db.commit()
    logger.info("profile %s: changes held (%s)", profile["id"], "; ".join(reasons))
    from app.repositories import notifications

    notifications.create_profile_held_notifications(db, profile, held, reasons)


def ready(profile_id: int) -> None:
    """Before a run: release the profile's changes its gate lets through, and
    hold the rest (see the module). Returns once released; a run sends the
    released members only. While another run releases, this one sends what
    was released already."""
    from app.database import SessionLocal

    profile = detection_profiles.load(profile_id)
    gate = gate_of(profile.get("gate"))
    with _lock(profile_id, LOCK_WAIT_SECONDS) as locked:
        if not locked:
            logger.info("profile %s: release busy; sending the last one", profile_id)
            return
        diff = _diff(profile)
        try:
            flagged: set = set()
            summary = summarise(diff, gate, flagged)
            with SessionLocal() as db:
                held = plan(
                    summary, gate, usual_added(db, profile_id) if gate.enabled else None
                )
                kept = _keep_out(diff, held, flagged)
                members = diff.members
                diff.commit(baseline_key(profile_id))
                released = {
                    **summary,
                    "members": members,
                    "added": summary["added"] - kept[0],
                    "removed": summary["removed"] - kept[1],
                }
                if summary["first"] or released["added"] or released["removed"]:
                    _record(
                        db,
                        profile_id,
                        "baseline" if summary["first"] else "released",
                        released,
                    )
                if held["reasons"]:
                    _hold(db, profile, summary, held["reasons"], kept)
                else:
                    _lift(db, profile_id)
                db.commit()
        except Exception:
            diff.discard()
            raise


def check(profile_id: int) -> Optional[list[str]]:
    """Look ahead (between runs): record what the next run would hold, so
    reviewers hear of it early, and lift a hold that no longer applies.
    Nothing is released. None when another check is running."""
    from app.database import SessionLocal

    profile = detection_profiles.load(profile_id)
    gate = gate_of(profile.get("gate"))
    with _lock(profile_id, 0) as locked:
        if not locked:
            return None
        diff = _diff(profile)
        try:
            flagged: set = set()
            summary = summarise(diff, gate, flagged)
            with SessionLocal() as db:
                held = plan(summary, gate, usual_added(db, profile_id))
                kept = _keep_out(diff, held, flagged)
                if held["reasons"]:
                    _hold(db, profile, summary, held["reasons"], kept)
                else:
                    _lift(db, profile_id)
                    db.commit()
        finally:
            diff.discard()
        return held["reasons"]


def check_all() -> dict:
    """Look ahead for every profile with an enabled gate."""
    from app.database import SessionLocal

    with SessionLocal() as db:
        ids = [
            p.id for p in detection_profiles.get_profiles(db) if gate_of(p.gate).enabled
        ]
    held = 0
    for profile_id in ids:
        try:
            if check(profile_id):
                held += 1
        except Exception:
            logger.exception("profile %s: change check failed", profile_id)
    return {"checked": len(ids), "held": held}


def preview(db: Session, profile_id: int, rules=None) -> dict:
    """The change preview, with why the next run would be held. With
    ``rules``, of those rules instead of the profile's (a dry run)."""
    profile = detection_profiles.load(profile_id)
    gate = gate_of(profile.get("gate"))
    usual = usual_added(db, profile_id)
    diff = _diff(profile, rules)
    try:
        flagged: set = set()
        summary = summarise(diff, gate, flagged)
        digest = fingerprint(diff)
        held = plan(summary, gate, usual)
        kept = _keep_out(diff, held, flagged)
    finally:
        diff.discard()
    summary["usual_added"] = usual
    hold = active_hold(db, profile_id)
    return {
        "generated_at": datetime.now(timezone.utc),
        # What approving these changes must name (see approve).
        "fingerprint": digest,
        "gate": gate,
        "held": hold is not None,
        "held_since": hold.created_at if hold is not None else None,
        "reasons": held["reasons"],
        # What the next run keeps out of the outputs.
        "held_added": kept[0],
        "held_removed": kept[1],
        "changes": summary,
        "releases": releases(db, profile_id),
        "consumers": consumers(db, profile_id),
    }


def approve(db: Session, profile_id: int, user_id: int, expected: str) -> dict:
    """Release every change a reviewer saw (``expected``, the preview's
    fingerprint), held ones included, and run the outputs. ChangesMoved when
    the changes are no longer those: they need reviewing again."""
    profile = detection_profiles.load(profile_id)
    gate = gate_of(profile.get("gate"))
    with _lock(profile_id, LOCK_WAIT_SECONDS) as locked:
        if not locked:
            raise GateBusy("another run is releasing the profile's changes")
        diff = _diff(profile)
        try:
            if fingerprint(diff) != expected:
                raise ChangesMoved(
                    "the changes moved since they were previewed; review them again"
                )
            summary = summarise(diff, gate)
            diff.commit(baseline_key(profile_id))
        except Exception:
            diff.discard()
            raise
        _lift(db, profile_id)
        row = _record(db, profile_id, "approved", summary, user_id=user_id)
        db.commit()
    _rerun(db, profile_id)
    return {"id": row.id, "added": row.added, "removed": row.removed}


def releases(db: Session, profile_id: int, limit: int = 30) -> list[dict]:
    from app.models import user as user_models

    rows = (
        db.query(release_models.ProfileRelease, user_models.User.email)
        .outerjoin(
            user_models.User,
            user_models.User.id == release_models.ProfileRelease.user_id,
        )
        .filter(release_models.ProfileRelease.profile_id == profile_id)
        .order_by(
            release_models.ProfileRelease.created_at.desc(),
            release_models.ProfileRelease.id.desc(),
        )
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "members": r.members,
            "added": r.added,
            "removed": r.removed,
            "reasons": r.reasons or [],
            "user_email": email,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r, email in rows
    ]


# ── Outputs ───────────────────────────────────────────────────────────────


def consumers(db: Session, profile_id: int) -> list[dict]:
    """The outputs reading the profile, and whether its gate holds them."""
    from app.models import export as export_models
    from app.models import sink as sink_models

    found = [
        {
            "kind": "export",
            "id": e.id,
            "name": e.name,
            "status": e.status,
            "gated": True,
        }
        for e in db.query(export_models.Export)
        .filter(export_models.Export.profile_id == profile_id)
        .order_by(export_models.Export.name)
    ]
    for sink in db.query(sink_models.Sink).order_by(sink_models.Sink.name):
        filters = sink.filters or {}
        if filters.get("profile_id") != profile_id:
            continue
        found.append(
            {
                "kind": "sink",
                "id": sink.id,
                "name": sink.name,
                "status": (
                    "keeps in step"
                    if filters.get("sync_membership")
                    else "sends published events"
                ),
                "gated": bool(filters.get("sync_membership")),
            }
        )
    return found


def _rerun(db: Session, profile_id: int) -> None:
    """Run the profile's exports, and sync its sinks keeping in step, so what
    was approved goes out now."""
    from app.worker import tasks

    for consumer in consumers(db, profile_id):
        if consumer["kind"] == "export":
            tasks.run_export.delay(consumer["id"])
        elif consumer["kind"] == "sink" and consumer["gated"]:
            tasks.sync_sink_membership.apply_async((consumer["id"],), queue="sinks")


def forget(profile_id: int) -> None:
    get_redis_client().delete(baseline_key(profile_id))
