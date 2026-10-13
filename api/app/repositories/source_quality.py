"""How good each source's indicators are, from the consolidated indicators.

Per feed, MISP server, local source and organisation, over the live
indicators it reports:

- **volume**: how many indicators;
- **exclusive**: how many no other source reports (the rest overlap, and the
  sources it overlaps most with are listed);
- **hit rate**: the share sighted (positive sighting) within the window;
- **false-positive rate**: the share reported benign within the window;
- **average score**, and the share that has decayed.

The false-positive rate also drives **adaptive trust** (scoring setting
``adaptive_trust``, off by default): a source's effective modifier drops by
``adaptive_points_per_percent`` per percent of false positives, up to
``adaptive_max_penalty``, once it has ``adaptive_min_indicators``. It is off
by default because anyone who can report sightings can report false
positives against a source's values.
"""

import json
import logging
import time
from typing import Optional

from app.repositories import indicators as indicators_repository
from app.services import scoring
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client

logger = logging.getLogger(__name__)

DAY = 86400
# Sources (and organisations) one statistics query covers.
MAX_SOURCES = 1000
TOP_OVERLAPS = 5
# Adaptive penalties are recomputed at most this often (a sync runs every
# 15 seconds; the rates move slowly).
ADAPTIVE_CACHE_KEY = "indicators:adaptive_trust"
ADAPTIVE_CACHE_SECONDS = 600

# kind -> the indicator field holding its keys and the count of them.
FIELDS = {
    "source": ("source_keys", "source_count"),
    "organisation": ("organisation_ids", "organisation_count"),
}


def _aggs(field: str, count_field: str, since: int, decayed_below: int) -> dict:
    return {
        "terms": {"field": field, "size": MAX_SOURCES},
        "aggs": {
            "exclusive": {"filter": {"term": {count_field: 1}}},
            "overlaps": {"terms": {"field": field, "size": TOP_OVERLAPS + 1}},
            "hits": {
                "filter": {"range": {"sightings.last_positive_at": {"gte": since}}}
            },
            "false_positives": {
                "filter": {
                    "range": {"sightings.last_false_positive_at": {"gte": since}}
                }
            },
            "average_score": {"avg": {"field": "score"}},
            "decayed": {"filter": {"range": {"score": {"lt": decayed_below}}}},
        },
    }


