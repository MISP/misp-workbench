"""The review queue: analysts' decisions between ingestion and the controls.

A profile that requires approval (``ProfileRules.require_approval``) only
selects indicators that are approved, by an analyst or by an auto-approve
profile. What such a profile would select but isn't approved, rejected or
snoozed is *pending*: the queue.

Decisions are rows of ``indicator_reviews``, one per indicator uuid (so per
type and value, whichever sources report it, and outliving the indicator),
audited, and carried on the indicator as ``review`` so profiles can filter
on them. Auto-approval isn't stored: it is evaluated with the profiles, so
an indicator moves in and out of it as its score or sources change.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from fastapi import Request
from sqlalchemy.orm import Session, joinedload

from app.models import audit_log as audit_log_models
from app.models import detection_profile as profile_models
from app.models import indicator_review as review_models
from app.repositories import detection_profiles
from app.repositories import indicators as indicators_repository
from app.services import audit
from app.services.opensearch import get_opensearch_client

logger = logging.getLogger(__name__)

# Action -> the status it leaves. Reopening takes a decision back.
ACTIONS = {
    "approve": "approved",
    "reject": "rejected",
    "snooze": "snoozed",
    "reopen": "pending",
}
AUDIT_ACTIONS = {
    "approve": "indicator_review.approved",
    "reject": "indicator_review.rejected",
    "snooze": "indicator_review.snoozed",
    "reopen": "indicator_review.reopened",
}
DECIDED = ("approved", "rejected", "snoozed")
MAX_BULK = 500
QUERY_CHUNK = 1000

QUEUE_SORTS = {
    "score": [{"score": {"order": "desc", "missing": "_last"}}],
    "last_seen": [{"last_seen": {"order": "desc", "missing": "_last"}}],
    "first_seen": [{"first_seen": {"order": "desc", "missing": "_last"}}],
    "event_count": [{"event_count": {"order": "desc"}}],
}


class UnknownIndicators(Exception):
    def __init__(self, ids: list[str]):
        super().__init__(", ".join(ids))
        self.ids = ids


def _epoch(value: Optional[datetime]) -> Optional[int]:
    return int(value.timestamp()) if value else None


def doc_review(row) -> Optional[dict]:
    """A decision as the indicator carries it; None when there is none."""
    if row is None or row.status not in DECIDED:
        return None
    return {
        "status": row.status,
        "until": _epoch(row.snoozed_until) if row.status == "snoozed" else None,
        "at": _epoch(row.decided_at),
    }


def _rows(db: Session, ids: list[str]) -> dict[str, review_models.IndicatorReview]:
    rows = {}
    for start in range(0, len(ids), QUERY_CHUNK):
        chunk = ids[start : start + QUERY_CHUNK]
        for row in db.query(review_models.IndicatorReview).filter(
            review_models.IndicatorReview.indicator_uuid.in_(chunk)
        ):
            rows[row.indicator_uuid] = row
    return rows


def reviews_for(ids: Iterable[str]) -> dict[str, dict]:
    """The decisions on indicators, as they carry them, by uuid."""
    from app.database import SessionLocal

    ids = list(dict.fromkeys(ids))
    if not ids:
        return {}
    with SessionLocal() as db:
        return {
            uuid: review
            for uuid, row in _rows(db, ids).items()
            if (review := doc_review(row)) is not None
        }


def statuses() -> dict[str, str]:
    """Every decision's status, by indicator uuid (for values without an
    indicator yet, see detection_profiles._review_status)."""
    from app.database import SessionLocal

    with SessionLocal() as db:
        return dict(
            db.query(
                review_models.IndicatorReview.indicator_uuid,
                review_models.IndicatorReview.status,
            ).filter(review_models.IndicatorReview.status.in_(DECIDED))
        )


# ── The queue ─────────────────────────────────────────────────────────────


def requiring_profiles(db: Session) -> list:
    """Profiles that require approval: what they'd select is reviewed."""
    return [
        p
        for p in db.query(profile_models.DetectionProfile).order_by(
            profile_models.DetectionProfile.name
        )
        if (p.rules or {}).get("require_approval")
    ]


