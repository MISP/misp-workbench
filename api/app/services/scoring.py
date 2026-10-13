"""Confidence scores for consolidated indicators.

A score from 0 to 100 says how much an indicator can be acted on now:

- **base**: the best source it comes from (``base_by_source``), plus a little
  per further independent source (corroboration);
- **decay**: halved every ``half_life_days`` of its type since ``last_seen``
  (which positive sightings move), so a two-year-old C2 IP fades out while a
  hash keeps its score;
- **sightings**: positive ones add a little, false positives take off a lot;
  an expiration newer than any positive sighting caps it;
- **warninglists**: being on one costs a strong penalty;
- **source trust**: each feed, MISP server and organisation can carry a
  ``score_modifier`` and a ``score_cap``. The best source wins: the highest
  base + modifier sets the base, the most favourable organisation modifier
  applies, and a cap holds only when every source (and, separately, every
  organisation) reporting the value is capped.

Each step is kept as a breakdown entry, so "why is this 42?" has an answer.
"""

import copy
import math
from datetime import datetime, timezone
from typing import Optional

from app.defaults.runtime_settings_defaults import DEFAULT_SETTINGS

DEFAULTS = DEFAULT_SETTINGS["scoring"]
DAY = 86400


def config(stored: Optional[dict] = None) -> dict:
    """The scoring settings, stored values over the defaults.

    A saved namespace replaces the defaults wholesale; merging here means a
    settings dict saved before a new key existed still gets that key.
    """
    merged = copy.deepcopy(DEFAULTS)
    for key, value in (stored or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


class InvalidScoringConfig(ValueError):
    pass


NUMBERS = (
    "corroboration_per_source",
    "corroboration_max",
    "default_half_life_days",
    "sighting_boost_max",
    "false_positive_penalty",
    "false_positive_penalty_max",
    "warninglist_penalty",
    "expiration_cap",
    "decayed_below",
    "refresh_step",
)
MAPS = ("base_by_source", "half_life_days")


def validate(stored: dict) -> None:
    """Refuse settings a rebuild would trip over, naming the bad key."""

    def number(key: str, value) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidScoringConfig(f"{key} must be a number")
        if value < 0:
            raise InvalidScoringConfig(f"{key} must be >= 0")

    cfg = config(stored)
    if not isinstance(cfg.get("enabled"), bool):
        raise InvalidScoringConfig("enabled must be true or false")
    for key in NUMBERS:
        number(key, cfg.get(key))
    for key in MAPS:
        if not isinstance(cfg.get(key), dict):
            raise InvalidScoringConfig(f"{key} must be an object")
        for name, value in cfg[key].items():
            number(f"{key}.{name}", value)


def _load_trust(db) -> dict:
    """Modifier and cap of every source that has either, by kind and key."""
    from app.models import feed as feed_models
    from app.models import organisation as organisation_models
    from app.models import server as server_models

    trust: dict = {"feed": {}, "server": {}, "organisation": {}}
    for kind, model, key in (
        ("feed", feed_models.Feed, "id"),
        ("server", server_models.Server, "id"),
        # By id, never name: names aren't unique (see indicators._Events).
        ("organisation", organisation_models.Organisation, "id"),
    ):
        rows = db.query(
            getattr(model, key), model.score_modifier, model.score_cap
        ).filter((model.score_modifier != 0) | (model.score_cap.isnot(None)))
        for row_key, modifier, cap in rows:
            trust[kind][row_key] = (modifier or 0, cap)
    return trust


def load_config() -> dict:
    """The settings plus every source's trust, for one sync or rebuild."""
    from app.database import SessionLocal
    from app.services.runtime_settings import RuntimeSettings

    with SessionLocal() as db:
        cfg = config(RuntimeSettings(db).get("scoring"))
        cfg["_trust"] = _load_trust(db)
        return cfg


def _trust(cfg: dict, kind: str, key) -> tuple[int, Optional[int]]:
    return cfg.get("_trust", {}).get(kind, {}).get(key, (0, None))


def _source_trust(cfg: dict, source: dict) -> tuple[int, Optional[int]]:
    if source.get("type") in ("feed", "server"):
        return _trust(cfg, source["type"], source.get("id"))
    return 0, None


def _label(source: dict) -> str:
    if source.get("type") in ("feed", "server"):
        return f"{source['type']}: {source['name']}"
    return f"{source.get('type')} source"


def _cap(entries: list[tuple[str, Optional[int]]]) -> tuple[float, list[str]]:
    """The highest cap among entries (uncapped ones count as 100), and who set it."""
    if not entries or any(cap is None for _, cap in entries):
        return 100.0, []
    top = max(cap for _, cap in entries)
    return float(top), [name for name, cap in entries if cap == top]


def half_life_days(cfg: dict, type_: str) -> float:
    days = cfg["half_life_days"].get(type_)
    return float(cfg["default_half_life_days"] if days is None else days)


def _entry(factor: str, points: float, detail: str) -> dict:
    return {"factor": factor, "points": round(points), "detail": detail}


def _date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def score(indicator: dict, cfg: dict, now: int) -> tuple[Optional[int], list]:
    """The indicator's score and its breakdown; (None, []) when scoring is off."""
    if not cfg.get("enabled", True):
        return None, []

    breakdown = []
    bases = cfg["base_by_source"]
    sources = indicator.get("sources") or [{"type": "unknown", "name": "unknown"}]

    def source_base(source):
        return float(bases.get(source.get("type"), bases.get("unknown", 50)))

    # The best source: the highest base once its own trust modifier is in.
    best = max(sources, key=lambda s: source_base(s) + _source_trust(cfg, s)[0])
    base = source_base(best)
    breakdown.append(_entry("base", base, _label(best)))
    points = base
    modifier = _source_trust(cfg, best)[0]
    if modifier:
        breakdown.append(_entry("source_trust", modifier, _label(best)))
        points += modifier

    organisations = indicator.get("organisations") or []
    if organisations:
        trusted = max(
            organisations,
            key=lambda o: _trust(cfg, "organisation", o.get("id"))[0],
        )
        org_modifier = _trust(cfg, "organisation", trusted.get("id"))[0]
        if org_modifier:
            breakdown.append(
                _entry(
                    "organisation_trust",
                    org_modifier,
                    f"organisation: {trusted.get('name')}",
                )
            )
            points += org_modifier

    if len(sources) > 1:
        bonus = min(
            cfg["corroboration_max"],
            cfg["corroboration_per_source"] * (len(sources) - 1),
        )
        breakdown.append(_entry("corroboration", bonus, f"{len(sources)} sources"))
        points += bonus

    days = half_life_days(cfg, indicator.get("type"))
    last_seen = indicator.get("last_seen")
    if days > 0 and last_seen:
        age = max(now - int(last_seen), 0) / DAY
        factor = 0.5 ** (age / days)
        decayed = points * factor
        breakdown.append(
            _entry(
                "decay",
                decayed - points,
                f"last seen {age:.0f} days ago, half-life {days:g} days",
            )
        )
        points = decayed

    sightings = indicator.get("sightings") or {}
    positive = sightings.get("positive") or 0
    if positive:
        boost = min(cfg["sighting_boost_max"], 5 * math.log2(1 + positive))
        breakdown.append(_entry("sightings", boost, f"{positive} positive sighting(s)"))
        points += boost
    false_positives = sightings.get("false_positive") or 0
    if false_positives:
        penalty = min(
            cfg["false_positive_penalty_max"],
            cfg["false_positive_penalty"] * false_positives,
        )
        breakdown.append(
            _entry(
                "false_positives",
                -penalty,
                f"{false_positives} false-positive sighting(s)",
            )
        )
        points -= penalty

    hits = indicator.get("warninglist_hits") or []
    if hits:
        penalty = cfg["warninglist_penalty"]
        breakdown.append(_entry("warninglist", -penalty, f"on {', '.join(hits)}"))
        points -= penalty

    points = min(max(points, 0.0), 100.0)

    source_cap, capped_by = _cap(
        [(_label(s), _source_trust(cfg, s)[1]) for s in sources]
    )
    org_cap, org_capped_by = _cap(
        [
            (
                f"organisation: {o.get('name')}",
                _trust(cfg, "organisation", o.get("id"))[1],
            )
            for o in organisations
        ]
    )
    cap = min(source_cap, org_cap)
    if cap < points:
        by = capped_by if source_cap <= org_cap else org_capped_by
        breakdown.append(
            _entry("cap", cap - points, f"capped at {cap:g} by {', '.join(by)}")
        )
        points = cap

    expired_at = sightings.get("last_expiration_at")
    if expired_at and expired_at >= (sightings.get("last_positive_at") or 0):
        capped = min(points, float(cfg["expiration_cap"]))
        if capped < points:
            breakdown.append(
                _entry(
                    "expiration",
                    capped - points,
                    f"expired by a sighting on {_date(int(expired_at))}",
                )
            )
            points = capped

    return int(round(points)), breakdown


def needs_rewrite(stored: Optional[int], new: Optional[int], cfg: dict) -> bool:
    """Whether a changed score is worth rewriting the indicator for."""
    if stored is None or new is None:
        return stored != new
    threshold = cfg["decayed_below"]
    return abs(new - stored) >= cfg["refresh_step"] or (
        (new < threshold) != (stored < threshold)
    )


def decayed(value: Optional[int], cfg: dict, threshold: Optional[int] = None) -> bool:
    if value is None:
        return False
    return value < (cfg["decayed_below"] if threshold is None else threshold)