def _rate(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def adaptive_penalty(cfg: dict, indicators: int, false_positive_rate: float) -> int:
    """Points a source's trust drops for its false-positive rate."""
    if indicators < cfg["adaptive_min_indicators"]:
        return 0
    return int(
        min(
            cfg["adaptive_max_penalty"],
            round(false_positive_rate * 100 * cfg["adaptive_points_per_percent"]),
        )
    )


def _names() -> dict:
    """Display names of feeds, servers and organisations, by key."""
    from app.database import SessionLocal
    from app.models import feed as feed_models
    from app.models import organisation as organisation_models
    from app.models import server as server_models

    names = {"local": "local", "unknown": "unknown"}
    with SessionLocal() as db:
        for kind, model in (
            ("feed", feed_models.Feed),
            ("server", server_models.Server),
        ):
            for row_id, name in db.query(model.id, model.name):
                names[f"{kind}:{row_id}"] = name
        for row_id, name in db.query(
            organisation_models.Organisation.id, organisation_models.Organisation.name
        ):
            names[f"organisation:{row_id}"] = name
    return names


def _key_parts(kind: str, key) -> tuple[str, Optional[int]]:
    """(kind, id) of a source key or organisation id."""
    if kind == "organisation":
        return "organisation", int(key)
    if ":" in str(key):
        source_kind, source_id = str(key).split(":", 1)
        return source_kind, int(source_id)
    return str(key), None


def _name_key(kind: str, key) -> str:
    return f"organisation:{key}" if kind == "organisation" else str(key)


def statistics(
    cfg: Optional[dict] = None, only: Optional[tuple[str, object]] = None
) -> dict:
    """Quality of every source and organisation (or of ``only``: (kind, key)).

    ``kind`` is ``source`` (key ``feed:3``, ``server:2``, ``local``) or
    ``organisation`` (key: its id).
    """
    cfg = cfg or scoring.load_config()
    now = int(time.time())
    since = now - int(cfg["adaptive_window_days"] * DAY)
    client = get_opensearch_client()
    names = _names()
    trust = cfg.get("_trust", {})

    result: dict = {
        "window_days": cfg["adaptive_window_days"],
        "adaptive_trust": cfg["adaptive_trust"],
        "sources": [],
        "organisations": [],
    }
    for kind, (field, count_field) in FIELDS.items():
        if only and only[0] != kind:
            continue
        query: dict = {"bool": {"filter": [{"term": {"deleted": False}}]}}
        if only:
            query["bool"]["filter"].append({"term": {field: only[1]}})
        response = client.search(
            index=indicators_repository.INDEX,
            body={
                "size": 0,
                "query": query,
                "aggs": {"by": _aggs(field, count_field, since, cfg["decayed_below"])},
            },
            ignore=[404],
        )
        buckets = (response.get("aggregations") or {}).get("by", {}).get("buckets", [])
        for bucket in buckets:
            key = bucket["key"]
            if only and str(key) != str(only[1]):
                # Its overlaps share the indicators but aren't what was asked.
                continue
            volume = bucket["doc_count"]
            exclusive = bucket["exclusive"]["doc_count"]
            false_positive_rate = _rate(bucket["false_positives"]["doc_count"], volume)
            entity_kind, entity_id = _key_parts(kind, key)
            modifier, cap = trust.get(entity_kind, {}).get(entity_id, (0, None))
            # local and unknown have no record whose trust could be lowered.
            penalty = (
                adaptive_penalty(cfg, volume, false_positive_rate)
                if entity_kind in ("feed", "server", "organisation")
                else 0
            )
            average = bucket["average_score"].get("value")
            result["sources" if kind == "source" else "organisations"].append(
                {
                    "key": str(key),
                    "kind": entity_kind,
                    "id": entity_id,
                    "name": names.get(_name_key(kind, key), str(key)),
                    "indicators": volume,
                    "exclusive": exclusive,
                    "overlap_rate": _rate(volume - exclusive, volume),
                    "top_overlaps": [
                        {
                            "key": str(o["key"]),
                            "name": names.get(_name_key(kind, o["key"]), str(o["key"])),
                            "indicators": o["doc_count"],
                        }
                        for o in bucket["overlaps"]["buckets"]
                        if str(o["key"]) != str(key)
                    ][:TOP_OVERLAPS],
                    "hit_rate": _rate(bucket["hits"]["doc_count"], volume),
                    "false_positive_rate": false_positive_rate,
                    "average_score": round(average, 1) if average is not None else None,
                    "decayed_rate": _rate(bucket["decayed"]["doc_count"], volume),
                    "score_modifier": modifier,
                    "score_cap": cap,
                    # What adaptive trust takes off: applied only when it is on,
                    # shown either way.
                    "adaptive_penalty": penalty,
                    "effective_modifier": modifier
                    - (penalty if cfg["adaptive_trust"] else 0),
                }
            )
    return result


def adaptive_penalties(cfg: dict) -> dict:
    """Penalties (and the rates behind them) by kind and id, cached briefly.

    ``{"feed": {3: [12, 0.12]}, "server": {...}, "organisation": {...}}``;
    empty when adaptive trust is off.
    """
    if not cfg.get("adaptive_trust"):
        return {}
    redis = get_redis_client()
    cached = redis.get(ADAPTIVE_CACHE_KEY)
    if cached:
        raw = json.loads(cached)
        return {kind: {int(k): v for k, v in by.items()} for kind, by in raw.items()}

    penalties: dict = {"feed": {}, "server": {}, "organisation": {}}
    stats = statistics(cfg)
    for entry in stats["sources"] + stats["organisations"]:
        if entry["adaptive_penalty"] and entry["kind"] in penalties:
            penalties[entry["kind"]][entry["id"]] = [
                entry["adaptive_penalty"],
                entry["false_positive_rate"],
            ]
    redis.set(ADAPTIVE_CACHE_KEY, json.dumps(penalties), ex=ADAPTIVE_CACHE_SECONDS)
    return penalties


def forget_adaptive_penalties() -> None:
    get_redis_client().delete(ADAPTIVE_CACHE_KEY)