def auto_approve_profiles(db: Session) -> list:
    return (
        db.query(profile_models.DetectionProfile)
        .filter(profile_models.DetectionProfile.auto_approve.is_(True))
        .order_by(profile_models.DetectionProfile.name)
        .all()
    )


def _unreviewed(rules):
    """A profile's rules, without the approval it requires."""
    return detection_profiles._rules(rules).model_copy(
        update={"require_approval": False}
    )


def snoozed_now(now: int) -> dict:
    return {
        "bool": {
            "filter": [
                {"term": {"review.status": "snoozed"}},
                {"range": {"review.until": {"gt": now}}},
            ]
        }
    }


def queue_query(profiles: list, ctx: dict) -> Optional[dict]:
    """Pending indicators: ones a profile requiring approval would select,
    not approved (by an analyst or automatically), rejected or snoozed.

    None when no profile requires approval (nothing is pending).
    """
    if not profiles:
        return None
    return {
        "bool": {
            "filter": [
                {
                    "bool": {
                        "should": [
                            detection_profiles.to_query(_unreviewed(p.rules), ctx)
                            for p in profiles
                        ],
                        "minimum_should_match": 1,
                    }
                }
            ],
            "must_not": [
                detection_profiles.approved_query(ctx),
                detection_profiles.REJECTED,
                snoozed_now(ctx["now"]),
            ],
        }
    }


def queue(
    db: Session,
    profile_id: Optional[int] = None,
    query: Optional[str] = None,
    type_: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    sort: str = "score",
    page: int = 1,
    size: int = 50,
) -> dict:
    """One page of the queue, each item with the profiles it is pending for."""
    profiles = requiring_profiles(db)
    if profile_id is not None:
        profiles = [p for p in profiles if p.id == profile_id]
    ctx = detection_profiles.context()
    base = queue_query(profiles, ctx)
    size = max(1, min(size, 200))
    page = max(page, 1)
    empty = {"total": 0, "page": page, "size": size, "items": []}
    if base is None:
        return empty
    filters: list = [base]
    if type_:
        filters.append({"term": {"type.keyword": type_}})
    if source:
        filters.append({"term": {"source_keys": source}})
    if min_score is not None or max_score is not None:
        bounds = {}
        if min_score is not None:
            bounds["gte"] = min_score
        if max_score is not None:
            bounds["lte"] = max_score
        filters.append({"range": {"score": bounds}})
    must = (
        [{"query_string": {"query": query, "default_field": "value"}}] if query else []
    )
    start = (page - 1) * size
    if start + size > indicators_repository.MAX_RESULT_WINDOW:
        raise ValueError(
            f"results past the first {indicators_repository.MAX_RESULT_WINDOW} "
            "can't be paged to; narrow the filters"
        )
    response = get_opensearch_client().search(
        index=indicators_repository.INDEX,
        body={
            "query": {"bool": {"must": must, "filter": filters}},
            "sort": QUEUE_SORTS.get(sort, QUEUE_SORTS["score"])
            + [{"uuid.keyword": "asc"}],
            "from": start,
            "size": size,
            "track_total_hits": True,
            "_source": {"excludes": list(indicators_repository.INTERNAL_FIELDS)},
        },
        ignore=[404],
    )
    hits = response.get("hits", {})
    items = []
    for hit in hits.get("hits", []):
        indicator = hit["_source"]
        indicator["pending_for"] = [
            {"id": p.id, "name": p.name}
            for p in profiles
            if detection_profiles.matches(_unreviewed(p.rules), indicator, ctx)
        ]
        items.append(indicator)
    return {
        "total": hits.get("total", {}).get("value", 0),
        "page": page,
        "size": size,
        "items": items,
    }


