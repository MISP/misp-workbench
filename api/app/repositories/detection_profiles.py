"""Detection profiles: "what goes to which control", defined once.

A profile's rules select consolidated indicators. They are evaluated two
ways, kept equivalent by tests:

- ``to_query``: an OpenSearch query on the indicators index, for outputs that
  read many indicators (exports, feeds, the indicators search, counts);
- ``matches``: a check on one indicator, for outputs that judge records one
  at a time (sinks, /lookup, restSearch).

A value too new to have an indicator yet is judged on its attribute
(``attribute_indicator``): the rules it can answer (type, category, tags,
TLP, to_ids, warninglists, validation) apply, the ones it can't (score,
age, sources, trust) don't, as the value is fresh.
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
        }


def create_profile(db: Session, profile: profile_schemas.DetectionProfileCreate):
    db_profile = profile_models.DetectionProfile(
        name=profile.name,
        description=profile.description,
        granularity=profile.granularity,
        rules=profile.rules.model_dump(),
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
    db.delete(db_profile)
    db.commit()


# ── Evaluation ────────────────────────────────────────────────────────────


def context(now: Optional[int] = None) -> dict:
    """What evaluating rules needs besides the indicator: time and trust."""
    from app.services import scoring

    trust = scoring.load_config().get("_trust", {})
    return {
        "now": int(time.time()) if now is None else now,
        # Source key -> score modifier, for feeds and servers that have one.
        "trust": {
            f"{kind}:{key}": modifier
            for kind in ("feed", "server")
            for key, (modifier, _cap) in trust.get(kind, {}).items()
        },
    }


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


def _any_tag(tags: list[str], patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(t, p) for p in patterns for t in tags)


def matches(rules, indicator: dict, ctx: dict) -> bool:
    """Whether one indicator passes the rules (``to_query``, for one document).

    An indicator built from a lone attribute (``partial``) skips the rules it
    can't answer: score, age, sources, organisations and trust.
    """
    rules = _rules(rules)
    partial = indicator.get("partial", False)
    if indicator.get("deleted"):
        return False
    if rules.types and indicator.get("type") not in rules.types:
        return False
    if rules.categories and not set(indicator.get("categories") or []) & set(
        rules.categories
    ):
        return False
    tlp = indicator.get("tlp")
    if rules.tlp_ceiling and tlp in _too_restrictive(rules.tlp_ceiling):
        return False
    tags = indicator.get("tags") or []
    if rules.tags and not _any_tag(tags, rules.tags):
        return False
    if rules.exclude_tags and _any_tag(tags, rules.exclude_tags):
        return False
    if rules.to_ids and not indicator.get("to_ids"):
        return False
    if rules.exclude_warninglisted and indicator.get("warninglist_hits"):
        return False
    if rules.exclude_validation_issues and indicator.get("validation_issues"):
        return False
    if partial:
        return True

    score = indicator.get("score")
    if rules.min_score is not None and (score is None or score < rules.min_score):
        return False
    last_seen = indicator.get("last_seen")
    if rules.max_age_days and (
        last_seen is None or last_seen < ctx["now"] - rules.max_age_days * DAY
    ):
        return False
    keys = indicator.get("source_keys") or []
    if rules.sources and not set(keys) & set(rules.sources):
        return False
    if rules.exclude_sources and keys and set(keys) <= set(rules.exclude_sources):
        return False
    organisations = indicator.get("organisation_ids") or []
    if rules.organisations and not set(organisations) & set(rules.organisations):
        return False
    if (
        rules.exclude_organisations
        and organisations
        and set(organisations) <= set(rules.exclude_organisations)
    ):
        return False
    if rules.min_source_trust is not None:
        allowed, below = _trust_split(rules, ctx)
        if allowed is not None and not set(keys) & set(allowed):
            return False
        if allowed is None and below and keys and set(keys) <= set(below):
            return False
    return True


def attribute_indicator(attribute: dict, event: Optional[dict] = None) -> dict:
    """A partial indicator from one attribute, for values without one yet."""
    # Tags as stored (dicts) or as outputs carry them (names).
    tag_names = [
        t.get("name") if isinstance(t, dict) else t
        for t in (attribute.get("tags") or []) + ((event or {}).get("tags") or [])
        if (t.get("name") if isinstance(t, dict) else t)
    ]
    tag_names += [
        indicators_repository.validation_tag(i)
        for i in attribute.get("validation_issues") or []
    ]
    tags, tlp, _ = indicators_repository.merge_tags(
        TLP_ALIASES.get(t.lower(), t) for t in tag_names
    )
    return {
        "partial": True,
        "type": attribute.get("type"),
        "value": attribute.get("value"),
        "categories": [attribute["category"]] if attribute.get("category") else [],
        "to_ids": bool(attribute.get("to_ids")),
        "tags": tags,
        "tlp": TLP_ALIASES.get(tlp, tlp),
        "warninglist_hits": attribute.get("warninglist_hits") or [],
        "validation_issues": attribute.get("validation_issues") or [],
    }


def indicators_for(attributes: Iterable[dict]) -> dict[str, dict]:
    """The live indicators behind attributes, by indicator uuid."""
    return indicators_repository.get_indicators(
        indicators_repository.indicator_uuid(a.get("type"), a.get("value"))
        for a in attributes
    )


def attribute_matches(
    rules, attribute: dict, found: dict, ctx: dict, event: Optional[dict] = None
) -> bool:
    """Whether an attribute's indicator (or, failing one, the attribute) passes."""
    key = indicators_repository.indicator_uuid(
        attribute.get("type"), attribute.get("value")
    )
    indicator = found.get(key) or attribute_indicator(attribute, event)
    return matches(rules, indicator, ctx)


def exclusions_only(rules) -> profile_schemas.ProfileRules:
    """The rules that keep things out, without the ones that select.

    For sends from notebooks and reactor scripts: code chooses what to send,
    but a profile's TLP ceiling, excluded tags, warninglists and validation
    issues still hold.
    """
    rules = _rules(rules)
    return profile_schemas.ProfileRules(
        tlp_ceiling=rules.tlp_ceiling,
        exclude_tags=rules.exclude_tags,
        to_ids=False,
        exclude_warninglisted=rules.exclude_warninglisted,
        exclude_validation_issues=rules.exclude_validation_issues,
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
