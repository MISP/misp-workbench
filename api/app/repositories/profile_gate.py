"""Change preview and approval gate: see what a profile's next run changes,
and hold large or risky changes until an analyst approves them.

A profile's *runs* are those of the outputs that send its members as a set:
exports and feeds referencing it, and sinks keeping in step with it. Before
each, ``ready`` compares what the profile selects now with what it last
*released* (a member set kept in Redis, like a sink's, see
profile_membership):

- within the profile's gate (or without one), the changes are released: the
  baseline moves on and the run goes ahead;
- past it (too many additions or removals, a risky addition, a spike), the
  changes are *held*: the run waits, and reviewers are notified. Approving
  releases them and runs the outputs that waited.

Every release and hold is recorded (``profile_releases``), with the change
preview at the time, which gives the trend of recent runs. Lookups,
restSearch and sinks sending published events judge one value at a time, as
it comes; they aren't runs and aren't held.
"""

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


class ChangesHeld(Exception):
    """A run waits: its profile's changes need approving."""

    def __init__(self, reasons: list[str]):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


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


def summarise(diff, gate: profile_schemas.ProfileGate) -> dict:
    """The change preview of a computed diff."""
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


def hold_reasons(
    summary: dict, gate: profile_schemas.ProfileGate, usual: Optional[float]
) -> list[str]:
    """Why the gate holds these changes; empty when it lets them through."""
    if not gate.enabled or summary["first"]:
        return []
    reasons = []
    added, removed = summary["added"], summary["removed"]
    if gate.max_additions is not None and added > gate.max_additions:
        reasons.append(f"{added:,} additions, more than {gate.max_additions:,}")
    if gate.max_removals is not None and removed > gate.max_removals:
        reasons.append(f"{removed:,} removals, more than {gate.max_removals:,}")
    for flag in gate.hold_on_risk:
        count = (summary["risks"].get(flag) or {}).get("count", 0)
        if count:
            reasons.append(f"{count:,} addition(s) flagged {flag.replace('_', ' ')}")
    if (
        gate.spike_factor
        and usual is not None
        and added >= SPIKE_MIN
        and added > gate.spike_factor * max(usual, 1)
    ):
        reasons.append(
            f"{added:,} additions, {added / max(usual, 1):.1f}× the usual {usual:,.0f}"
        )
    return reasons


def _diff(profile: dict, rules=None):
    return profile_membership.Diff(
        f"profile:{profile['id']}",
        rules if rules is not None else profile["rules"],
        detection_profiles.context(),
        baseline_key(profile["id"]),
    )


# ── Releases ──────────────────────────────────────────────────────────────


def latest(db: Session, profile_id: int):
    return (
        db.query(release_models.ProfileRelease)
        .filter(release_models.ProfileRelease.profile_id == profile_id)
        .order_by(
            release_models.ProfileRelease.created_at.desc(),
            release_models.ProfileRelease.id.desc(),
        )
        .first()
    )


def held_profiles(db: Session) -> set[int]:
    """Profiles whose latest check holds their changes."""
    from sqlalchemy import func

    newest = (
        db.query(
            release_models.ProfileRelease.profile_id,
            func.max(release_models.ProfileRelease.id).label("id"),
        )
        .group_by(release_models.ProfileRelease.profile_id)
        .subquery()
    )
    return {
        r.profile_id
        for r in db.query(release_models.ProfileRelease).join(
            newest, release_models.ProfileRelease.id == newest.c.id
        )
        if r.status == "held"
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
    row = latest(db, profile_id)
    if row is not None and row.status == "held":
        row.status = "lifted"
        row.updated_at = datetime.now(timezone.utc)


def _hold(db: Session, profile: dict, summary: dict, reasons: list[str]) -> None:
    """Hold the changes: update a current hold, or start one and notify."""
    row = latest(db, profile["id"])
    if row is not None and row.status == "held":
        row.summary = summary
        row.reasons = reasons
        row.members, row.added, row.removed = (
            summary["members"],
            summary["added"],
            summary["removed"],
        )
        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        return
    _record(db, profile["id"], "held", summary, reasons)
    db.commit()
    logger.info("profile %s: changes held (%s)", profile["id"], "; ".join(reasons))
    from app.repositories import notifications

    notifications.create_profile_held_notifications(db, profile, summary, reasons)


def _changed(summary: dict) -> bool:
    return bool(summary["first"] or summary["added"] or summary["removed"])


def ready(profile_id: int) -> None:
    """Before a run: release the profile's changes, or raise ChangesHeld."""
    from app.database import SessionLocal

    profile = detection_profiles.load(profile_id)
    gate = gate_of(profile.get("gate"))
    with _lock(profile_id, LOCK_WAIT_SECONDS) as locked:
        if not locked:
            raise ChangesHeld(["another run is checking the profile's changes"])
        diff = _diff(profile)
        try:
            summary = summarise(diff, gate)
            with SessionLocal() as db:
                reasons = hold_reasons(
                    summary, gate, usual_added(db, profile_id) if gate.enabled else None
                )
                if reasons:
                    diff.discard()
                    _hold(db, profile, summary, reasons)
                    raise ChangesHeld(reasons)
                diff.commit(baseline_key(profile_id))
                _lift(db, profile_id)
                if _changed(summary):
                    _record(
                        db,
                        profile_id,
                        "baseline" if summary["first"] else "released",
                        summary,
                    )
                db.commit()
        except ChangesHeld:
            raise
        except Exception:
            diff.discard()
            raise


def check(profile_id: int) -> Optional[list[str]]:
    """Look ahead (between runs): hold what the next run would hold, so
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
            summary = summarise(diff, gate)
        finally:
            diff.discard()
        with SessionLocal() as db:
            reasons = hold_reasons(summary, gate, usual_added(db, profile_id))
            if reasons:
                _hold(db, profile, summary, reasons)
            else:
                _lift(db, profile_id)
                db.commit()
        return reasons


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
    diff = _diff(profile, rules)
    try:
        summary = summarise(diff, gate)
    finally:
        diff.discard()
    usual = usual_added(db, profile_id)
    summary["usual_added"] = usual
    row = latest(db, profile_id)
    held = row is not None and row.status == "held"
    return {
        "generated_at": datetime.now(timezone.utc),
        "gate": gate,
        "held": held,
        "held_since": row.created_at if held else None,
        "reasons": hold_reasons(summary, gate, usual),
        "changes": summary,
        "releases": releases(db, profile_id),
        "consumers": consumers(db, profile_id),
    }


def approve(db: Session, profile_id: int, user_id: int) -> dict:
    """Release the profile's changes as they are now, and run the outputs
    that waited."""
    profile = detection_profiles.load(profile_id)
    gate = gate_of(profile.get("gate"))
    with _lock(profile_id, LOCK_WAIT_SECONDS) as locked:
        if not locked:
            raise ChangesHeld(["another run is checking the profile's changes"])
        diff = _diff(profile)
        try:
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
    """Run the exports that waited, and sync the sinks keeping in step."""
    from app.worker import tasks

    for consumer in consumers(db, profile_id):
        if consumer["kind"] == "export" and consumer["status"] == "held":
            tasks.run_export.delay(consumer["id"])
        elif consumer["kind"] == "sink" and consumer["gated"]:
            tasks.sync_sink_membership.apply_async((consumer["id"],), queue="sinks")


def forget(profile_id: int) -> None:
    get_redis_client().delete(baseline_key(profile_id))
