"""Detection profiles: "what goes to which control", defined once.

A profile's rules select consolidated indicators. They are evaluated two
ways, kept equivalent by tests:

- ``to_query``: an OpenSearch query on the indicators index, for outputs that
  read many indicators (exports, feeds, the indicators search, counts);
- ``matches``: a check on one indicator, for outputs that judge records one
  at a time (sinks, /lookup, restSearch).

A value too new to have an indicator yet is judged on an indicator built
from its attribute and event (``attribute_indicator``), on every rule: its
source and organisation come from the event, its score is computed as
usual. A rule it can't answer fails closed. And because an indicator can
lag behind its attributes by a sync, the rules that keep things out (TLP,
excluded tags, warninglists, validation) are also checked on the attribute
as it is now: a value tagged tlp:red a second ago doesn't leave on a stale
indicator.

Review decisions (``indicator_reviews``) are on the indicators too: a profile
can require approval, by an analyst or by an auto-approve profile, or just
leave out what analysts rejected. A value without an indicator is judged on
its stored decision.
"""

import fnmatch
import time
from datetime import datetime, timezone
from typing import Iterable, Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import detection_profile as profile_models
from app.repositories import indicators as indicators_repository
from app.schemas import detection_profile as profile_schemas

DAY = 86400
# Least to most restrictive (indicators store their most restrictive TLP).
TLP_LEVELS = ["tlp:clear", "tlp:green", "tlp:amber", "tlp:amber+strict", "tlp:red"]
# A tlp:white is a tlp:clear.
TLP_ALIASES = {"tlp:white": "tlp:clear"}
PREVIEW_SAMPLE = 5


class ProfileInUse(Exception):
    pass


class ProfileNotFound(Exception):
    pass


# ── CRUD ──────────────────────────────────────────────────────────────────


def get_profiles(db: Session) -> list[profile_models.DetectionProfile]:
    return (
        db.query(profile_models.DetectionProfile)
        .order_by(profile_models.DetectionProfile.name)
        .all()
    )


def get_profile(db: Session, profile_id: int):
    return db.get(profile_models.DetectionProfile, profile_id)


def resolve(db: Session, ref: Union[int, str, None]):
    """A profile by id or name; None for no reference, 404 for a bad one."""
    if ref in (None, ""):
        return None
    query = db.query(profile_models.DetectionProfile)
    if isinstance(ref, int) or str(ref).isdigit():
        found = query.filter(profile_models.DetectionProfile.id == int(ref)).first()
    else:
        found = query.filter(profile_models.DetectionProfile.name == str(ref)).first()
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No detection profile {ref!r}",
        )
    return found


def load(ref) -> dict:
    """``{id, name, granularity, rules}`` of a profile by id or name, outside
    a request (workers, streaming). Raises ProfileNotFound."""
    from app.database import SessionLocal

    with SessionLocal() as db:
        try:
            profile = resolve(db, ref)
        except HTTPException:
            raise ProfileNotFound(f"No detection profile {ref!r}") from None
        if profile is None:
            raise ProfileNotFound("No detection profile given")
        return {
            "id": profile.id,
            "name": profile.name,
            "granularity": profile.granularity,
            "rules": _rules(profile.rules),
            "gate": profile.gate,
        }