def summary(db: Session) -> dict:
    """How many are pending and decided, and the profiles involved."""
    profiles = requiring_profiles(db)
    ctx = detection_profiles.context()
    pending = 0
    query = queue_query(profiles, ctx)
    if query is not None:
        pending = (
            get_opensearch_client()
            .count(
                index=indicators_repository.INDEX,
                body={"query": query},
                ignore=[404],
            )
            .get("count", 0)
        )
    now = datetime.now(timezone.utc)
    rows = db.query(review_models.IndicatorReview)
    return {
        "pending": pending,
        "snoozed": rows.filter(
            review_models.IndicatorReview.status == "snoozed",
            review_models.IndicatorReview.snoozed_until > now,
        ).count(),
        "approved": rows.filter(
            review_models.IndicatorReview.status == "approved"
        ).count(),
        "rejected": rows.filter(
            review_models.IndicatorReview.status == "rejected"
        ).count(),
        "requiring_profiles": [{"id": p.id, "name": p.name} for p in profiles],
        "auto_approve_profiles": [
            {"id": p.id, "name": p.name} for p in auto_approve_profiles(db)
        ],
    }


# ── Decisions ─────────────────────────────────────────────────────────────


def _org_name(user) -> Optional[str]:
    return user.organisation.name if user and user.organisation else None


def redact(entries: list[dict], viewer) -> list[dict]:
    """Who decided is audit data: the decider's email is only shown to audit
    admins and to the decider's own organisation; others see the organisation.
    """
    from app.auth.utils import role_has_scope

    scopes = list(getattr(getattr(viewer, "role", None), "scopes", None) or [])
    if role_has_scope(scopes, "audit_logs:admin"):
        return entries
    for entry in entries:
        if entry.get("user_org_id") != viewer.org_id:
            entry["user_email"] = None
    return entries


def _decision(row) -> dict:
    return {
        "indicator_uuid": row.indicator_uuid,
        "type": row.type,
        "value": row.value,
        "status": row.status,
        "reason": row.reason,
        "snoozed_until": row.snoozed_until,
        "warninglisted": row.warninglisted,
        "user_id": row.user_id,
        "user_email": row.user.email if row.user else None,
        "user_org_id": row.user.org_id if row.user else None,
        "user_organisation": _org_name(row.user),
        "decided_at": row.decided_at,
    }