def create_profile(db: Session, profile: profile_schemas.DetectionProfileCreate):
    db_profile = profile_models.DetectionProfile(
        name=profile.name,
        description=profile.description,
        granularity=profile.granularity,
        rules=profile.rules.model_dump(),
        auto_approve=profile.auto_approve,
        gate=profile.gate.model_dump() if profile.gate else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_profile(
    db: Session, db_profile, profile: profile_schemas.DetectionProfileUpdate
):
    patch = profile.model_dump(exclude_unset=True)
    try:
        profile_schemas.check_auto_approve(
            patch.get("auto_approve", db_profile.auto_approve),
            _rules(patch.get("rules", db_profile.rules)),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    for key, value in patch.items():
        setattr(db_profile, key, value)
    db_profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def users_of(db: Session, profile_id: int) -> list[str]:
    """Exports and sinks referencing the profile, by name."""
    from app.models import export as export_models
    from app.models import sink as sink_models

    names = [
        f"export {e.name!r}"
        for e in db.query(export_models.Export).filter(
            export_models.Export.profile_id == profile_id
        )
    ]
    names += [
        f"sink {s.name!r}"
        for s in db.query(sink_models.Sink).all()
        if (s.filters or {}).get("profile_id") == profile_id
    ]
    return names


def delete_profile(db: Session, db_profile) -> None:
    # An output losing its profile would send everything its own query
    # matches: refuse rather than let a block list fill up.
    used_by = users_of(db, db_profile.id)
    if used_by:
        raise ProfileInUse(", ".join(used_by))
    from app.repositories import profile_gate

    profile_gate.forget(db_profile.id)
    db.delete(db_profile)
    db.commit()


# ── Evaluation ────────────────────────────────────────────────────────────


def context(now: Optional[int] = None) -> dict:
    """What evaluating rules needs besides the indicator: time, trust, and
    the auto-approve profiles' rules."""
    from app.services import scoring

    cfg = scoring.load_config()
    trust = cfg.get("_trust", {})
    return {
        "auto_approve": auto_approve_rules(),
        "now": int(time.time()) if now is None else now,
        # For scoring indicators built from a lone attribute.
        "scoring": cfg,
        # Source key -> score modifier, for feeds and servers that have one.
        "trust": {
            f"{kind}:{key}": modifier
            for kind in ("feed", "server")
            for key, (modifier, _cap) in trust.get(kind, {}).items()
        },
    }


def auto_approve_rules() -> list[profile_schemas.ProfileRules]:
    """The rules of the auto-approve profiles."""
    from app.database import SessionLocal

    with SessionLocal() as db:
        return [
            _rules(p.rules)
            for p in db.query(profile_models.DetectionProfile)
            .filter(profile_models.DetectionProfile.auto_approve.is_(True))
            .order_by(profile_models.DetectionProfile.id)
        ]


def _rules(rules) -> profile_schemas.ProfileRules:
    if isinstance(rules, profile_schemas.ProfileRules):
        return rules
    return profile_schemas.ProfileRules.model_validate(rules or {})


def _too_restrictive(ceiling: str) -> list[str]:
    return TLP_LEVELS[TLP_LEVELS.index(ceiling) + 1 :]


def _tag_clause(pattern: str) -> dict:
    if any(c in pattern for c in "*?["):
        return {"wildcard": {"tags": {"value": pattern}}}
    return {"term": {"tags": pattern}}


def _only_from(field: str, count_field: str, keys: list) -> dict:
    """Indicators whose every ``field`` value is among ``keys``."""
    return {
        "terms_set": {
            field: {
                "terms": keys,
                # At least one: an indicator with none isn't "only" from them.
                "minimum_should_match_script": {
                    "source": f"Math.max(doc['{count_field}'].value, 1)"
                },
            }
        }
    }


def _trust_split(rules, ctx: dict) -> tuple[Optional[list], list]:
    """For min_source_trust: (allowed keys, or None for "any but"), below keys."""
    threshold = rules.min_source_trust
    trust = ctx["trust"]
    if threshold > 0:
        # Unconfigured sources (0) are below: only configured ones can pass.
        return [k for k, m in trust.items() if m >= threshold], []
    return None, [k for k, m in trust.items() if m < threshold]


REJECTED = {"term": {"review.status": "rejected"}}


def approved_query(ctx: dict) -> dict:
    """Indicators an analyst approved, or an auto-approve profile selects and
    no analyst rejected."""
    should: list = [{"term": {"review.status": "approved"}}]
    auto = [to_query(r, ctx) for r in ctx.get("auto_approve", [])]
    if auto:
        should.append(
            {
                "bool": {
                    "should": auto,
                    "minimum_should_match": 1,
                    "must_not": [REJECTED],
                }
            }
        )
    return {"bool": {"should": should, "minimum_should_match": 1}}


def to_query(rules, ctx: dict, live_only: bool = True) -> dict:
    """The rules as a query on the indicators index.

    ``live_only=False`` leaves out the tombstone filter, for deltas, which
    carry removals too.
    """
    rules = _rules(rules)
    filters: list = [{"term": {"deleted": False}}] if live_only else []
    must_not: list = []
    if rules.types:
        filters.append({"terms": {"type.keyword": rules.types}})
    if rules.categories:
        filters.append({"terms": {"categories": rules.categories}})
    if rules.tlp_ceiling:
        must_not.append({"terms": {"tlp": _too_restrictive(rules.tlp_ceiling)}})
    if rules.tags:
        filters.append(
            {
                "bool": {
                    "should": [_tag_clause(t) for t in rules.tags],
                    "minimum_should_match": 1,
                }
            }
        )
    must_not += [_tag_clause(t) for t in rules.exclude_tags]
    if rules.min_score is not None:
        filters.append({"range": {"score": {"gte": rules.min_score}}})
    if rules.max_age_days:
        filters.append(
            {"range": {"last_seen": {"gte": ctx["now"] - rules.max_age_days * DAY}}}
        )
    if rules.sources:
        filters.append({"terms": {"source_keys": rules.sources}})
    if rules.exclude_sources:
        must_not.append(
            _only_from("source_keys", "source_count", rules.exclude_sources)
        )
    if rules.organisations:
        filters.append({"terms": {"organisation_ids": rules.organisations}})
    if rules.exclude_organisations:
        must_not.append(
            _only_from(
                "organisation_ids", "organisation_count", rules.exclude_organisations
            )
        )
    if rules.min_source_trust is not None:
        allowed, below = _trust_split(rules, ctx)
        if allowed is not None:
            filters.append({"terms": {"source_keys": allowed}})
        elif below:
            must_not.append(_only_from("source_keys", "source_count", below))
    if rules.to_ids:
        filters.append({"term": {"to_ids": True}})
    if rules.exclude_warninglisted:
        must_not.append({"exists": {"field": "warninglist_hits"}})
    if rules.exclude_validation_issues:
        must_not.append({"exists": {"field": "validation_issues"}})
    for list_id in rules.exclude_lists:
        # Members are private: looked up where they're kept, not stored on
        # the indicators (which anyone can query).
        must_not.append(
            {
                "terms": {
                    "uuid.keyword": {
                        "index": "misp-local-list-members",
                        "id": str(list_id),
                        "path": "members",
                    }
                }
            }
        )
    if rules.require_approval:
        filters.append(approved_query(ctx))
    elif rules.exclude_rejected:
        must_not.append(REJECTED)
    return {"bool": {"filter": filters, "must_not": must_not}}


def output_query(rules, ctx: dict, delta: bool = False) -> dict:
    """The rules for an output: live indicators, or for a delta, those that
    still match plus every tombstone (a removal a consumer must hear of)."""
    if not delta:
        return to_query(rules, ctx)
    return {
        "bool": {
            "should": [
                to_query(rules, ctx, live_only=False),
                {"term": {"deleted": True}},
            ],
            "minimum_should_match": 1,
        }
    }


# ── As a Lucene query, for Explore ────────────────────────────────────────

_LUCENE_SPECIAL = set('+-=&|><!(){}[]^"~*?:\\/ ')


def _quoted(value) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _pattern(pattern: str) -> str:
    """A tag pattern for query_string: wildcards kept, everything else escaped."""
    if not any(c in pattern for c in "*?"):
        return _quoted(pattern)
    return "".join(
        c if c in "*?" else ("\\" + c if c in _LUCENE_SPECIAL else c) for c in pattern
    )


def _any_of(field: str, values) -> str:
    return f"{field}:({' OR '.join(_quoted(v) for v in values)})"


def _present(field: str) -> list:
    """Every value of ``field`` across live indicators (sources, organisations)."""
    from app.services.opensearch import get_opensearch_client

    response = get_opensearch_client().search(
        index=indicators_repository.INDEX,
        body={
            "size": 0,
            "query": {"term": {"deleted": False}},
            "aggs": {"values": {"terms": {"field": field, "size": 10000}}},
        },
        ignore=[404],
    )
    buckets = (response.get("aggregations") or {}).get("values", {}).get("buckets", [])
    return [b["key"] for b in buckets]


def _outside(field: str, keys: list) -> str:
    """Indicators with at least one ``field`` value outside ``keys``: the
    query_string form of "not only from keys", over the values present now."""
    others = [v for v in _present(field) if v not in set(keys)]
    return _any_of(field, others) if others else "NOT *"


def to_lucene(rules, ctx: dict) -> dict:
    """The rules as a Lucene query on the indicators index, for Explore.

    Selects what ``to_query`` does. "Never only from" sources and
    organisations, and source trust, have no query_string form: they are
    written as "has a source outside these", listing the sources present
    now, so a source that appears later isn't covered (``snapshot``).
    """
    rules = _rules(rules)
    parts = ["deleted:false"]
    snapshot = False
    if rules.types:
        parts.append(_any_of("type.keyword", rules.types))
    if rules.categories:
        parts.append(_any_of("categories", rules.categories))
    if rules.tlp_ceiling:
        parts.append(f"NOT {_any_of('tlp', _too_restrictive(rules.tlp_ceiling))}")
    if rules.tags:
        parts.append(f"tags:({' OR '.join(_pattern(t) for t in rules.tags)})")
    if rules.exclude_tags:
        parts.append(
            f"NOT tags:({' OR '.join(_pattern(t) for t in rules.exclude_tags)})"
        )
    if rules.min_score is not None:
        parts.append(f"score:>={rules.min_score}")
    if rules.max_age_days:
        parts.append(f"last_seen:>={ctx['now'] - rules.max_age_days * DAY}")
    if rules.sources:
        parts.append(_any_of("source_keys", rules.sources))
    if rules.exclude_sources:
        parts.append(_outside("source_keys", rules.exclude_sources))
        snapshot = True
    if rules.organisations:
        parts.append(_any_of("organisation_ids", rules.organisations))
    if rules.exclude_organisations:
        parts.append(_outside("organisation_ids", rules.exclude_organisations))
        snapshot = True
    if rules.min_source_trust is not None:
        allowed, below = _trust_split(rules, ctx)
        if allowed is not None:
            parts.append(_any_of("source_keys", allowed) if allowed else "NOT *")
        elif below:
            parts.append(_outside("source_keys", below))
        snapshot = True
    if rules.to_ids:
        parts.append("to_ids:true")
    if rules.exclude_warninglisted:
        parts.append("NOT _exists_:warninglist_hits")
    if rules.exclude_validation_issues:
        parts.append("NOT _exists_:validation_issues")
    if rules.exclude_lists:
        # A list's members are private: Explore can't leave them out.
        snapshot = True
    if rules.require_approval:
        either = ["review.status:approved"]
        auto = [to_lucene(r, ctx) for r in ctx.get("auto_approve", [])]
        if auto:
            snapshot = snapshot or any(a["snapshot"] for a in auto)
            selected = " OR ".join(f"({a['query']})" for a in auto)
            either.append(f"(NOT review.status:rejected AND ({selected}))")
        parts.append(f"({' OR '.join(either)})")
    elif rules.exclude_rejected:
        parts.append("NOT review.status:rejected")
    return {"query": " AND ".join(parts), "snapshot": snapshot}


def _any_tag(tags: list[str], patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(t, p) for p in patterns for t in tags)


# Why an indicator fails a profile, as removals in membership deltas report it.
REASONS = (
    "deleted",
    "type",
    "category",
    "tlp",
    "tags",
    "excluded_tag",
    "no_longer_ids",
    "warninglisted",
    "validation",
    "score",
    "expired",
    "sources",
    "excluded_source",
    "organisations",
    "excluded_organisation",
    "trust",
    "rejected",
    "pending",
    "listed",
)


def _review_status(indicator: dict, ctx: dict) -> Optional[str]:
    """The analysts' decision on an indicator (approved, rejected, snoozed).

    An indicator built from an attribute doesn't carry it: it is read from
    the stored decisions, once per context.
    """
    if not indicator.get("_fresh"):
        return (indicator.get("review") or {}).get("status")
    if "_reviews" not in ctx:
        from app.repositories import indicator_reviews

        ctx["_reviews"] = indicator_reviews.statuses()
    return ctx["_reviews"].get(
        indicators_repository.indicator_uuid(
            indicator.get("type"), indicator.get("value")
        )
    )


def _listed(indicator: dict, list_ids: list[int], ctx: dict) -> bool:
    """Whether an indicator is on one of organisations' lists. One built
    from an attribute (no indicator yet) is matched now; others are looked
    up in the lists' members, once per context."""
    from app.repositories import local_warninglists

    if indicator.get("_fresh"):
        from app.database import SessionLocal

        key = tuple(sorted(list_ids))
        matchers = ctx.setdefault("_list_matchers", {})
        if key not in matchers:
            with SessionLocal() as db:
                matchers[key] = local_warninglists.LocalMatcher(db, only=key)
        value = str(indicator.get("value") or "")
        return bool(matchers[key].match([(indicator.get("type"), value)])[0])
    uuid = indicator.get("uuid") or indicators_repository.indicator_uuid(
        indicator.get("type"), indicator.get("value")
    )
    cache = ctx.setdefault("_list_members", {})
    for list_id in list_ids:
        if list_id not in cache:
            cache[list_id] = local_warninglists.members(list_id)
        if uuid in cache[list_id]:
            return True
    return False


def approved(indicator: dict, ctx: dict) -> bool:
    """``approved_query`` for one indicator."""
    status = _review_status(indicator, ctx)
    if status in ("approved", "rejected"):
        return status == "approved"
    return any(matches(r, indicator, ctx) for r in ctx.get("auto_approve", []))


def failing_rule(rules, indicator: Optional[dict], ctx: dict) -> Optional[str]:
    """The first rule an indicator fails (one of ``REASONS``), or None.

    ``to_query`` for one document: None means the profile selects it. A
    missing indicator (purged) is ``deleted``.
    """
    rules = _rules(rules)
    if not indicator or indicator.get("deleted"):
        return "deleted"
    if (rules.require_approval or rules.exclude_rejected) and _review_status(
        indicator, ctx
    ) == "rejected":
        return "rejected"
    if rules.types and indicator.get("type") not in rules.types:
        return "type"
    if rules.categories and not set(indicator.get("categories") or []) & set(
        rules.categories
    ):
        return "category"
    tlp = indicator.get("tlp")
    if rules.tlp_ceiling and tlp in _too_restrictive(rules.tlp_ceiling):
        return "tlp"
    tags = indicator.get("tags") or []
    if rules.tags and not _any_tag(tags, rules.tags):
        return "tags"
    if rules.exclude_tags and _any_tag(tags, rules.exclude_tags):
        return "excluded_tag"
    if rules.to_ids and not indicator.get("to_ids"):
        return "no_longer_ids"
    if rules.exclude_warninglisted and indicator.get("warninglist_hits"):
        return "warninglisted"
    if rules.exclude_validation_issues and indicator.get("validation_issues"):
        return "validation"
    if rules.exclude_lists and _listed(indicator, rules.exclude_lists, ctx):
        return "listed"

    score = indicator.get("score")
    if rules.min_score is not None and (score is None or score < rules.min_score):
        return "score"
    last_seen = indicator.get("last_seen")
    if rules.max_age_days and (
        last_seen is None or last_seen < ctx["now"] - rules.max_age_days * DAY
    ):
        return "expired"
    keys = indicator.get("source_keys") or []
    if rules.sources and not set(keys) & set(rules.sources):
        return "sources"
    if rules.exclude_sources and keys and set(keys) <= set(rules.exclude_sources):
        return "excluded_source"
    organisations = indicator.get("organisation_ids") or []
    if rules.organisations and not set(organisations) & set(rules.organisations):
        return "organisations"
    if (
        rules.exclude_organisations
        and organisations
        and set(organisations) <= set(rules.exclude_organisations)
    ):
        return "excluded_organisation"
    if rules.min_source_trust is not None:
        allowed, below = _trust_split(rules, ctx)
        if allowed is not None and not set(keys) & set(allowed):
            return "trust"
        if allowed is None and below and keys and set(keys) <= set(below):
            return "trust"
    if rules.require_approval and not approved(indicator, ctx):
        return "pending"
    return None


def matches(rules, indicator: dict, ctx: dict) -> bool:
    """Whether one indicator passes the rules (``to_query``, for one document)."""
    return failing_rule(rules, indicator, ctx) is None


def _event_source(event: dict) -> dict:
    """The event's source, as indicators record it (see indicators._Events)."""
    source = event.get("source") or {}
    if not source.get("type"):
        source = {"type": "local" if event.get("organisation") else "unknown"}
    return {
        "type": source.get("type"),
        "id": source.get("id"),
        "name": source.get("name") or source.get("type"),
        "event_count": 1,
    }


def attribute_indicator(
    attribute: dict, event: Optional[dict] = None, ctx: Optional[dict] = None
) -> dict:
    """An indicator from one attribute and its event, for values without one.

    Its source and organisation come from the event (unknown without one),
    its last seen from the attribute, and with ``ctx`` its score is computed
    as for any indicator, so every rule can be judged.
    """
    from app.services import scoring

    event = event or {}
    # Tags as stored (dicts) or as outputs carry them (names).
    tag_names = [
        t.get("name") if isinstance(t, dict) else t
        for t in (attribute.get("tags") or []) + (event.get("tags") or [])
        if (t.get("name") if isinstance(t, dict) else t)
    ]
    tag_names += [
        indicators_repository.validation_tag(i)
        for i in attribute.get("validation_issues") or []
    ]
    tags, tlp, _ = indicators_repository.merge_tags(
        TLP_ALIASES.get(t.lower(), t) for t in tag_names
    )
    source = _event_source(event)
    embedded = event.get("organisation") or {}
    org_id = embedded.get("id") or event.get("orgc_id") or event.get("org_id")
    seen = attribute.get("last_seen") or attribute.get("timestamp")
    indicator = {
        "type": attribute.get("type"),
        "value": attribute.get("value"),
        "categories": [attribute["category"]] if attribute.get("category") else [],
        "to_ids": bool(attribute.get("to_ids")),
        "tags": tags,
        "tlp": TLP_ALIASES.get(tlp, tlp),
        "warninglist_hits": attribute.get("warninglist_hits") or [],
        "validation_issues": attribute.get("validation_issues") or [],
        "sources": [source],
        "source_keys": [indicators_repository.source_key(source)],
        "organisations": (
            [{"id": org_id, "name": embedded.get("name"), "event_count": 1}]
            if org_id is not None
            else []
        ),
        "organisation_ids": [org_id] if org_id is not None else [],
        "last_seen": int(seen) if seen else None,
        "sightings": {},
        # Its review decision is stored, not on it (see _review_status).
        "_fresh": True,
    }
    if ctx is not None:
        indicator["score"], _ = scoring.score(indicator, ctx["scoring"], ctx["now"])
    return indicator


def indicators_for(attributes: Iterable[dict]) -> dict[str, dict]:
    """The live indicators behind attributes, by indicator uuid."""
    return indicators_repository.get_indicators(
        indicators_repository.indicator_uuid(a.get("type"), a.get("value"))
        for a in attributes
    )


def attribute_matches(
    rules, attribute: dict, found: dict, ctx: dict, event: Optional[dict] = None
) -> bool:
    """Whether an attribute passes: its indicator does (or, without one, an
    indicator built from the attribute does), and its exclusions hold on the
    attribute as it is now, whatever its indicator still says."""
    rules = _rules(rules)
    key = indicators_repository.indicator_uuid(
        attribute.get("type"), attribute.get("value")
    )
    current = attribute_indicator(attribute, event, ctx)
    indicator = found.get(key)
    if indicator is None:
        return matches(rules, current, ctx)
    return matches(rules, indicator, ctx) and matches(
        exclusions_only(rules), current, ctx
    )


def exclusions_only(rules) -> profile_schemas.ProfileRules:
    """The rules that keep things out, without the ones that select.

    For sends from notebooks and reactor scripts: code chooses what to send,
    but a profile's TLP ceiling, excluded tags, warninglists and validation
    issues still hold, and so does an analyst's rejection.
    """
    rules = _rules(rules)
    return profile_schemas.ProfileRules(
        tlp_ceiling=rules.tlp_ceiling,
        exclude_tags=rules.exclude_tags,
        to_ids=False,
        exclude_warninglisted=rules.exclude_warninglisted,
        exclude_validation_issues=rules.exclude_validation_issues,
        exclude_lists=rules.exclude_lists,
        exclude_rejected=rules.exclude_rejected or rules.require_approval,
    )


def preview(rules, ctx: Optional[dict] = None) -> dict:
    """How many live indicators the rules select, and a few of them."""
    from app.services.opensearch import get_opensearch_client

    ctx = ctx or context()
    response = get_opensearch_client().search(
        index=indicators_repository.INDEX,
        body={
            "query": to_query(rules, ctx),
            "size": PREVIEW_SAMPLE,
            "track_total_hits": True,
            "sort": [{"score": {"order": "desc", "missing": "_last"}}],
            "_source": ["uuid", "type", "value", "score", "tlp", "last_seen"],
        },
        ignore=[404],
    )
    hits = response.get("hits", {})
    return {
        "count": hits.get("total", {}).get("value", 0),
        "sample": [h["_source"] for h in hits.get("hits", [])],
    }