def decisions(
    db: Session,
    status: str,
    query: Optional[str] = None,
    page: int = 1,
    size: int = 50,
) -> dict:
    """Decided indicators, newest decision first (snoozed: still snoozed)."""
    rows = (
        db.query(review_models.IndicatorReview)
        .options(joinedload(review_models.IndicatorReview.user))
        .filter(review_models.IndicatorReview.status == status)
    )
    if status == "snoozed":
        rows = rows.filter(
            review_models.IndicatorReview.snoozed_until > datetime.now(timezone.utc)
        )
    if query:
        rows = rows.filter(review_models.IndicatorReview.value.ilike(f"%{query}%"))
    size = max(1, min(size, 200))
    page = max(page, 1)
    total = rows.count()
    rows = (
        rows.order_by(
            review_models.IndicatorReview.decided_at.desc(),
            review_models.IndicatorReview.id.desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [_decision(r) for r in rows],
    }


def get_decision(db: Session, indicator_uuid: str) -> Optional[dict]:
    row = (
        db.query(review_models.IndicatorReview)
        .filter(review_models.IndicatorReview.indicator_uuid == indicator_uuid)
        .first()
    )
    return _decision(row) if row else None


def history(db: Session, indicator_uuid: str) -> list[dict]:
    """Every decision taken on an indicator, newest first (the audit log)."""
    row = (
        db.query(review_models.IndicatorReview)
        .filter(review_models.IndicatorReview.indicator_uuid == indicator_uuid)
        .first()
    )
    if row is None:
        return []
    entries = (
        db.query(audit_log_models.AuditLog)
        .options(joinedload(audit_log_models.AuditLog.actor))
        .filter(
            audit_log_models.AuditLog.resource_type == "indicator_review",
            audit_log_models.AuditLog.resource_id == row.id,
        )
        .order_by(
            audit_log_models.AuditLog.created_at.desc(),
            audit_log_models.AuditLog.id.desc(),
        )
        .all()
    )
    return [
        {
            "action": e.action.removeprefix("indicator_review."),
            "at": e.created_at,
            "user_email": e.actor.email if e.actor else None,
            "user_org_id": e.actor.org_id if e.actor else None,
            "user_organisation": _org_name(e.actor),
            "reason": (e.metadata_ or {}).get("reason"),
            "snoozed_until": (e.metadata_ or {}).get("snoozed_until"),
            "warninglisted": bool((e.metadata_ or {}).get("warninglisted")),
        }
        for e in entries
    ]


def decide(
    db: Session,
    indicator_ids: list[str],
    action: str,
    user_id: int,
    reason: Optional[str] = None,
    snooze_days: Optional[int] = None,
    warninglist: bool = False,
    request: Optional[Request] = None,
) -> dict:
    """Approve, reject, snooze or reopen indicators, by uuid.

    An indicator is known by its live document, or for one decided before,
    by its decision (a purged indicator can still be reopened). Rejecting
    with ``warninglist`` adds the value to the "Rejected in review"
    warninglist; any
    other decision on it takes the value off again.
    """
    from app.repositories import warninglists

    ids = list(dict.fromkeys(indicator_ids))
    rows = _rows(db, ids)
    live = indicators_repository.get_indicators(i for i in ids if i not in rows)
    unknown = [i for i in ids if i not in rows and i not in live]
    if unknown:
        raise UnknownIndicators(unknown)

    status = ACTIONS[action]
    now = datetime.now(timezone.utc)
    until = (
        now + timedelta(days=snooze_days)
        if action == "snooze" and snooze_days
        else None
    )
    to_list, to_unlist = [], []
    touched = []
    for indicator_id in ids:
        row = rows.get(indicator_id)
        if row is None:
            found = live[indicator_id]
            row = review_models.IndicatorReview(
                indicator_uuid=indicator_id,
                type=found["type"],
                value=found["value"],
                warninglisted=False,
            )
            db.add(row)
        listed = action == "reject" and warninglist
        if listed and not row.warninglisted:
            to_list.append(row.value)
        if row.warninglisted and not listed:
            to_unlist.append(row.value)
        row.status = status
        row.reason = reason
        row.snoozed_until = until
        row.warninglisted = listed
        row.user_id = user_id
        row.decided_at = now
        touched.append(row)
    db.flush()
    for row in touched:
        audit.record(
            db,
            action=AUDIT_ACTIONS[action],
            resource_type="indicator_review",
            resource_id=row.id,
            actor_user_id=user_id,
            request=request,
            metadata={
                "indicator_uuid": row.indicator_uuid,
                "type": row.type,
                "value": row.value,
                "reason": reason,
                "snoozed_until": until.isoformat() if until else None,
                "warninglisted": row.warninglisted,
            },
        )
    db.commit()

    values = [row.value for row in touched]
    if to_list or to_unlist:
        warninglists.change_rejected_list(db, add=to_list, remove=to_unlist)
    _apply(values)
    return {"decided": len(touched), "status": status}


def _apply(values: list[str]) -> None:
    """Put the decisions on the indicators now, so the queue and every
    output see them; the next sync goes over them again in case one raced."""
    indicators_repository.mark_sighted(values)
    try:
        indicators_repository.refresh_values(values)
        get_opensearch_client().indices.refresh(index=indicators_repository.INDEX)
    except Exception:
        logger.exception("review decisions not applied yet; the next sync will")
