import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer

from app.database import SessionLocal
from app.models import audit_log as audit_log_models
from app.models import hunt as hunt_models
from app.models import lab as lab_models
from app.models import notification as notification_models
from app.models import feed as feed_models
from app.models import reactor as reactor_models
from app.repositories import analyst_data as analyst_data_repository
from app.repositories import attributes as attributes_repository
from app.repositories import correlations as correlations_repository
from app.repositories import feeds as feeds_repository
from app.repositories import reactor as reactor_repository
from app.repositories import servos as servos_repository
from app.repositories import events as events_repository
from app.repositories import hunts as hunts_repository
from app.repositories import objects as objects_repository
from app.repositories import organisations as organisations_repository
from app.repositories import tags as tags_repository
from app.repositories import users as user_repository
from app.schemas import analyst_data as analyst_data_schemas
from app.schemas import attribute as attribute_schemas
from app.schemas import feed as feed_schemas
from app.schemas import reactor as reactor_schemas
from app.schemas import servo as servo_schemas
from app.schemas import event as event_schemas
from app.schemas import hunt as hunt_schemas
from app.schemas import object as object_schemas
from app.schemas import organisations as organisation_schemas
from app.schemas import tag as tag_schemas
from app.schemas import user as user_schemas
from app.services.opensearch import get_opensearch_client
from app.services.redis import get_redis_client
from app.services.runtime_settings_provider import get_runtime_settings
from app.services.tech_lab.lab import nbformat_io
from app.services.tech_lab.servos import chain as servo_chain
from app.worker import tasks

app = typer.Typer()


@app.command()
def create_organisation(name: str, created_by: int = 0, local: bool = True):
    db = SessionLocal()

    db_organisation = organisations_repository.get_organisation_by_name(
        db, organisation_name=name
    )
    if db_organisation:
        print(f"Organisation '{name}' already exists.")
        return

    organisation = organisation_schemas.OrganisationCreate(
        name=name, created_by=created_by, local=local
    )
    organisation_db = organisations_repository.create_organisation(
        db, organisation=organisation
    )
    print(f"Created organisation id={organisation_db.id}")  # noqa: T201


@app.command()
def create_user(
    email: str,
    password: str,
    org_id: Optional[int] = typer.Option(None, "--org-id", help="Organisation id"),
    org_name: Optional[str] = typer.Option(
        None, "--org-name", help="Organisation name (alternative to --org-id)"
    ),
    role_id: int = typer.Option(..., "--role-id", help="Role id"),
):
    if (org_id is None) == (org_name is None):
        print("Error: pass exactly one of --org-id or --org-name.")
        raise typer.Exit(code=1)

    db = SessionLocal()

    db_user = user_repository.get_user_by_email(db, email=email)
    if db_user:
        print(f"User already exists with id={db_user.id}.")
        return

    if org_name is not None:
        db_org = organisations_repository.get_organisation_by_name(
            db, organisation_name=org_name
        )
        if db_org is None:
            print(f"Error: organisation '{org_name}' not found.")
            raise typer.Exit(code=1)
        org_id = db_org.id

    user = user_schemas.UserCreate(
        email=email, password=password, org_id=org_id, role_id=role_id
    )
    user_db = user_repository.create_user(db, user=user)
    print(f"Created user id={user_db.id}")  # noqa: T201


@app.command()
def load_galaxies(user_id: Optional[int] = None):
    tasks.load_galaxies.delay(user_id)


@app.command()
def load_taxonomies(user_id: Optional[int] = None):
    tasks.load_taxonomies.delay()


@app.command()
def seed_lab_library(
    owner_email: str = typer.Option(
        ...,
        "--owner-email",
        help="Email of the user that will own the seeded notebooks",
    ),
    directory: Path = typer.Option(
        Path("/code/lab_library"),
        "--directory",
        help="Directory containing .ipynb files to seed",
    ),
):
    """Upsert notebooks from .ipynb files into the Library section.

    Each file becomes a notebook with visibility=library, named after the file
    stem. Re-running the command updates the source of existing library
    notebooks (matched by name) without touching personal forks.
    """
    if not directory.exists() or not directory.is_dir():
        typer.echo(f"Directory not found: {directory}", err=True)
        raise typer.Exit(code=1)

    db = SessionLocal()
    owner = user_repository.get_user_by_email(db, email=owner_email)
    if owner is None:
        typer.echo(f"User not found: {owner_email}", err=True)
        raise typer.Exit(code=1)

    files = sorted(directory.glob("*.ipynb"))
    if not files:
        typer.echo(f"No .ipynb files in {directory}")
        return

    created = updated = 0
    for path in files:
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            typer.echo(f"Skipping {path.name}: invalid JSON ({e})", err=True)
            continue
        if not isinstance(blob, dict) or "cells" not in blob:
            typer.echo(f"Skipping {path.name}: not a valid .ipynb", err=True)
            continue
        source, fallback_name = nbformat_io.from_nbformat(blob)
        # Prefer the file stem so re-running with renamed metadata still
        # matches the same library entry.
        name = path.stem
        description = ((blob.get("metadata") or {}).get("misp_workbench") or {}).get(
            "description"
        ) or fallback_name

        existing = (
            db.query(lab_models.LabNotebook)
            .filter(
                lab_models.LabNotebook.visibility == "library",
                lab_models.LabNotebook.name == name,
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if existing is None:
            row = lab_models.LabNotebook(
                user_id=owner.id,
                folder_id=None,
                visibility="library",
                name=name,
                description=description,
                source=source,
                cell_outputs={},
                created_at=now,
            )
            db.add(row)
            created += 1
        else:
            existing.source = source
            existing.description = description
            existing.cell_outputs = {}
            existing.last_executed_at = None
            existing.updated_at = now
            updated += 1
    db.commit()
    typer.echo(f"Library seeded: {created} created, {updated} updated.")


DOCS_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "docs"
DOCS_ORG_NAME = "MISP Workbench Docs"
DOCS_USER_EMAIL = "admin@admin.test"
DOCS_USER_PASSWORD = "admin"  # noqa: S105 — local-only docs user
DOCS_USER_ROLE_ID = 1  # admin


def _clear_event_children(client, event_uuid: str) -> None:
    """Drop everything hanging off a fixture event before re-creating it.

    The fixtures pin every uuid, so re-seeding overwrites its own rows - but
    anything added to a fixture event by hand keeps its generated uuid and
    would otherwise pile up beside them, run after run. A docs fixture is
    meant to be exactly what the fixture file says, so its children are
    cleared first. Only these four events are touched.
    """
    for index, field in (
        ("misp-attributes", "event_uuid"),
        ("misp-objects", "event_uuid"),
        # This index maps its uuid fields as analyzed text, so a term query
        # on the bare field never matches a full uuid.
        ("misp-object-references", "event_uuid.keyword"),
    ):
        client.delete_by_query(
            index=index,
            body={"query": {"term": {field: event_uuid}}},
            refresh=True,
            ignore=[404],
        )


def _ensure_tag(db, tag: dict):
    """Create the fixture tag, or bring an existing one back to its colour.

    Taxonomy loading only creates a tag it does not already find, so a tag
    that first appeared through ad-hoc tagging keeps its hashed colour
    forever. Docs screenshots need the real one, so it is set either way.
    """
    db_tag = tags_repository.get_tag_by_name(db, tag_name=tag["name"])
    fields = {
        "name": tag["name"],
        "colour": tag["colour"],
        "exportable": True,
        "hide_tag": False,
        "is_galaxy": tag.get("is_galaxy", False),
        "is_custom_galaxy": False,
        "local_only": False,
    }

    if db_tag is None:
        tags_repository.create_tag(db, tag=tag_schemas.TagCreate(**fields))
        return

    tags_repository.update_tag(db, db_tag.id, tag_schemas.TagUpdate(**fields))


def _ensure_docs_user(db):
    org = organisations_repository.get_organisation_by_name(
        db, organisation_name=DOCS_ORG_NAME
    )
    if org is None:
        org = organisations_repository.create_organisation(
            db,
            organisation=organisation_schemas.OrganisationCreate(
                name=DOCS_ORG_NAME, created_by=0, local=True
            ),
        )
        typer.echo(f"Created docs organisation id={org.id}")

    user = user_repository.get_user_by_email(db, email=DOCS_USER_EMAIL)
    if user is None:
        user = user_repository.create_user(
            db,
            user=user_schemas.UserCreate(
                email=DOCS_USER_EMAIL,
                password=DOCS_USER_PASSWORD,
                org_id=org.id,
                role_id=DOCS_USER_ROLE_ID,
            ),
        )
        typer.echo(f"Created docs user id={user.id}")
    return org, user


@app.command()
def seed_docs_fixtures(
    fixtures_dir: Path = typer.Option(
        DOCS_FIXTURES_DIR,
        "--fixtures-dir",
        help="Directory containing events.json / attributes.json / hunts.json",
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Delete the fixture user's hunts before re-creating them (events/attributes are always re-timed and overwritten)",
    ),
):
    """Seed deterministic data used by docs/screenshots/* captures.

    Events and attributes are re-timed and re-indexed on every run so they
    always fall inside the Explore view's default 30-day window. Hunts are
    created once per fixture name; use --reset to pick up edits to hunts.json.
    Fixture UUIDs are pinned so screenshot URLs stay stable across runs.
    """
    db = SessionLocal()
    org, user = _ensure_docs_user(db)

    events_data = json.loads((fixtures_dir / "events.json").read_text())
    attrs_data = json.loads((fixtures_dir / "attributes.json").read_text())
    objects_data = json.loads((fixtures_dir / "objects.json").read_text())
    hunts_data = json.loads((fixtures_dir / "hunts.json").read_text())
    audit_data = json.loads((fixtures_dir / "audit_logs.json").read_text())

    client = get_opensearch_client()

    if reset:
        db.query(hunt_models.Hunt).filter(hunt_models.Hunt.user_id == user.id).delete()
        db.commit()
        typer.echo("Reset existing docs hunts.")

    # Audit logs are always re-timed and overwritten so screenshots show
    # recent entries. We mark each fixture row with metadata._docs_fixture so
    # we can wipe only docs-seeded entries — never any real audit history.
    db.query(audit_log_models.AuditLog).filter(
        audit_log_models.AuditLog.metadata_["_docs_fixture"].astext == "true",
    ).delete(synchronize_session=False)
    db.commit()

    # Recompute timestamps every run so events/attributes always sit within
    # the last 30 days (the default Explore date filter). Events and
    # attributes are always overwritten; their UUIDs are pinned so the index
    # never accumulates stale duplicates.
    now = datetime.now(timezone.utc)
    event_ts_by_uuid: dict[str, int] = {}

    for ev in events_data:
        offset_days = ev.get("date_offset_days", 0)
        when = now - timedelta(days=offset_days)
        event_ts_by_uuid[ev["uuid"]] = int(when.timestamp())

        payload = {k: v for k, v in ev.items() if k not in ("date_offset_days", "tags")}
        payload["date"] = when
        payload["timestamp"] = int(when.timestamp())
        payload["org_id"] = org.id
        payload["orgc_id"] = org.id
        payload["user_id"] = user.id

        client.delete(index="misp-events", id=ev["uuid"], ignore=[404], refresh=True)
        _clear_event_children(client, ev["uuid"])
        db_event = events_repository.create_event(
            db, event=event_schemas.EventCreate(**payload)
        )

        # Tags carry their colour in the fixture. get_or_create_tag_by_name
        # would otherwise hash the name into an arbitrary pastel, so a
        # well-known tag like tlp:amber would not come out amber on an
        # instance with no taxonomies loaded.
        for tag in ev.get("tags", []):
            _ensure_tag(db, tag)
            tags_repository.tag_event(
                db=db,
                event=db_event,
                tag=tags_repository.get_tag_by_name(db, tag_name=tag["name"]),
            )

    for attr in attrs_data:
        payload = dict(attr)
        offset_days = payload.pop("date_offset_days", None)
        if offset_days is not None:
            payload["timestamp"] = int((now - timedelta(days=offset_days)).timestamp())
        elif payload.get("event_uuid") in event_ts_by_uuid:
            payload["timestamp"] = event_ts_by_uuid[payload["event_uuid"]]

        client.delete(
            index="misp-attributes", id=attr["uuid"], ignore=[404], refresh=True
        )
        attributes_repository.create_attribute(
            db, attribute=attribute_schemas.AttributeCreate(**payload)
        )

    # Objects after their event, and after the standalone attributes: an
    # object owns its own attributes and the references between objects, all
    # keyed by pinned uuid so a re-run overwrites rather than duplicates.
    for obj in objects_data:
        payload = dict(obj)
        payload["timestamp"] = event_ts_by_uuid.get(
            payload.get("event_uuid"), int(now.timestamp())
        )
        for nested in payload.get("attributes", []):
            nested["timestamp"] = payload["timestamp"]

        client.delete(index="misp-objects", id=obj["uuid"], ignore=[404], refresh=True)
        objects_repository.create_object(
            db, object=object_schemas.ObjectCreate(**payload)
        )

    hunts_created = hunts_skipped = 0
    existing_hunts = {
        h.name
        for h in db.query(hunt_models.Hunt)
        .filter(hunt_models.Hunt.user_id == user.id)
        .all()
    }
    for hunt in hunts_data:
        if hunt["name"] in existing_hunts:
            hunts_skipped += 1
            continue
        hunts_repository.create_hunt(
            db, hunt=hunt_schemas.HuntCreate(**hunt), user_id=user.id
        )
        hunts_created += 1

    for entry in audit_data:
        offset_minutes = entry.get("offset_minutes", 0)
        created_at = now - timedelta(minutes=offset_minutes)
        meta = dict(entry.get("metadata") or {})
        meta["_docs_fixture"] = True
        db.add(
            audit_log_models.AuditLog(
                created_at=created_at,
                actor_user_id=user.id,
                actor_type=entry.get("actor_type", "user"),
                resource_type=entry["resource_type"],
                resource_id=entry.get("resource_id"),
                action=entry["action"],
                ip_address=entry.get("ip_address"),
                user_agent=entry.get("user_agent"),
                metadata_=meta,
            )
        )
    db.commit()

    typer.echo(
        f"Docs fixtures seeded: "
        f"events={len(events_data)} upserted, "
        f"attributes={len(attrs_data)} upserted, "
        f"objects={len(objects_data)} upserted, "
        f"hunts={hunts_created} created / {hunts_skipped} skipped, "
        f"audit_logs={len(audit_data)} re-timed."
    )
    typer.echo(f"Login: {DOCS_USER_EMAIL} / {DOCS_USER_PASSWORD}")


DEMO_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo"

# Fixed so the generated hunt history -- and therefore the heatmap -- is
# identical on every machine and every run.
DEMO_RNG_SEED = "misp-workbench-demo"

# hunts_repository.get_hunt_history caps what it returns; seeding past it
# just hides the recent end of the heatmap.
HUNT_HISTORY_LIMIT = 90

# Stamped into the payload of every notification this seeder creates, so a
# re-run replaces its own and never touches a real one.
DEMO_MARKER = "_demo_fixture"


def _demo_analyst_comment(entry: dict) -> str:
    """The text an analyst-data entry is matched on when re-seeding."""
    return entry.get("note") or entry.get("comment") or ""


def _seed_demo_servos(db, user, servos_data) -> tuple[int, int]:
    """Create a servo per shipped template named in servos.json.

    The fixture names templates rather than copying their processors, so a
    change to a template reaches the demo automatically instead of leaving
    two copies to drift apart.
    """
    templates = {t["slug"]: t for t in servo_chain.load_templates()}
    created = skipped = 0

    for entry in servos_data:
        template = templates.get(entry["template"])
        if template is None:
            typer.echo(f"  ! unknown servo template {entry['template']!r}, skipped")
            continue
        if servos_repository.get_servo_by_slug(db, template["slug"]) is not None:
            skipped += 1
            continue

        servos_repository.create_servo(
            db,
            servo=servo_schemas.ServoCreate(
                slug=template["slug"],
                name=template["name"],
                description=template["description"],
                processors=template["processors"],
                enabled=entry.get("enabled", False),
            ),
            user_id=user.id,
        )
        created += 1
    return created, skipped


def _seed_demo_reactor_scripts(db, user, scripts_data) -> tuple[int, int]:
    created = skipped = 0
    existing = {
        s.name
        for s in db.query(reactor_models.ReactorScript)
        .filter(reactor_models.ReactorScript.user_id == user.id)
        .all()
    }
    for script in scripts_data:
        if script["name"] in existing:
            skipped += 1
            continue
        reactor_repository.create_script(
            db,
            script=reactor_schemas.ReactorScriptCreate(**script),
            user_id=user.id,
        )
        created += 1
    return created, skipped


def _seed_demo_feeds(db, feeds_data) -> tuple[int, int]:
    """Feed definitions only.

    Every one is seeded disabled: a demo should decide when to pull, and a
    fetch reaches the network and brings back whatever is live today, which
    is the opposite of what fixture data is for.
    """
    created = skipped = 0
    existing = {f.name for f in db.query(feed_models.Feed).all()}
    for feed in feeds_data:
        if feed["name"] in existing:
            skipped += 1
            continue
        feeds_repository.create_feed(db, feed=feed_schemas.FeedCreate(**feed))
        created += 1
    return created, skipped


def _seed_demo_analyst_data(user, analyst_data) -> tuple[int, int]:
    """Notes and opinions on the fixture events and attributes.

    Analyst data generates its own uuid, so entries cannot be pinned the way
    events are. They are matched on their text against whatever the parent
    already carries instead, so re-running adds nothing.
    """
    created = skipped = 0
    for entry in analyst_data:
        payload = {k: v for k, v in entry.items() if k != "type"}
        analyst_type = analyst_data_schemas.AnalystDataType(entry["type"])

        existing = analyst_data_repository.get_analyst_data_by_object_uuid(
            object_uuid=entry["object_uuid"], object_type=entry["object_type"]
        )
        wanted = _demo_analyst_comment(entry)
        already_there = any(
            _demo_analyst_comment(thread.data) == wanted
            for thread in (*existing.notes, *existing.opinions)
        )
        if already_there:
            skipped += 1
            continue

        result = analyst_data_repository.create_analyst_data(
            analyst_type, payload, user
        )
        if result is None:
            typer.echo(
                f"  ! parent {entry['object_uuid']} not found, "
                f"{entry['type'].lower()} skipped"
            )
            continue
        created += 1
    return created, skipped


def _seed_demo_event_reports(reports_data) -> int:
    """Markdown event reports, written straight to the index with a pinned uuid.

    reports_repository.create_event_report generates its own uuid, which would
    stack a fresh copy on every seed. The document shape is small and stable,
    so it is built here instead and upserted like the events are.

    Reports hang off the docs-fixture events by uuid and survive a docs
    re-seed: _clear_event_children drops attributes, objects and object
    references, not reports.
    """
    client = get_opensearch_client()
    now = datetime.now(timezone.utc)

    for report in reports_data:
        client.index(
            index="misp-event-reports",
            id=report["uuid"],
            body={
                "uuid": report["uuid"],
                "event_uuid": report["event_uuid"],
                "name": report["name"],
                "content": report["content"],
                "distribution": report.get("distribution", 0),
                "sharing_group_id": report.get("sharing_group_id"),
                "timestamp": int(now.timestamp()),
                "@timestamp": now.isoformat(),
                "deleted": False,
            },
            refresh=True,
        )
    return len(reports_data)


def _seed_demo_hunt_history(db, user, history_data) -> tuple[int, int]:
    """Expand each hunt's run shape into individual HuntRunHistory rows.

    The hunt view draws a 90-day cal-heatmap and a sparkline straight off this
    table, so a handful of rows leaves both looking broken. The fixture
    describes the shape -- cadence, baseline, spikes -- and it is expanded here
    rather than checking thousands of literal rows into the repository.

    Seeded from a fixed RNG so the heatmap is identical on every machine; a
    demo that looks different each run is a demo you cannot rehearse.

    Kept at or under HUNT_HISTORY_LIMIT rows per hunt on purpose: the history
    endpoint returns the *oldest* 90 rows, so a hunt with more than that shows
    a heatmap of the wrong end of the window.
    """
    runs_created = hunts_skipped = 0
    now = datetime.now(timezone.utc)

    for entry in history_data:
        hunt = (
            db.query(hunt_models.Hunt)
            .filter(
                hunt_models.Hunt.user_id == user.id,
                hunt_models.Hunt.name == entry["hunt"],
            )
            .first()
        )
        if hunt is None:
            typer.echo(f"  ! hunt {entry['hunt']!r} not found, history skipped")
            hunts_skipped += 1
            continue

        # Re-seeding replaces this hunt's history so runs do not pile up on
        # top of each other every time the demo is refreshed. The endpoint
        # serves history from Redis when it is warm, so the cache has to go
        # with it or the heatmap keeps showing the previous seed.
        db.query(hunt_models.HuntRunHistory).filter(
            hunt_models.HuntRunHistory.hunt_id == hunt.id
        ).delete(synchronize_session=False)
        try:
            redis = get_redis_client()
            redis.delete(f"hunt:history:{hunt.id}")
            redis.delete(f"hunt:results:{hunt.id}")
        except Exception:  # noqa: BLE001 - a cold cache is not a failure
            pass

        planned = entry.get("days", 30) * max(1, entry.get("runs_per_day", 1))
        if planned > HUNT_HISTORY_LIMIT:
            typer.echo(
                f"  ! {entry['hunt']!r} would seed {planned} runs but the history "
                f"endpoint returns only the oldest {HUNT_HISTORY_LIMIT}; "
                "the heatmap would show the wrong end of the window"
            )

        rng = random.Random(f"{DEMO_RNG_SEED}:{entry['hunt']}")
        spikes = {s["days_ago"]: s["match_count"] for s in entry.get("spikes", [])}
        runs_per_day = max(1, entry.get("runs_per_day", 1))
        baseline = entry.get("baseline", 5)
        jitter = entry.get("jitter", 0)

        latest_run = None
        latest_count = 0

        # Stops at yesterday: today's row comes from the real run below, so
        # the newest point on the chart has results behind it.
        for days_ago in range(entry.get("days", 30), 0, -1):
            day = now - timedelta(days=days_ago)
            # A hunt that matches nothing at the weekend reads as a real
            # schedule rather than a flat block of colour.
            if entry.get("quiet_weekends") and day.weekday() >= 5:
                continue

            for run in range(runs_per_day):
                run_at = day.replace(
                    hour=(24 // runs_per_day) * run,
                    minute=rng.randrange(0, 60),
                    second=0,
                    microsecond=0,
                )
                if run_at > now:
                    continue

                if days_ago in spikes and run == runs_per_day - 1:
                    match_count = spikes[days_ago]
                else:
                    match_count = max(0, baseline + rng.randint(-jitter, jitter))

                db.add(
                    hunt_models.HuntRunHistory(
                        hunt_id=hunt.id,
                        run_at=run_at,
                        match_count=match_count,
                    )
                )
                runs_created += 1
                if latest_run is None or run_at > latest_run:
                    latest_run = run_at
                    latest_count = match_count

        if latest_run is not None:
            hunt.last_run_at = latest_run.replace(tzinfo=None)
            hunt.last_match_count = latest_count

    db.commit()
    return runs_created, hunts_skipped


def _run_demo_hunts(db, user, history_data) -> tuple[int, int]:
    """Execute each seeded hunt once so its results are real.

    The synthetic history gives the heatmap and sparkline their shape, but the
    results panel reads `hunt:results:<id>` in Redis, which only a real run
    writes. Without this the hunt view shows a populated chart above an empty
    result table, which is the one thing a demo of hunting must not do.

    Hunt types that reach an external service (cpe, rulezet) are allowed to
    fail: the demo should still come up on a machine with no outbound network.
    """
    ran = failed = 0
    for entry in history_data:
        hunt = (
            db.query(hunt_models.Hunt)
            .filter(
                hunt_models.Hunt.user_id == user.id,
                hunt_models.Hunt.name == entry["hunt"],
            )
            .first()
        )
        if hunt is None:
            continue
        try:
            hunts_repository.execute_hunt_system(db, hunt.id)
            ran += 1
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            failed += 1
            typer.echo(f"  ! hunt {hunt.name!r} did not run: {exc}")
    return ran, failed


def _warm_demo_hunt_history_cache(db, user, history_data) -> None:
    """Rebuild each hunt's Redis history list from the newest rows.

    Two reasons this cannot be left to the repository. Running a hunt rpushes
    onto the key the seeder just deleted, leaving a cache of exactly one entry
    that `get_hunt_history` then serves in preference to the database. And its
    own cold-cache path loads the *oldest* HUNT_HISTORY_LIMIT rows, which for a
    long-running hunt is the wrong end of the window.
    """
    try:
        redis = get_redis_client()
    except Exception:  # noqa: BLE001
        return

    for entry in history_data:
        hunt = (
            db.query(hunt_models.Hunt)
            .filter(
                hunt_models.Hunt.user_id == user.id,
                hunt_models.Hunt.name == entry["hunt"],
            )
            .first()
        )
        if hunt is None:
            continue

        rows = (
            db.query(hunt_models.HuntRunHistory)
            .filter(hunt_models.HuntRunHistory.hunt_id == hunt.id)
            .order_by(hunt_models.HuntRunHistory.run_at.desc())
            .limit(HUNT_HISTORY_LIMIT)
            .all()
        )
        key = f"hunt:history:{hunt.id}"
        redis.delete(key)
        if not rows:
            continue
        redis.rpush(
            key,
            *[
                json.dumps(
                    {
                        "run_at": row.run_at.isoformat(),
                        "match_count": row.match_count,
                    }
                )
                for row in reversed(rows)
            ],
        )


def _seed_demo_notifications(db, user, notifications_data) -> tuple[int, int]:
    """Notifications of each kind the notification list knows how to render.

    Real ones only appear as a side effect of ingest, sync and correlation, so
    a fresh instance shows an empty list -- and the payload shape differs per
    type, which is why these are fixtures rather than generated.
    """
    created = 0
    now = datetime.now(timezone.utc)

    # Replace this seeder's own notifications so re-running does not stack
    # duplicates. Matched on the marker, never on type or user alone.
    # payload is a plain JSON column, not JSONB, so `.astext` is unavailable
    # here -- unlike the audit log, which is JSONB.
    db.query(notification_models.Notification).filter(
        notification_models.Notification.user_id == user.id,
        notification_models.Notification.payload[DEMO_MARKER].as_boolean().is_(True),
    ).delete(synchronize_session=False)
    db.commit()

    hunt_ids: dict[str, int] = {}
    for entry in notifications_data:
        payload = dict(entry.get("payload") or {})

        # hunt.* notifications link by id, which only exists after the hunts
        # are seeded, so it is resolved here rather than pinned in the file.
        hunt_name = entry.get("hunt")
        if hunt_name is not None:
            if hunt_name not in hunt_ids:
                hunt = (
                    db.query(hunt_models.Hunt)
                    .filter(
                        hunt_models.Hunt.user_id == user.id,
                        hunt_models.Hunt.name == hunt_name,
                    )
                    .first()
                )
                if hunt is None:
                    typer.echo(
                        f"  ! hunt {hunt_name!r} not found, notification skipped"
                    )
                    continue
                hunt_ids[hunt_name] = hunt.id
            payload["hunt_id"] = hunt_ids[hunt_name]
            payload["hunt_name"] = hunt_name

        payload[DEMO_MARKER] = True

        db.add(
            notification_models.Notification(
                user_id=user.id,
                type=entry["type"],
                entity_type=entry.get("entity_type"),
                entity_uuid=None,
                read=entry.get("read", False),
                payload=payload,
                created_at=now - timedelta(minutes=entry.get("offset_minutes", 0)),
            )
        )
        created += 1

    db.commit()
    return created, 0


@app.command()
def seed_demo(
    fixtures_dir: Path = typer.Option(
        DEMO_FIXTURES_DIR,
        "--fixtures-dir",
        help="Directory containing the demo fixture JSON files",
    ),
    docs_fixtures_dir: Path = typer.Option(
        DOCS_FIXTURES_DIR,
        "--docs-fixtures-dir",
        help="Directory the underlying docs fixtures are read from",
    ),
    skip_docs: bool = typer.Option(
        False,
        "--skip-docs",
        help="Do not run seed-docs-fixtures first (the demo data references it)",
    ),
    skip_correlations: bool = typer.Option(
        False,
        "--skip-correlations",
        help="Do not run the correlation engine after seeding",
    ),
    notebooks_dir: Path = typer.Option(
        Path("/code/lab_library"),
        "--notebooks-dir",
        help="Directory of .ipynb files to seed into the Tech Lab library",
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help="Remove the demo's own rows before re-creating them. Never touches anything it did not create.",
    ),
):
    """Seed a full walkthrough dataset for a live demo.

    Builds on `seed-docs-fixtures` -- the events, attributes, objects, hunts
    and audit rows behind the documentation screenshots -- and adds the parts
    the screenshot suite fakes with Playwright route stubs and so never
    persists anywhere: servos, reactor scripts, analyst notes and opinions,
    feed definitions, library notebooks, and a second set of events whose
    indicators deliberately overlap the first so the correlation engine has
    something real to find.

    Additive by design. Everything is keyed by pinned uuid or by name, so
    re-running refreshes the demo in place and leaves the rest of the
    instance alone.
    """
    if not fixtures_dir.is_dir():
        typer.echo(f"Demo fixtures not found: {fixtures_dir}", err=True)
        raise typer.Exit(code=1)

    if not skip_docs:
        typer.echo("Seeding docs fixtures first...")
        seed_docs_fixtures(fixtures_dir=docs_fixtures_dir, reset=False)
        typer.echo("")

    db = SessionLocal()
    org, user = _ensure_docs_user(db)

    events_data = json.loads((fixtures_dir / "events.json").read_text())
    attrs_data = json.loads((fixtures_dir / "attributes.json").read_text())
    servos_data = json.loads((fixtures_dir / "servos.json").read_text())
    scripts_data = json.loads((fixtures_dir / "reactor_scripts.json").read_text())
    feeds_data = json.loads((fixtures_dir / "feeds.json").read_text())
    analyst_data = json.loads((fixtures_dir / "analyst_data.json").read_text())
    history_data = json.loads((fixtures_dir / "hunt_history.json").read_text())
    notifications_data = json.loads((fixtures_dir / "notifications.json").read_text())
    reports_data = json.loads((fixtures_dir / "event_reports.json").read_text())

    client = get_opensearch_client()

    if reset:
        _reset_demo(
            db, client, events_data, servos_data, scripts_data, feeds_data, reports_data
        )

    now = datetime.now(timezone.utc)

    # Events and their attributes, same pinned-uuid upsert the docs fixtures
    # use so a re-run overwrites rather than accumulates.
    for ev in events_data:
        when = now - timedelta(days=ev.get("date_offset_days", 0))
        payload = {k: v for k, v in ev.items() if k not in ("date_offset_days", "tags")}
        payload["date"] = when
        payload["timestamp"] = int(when.timestamp())
        payload["org_id"] = org.id
        payload["orgc_id"] = org.id
        payload["user_id"] = user.id

        client.delete(index="misp-events", id=ev["uuid"], ignore=[404], refresh=True)
        _clear_event_children(client, ev["uuid"])
        db_event = events_repository.create_event(
            db, event=event_schemas.EventCreate(**payload)
        )

        for tag in ev.get("tags", []):
            _ensure_tag(db, tag)
            tags_repository.tag_event(
                db=db,
                event=db_event,
                tag=tags_repository.get_tag_by_name(db, tag_name=tag["name"]),
            )

    event_ts = {
        ev["uuid"]: int(
            (now - timedelta(days=ev.get("date_offset_days", 0))).timestamp()
        )
        for ev in events_data
    }
    for attr in attrs_data:
        payload = dict(attr)
        payload["timestamp"] = event_ts.get(
            payload.get("event_uuid"), int(now.timestamp())
        )
        client.delete(
            index="misp-attributes", id=attr["uuid"], ignore=[404], refresh=True
        )
        attributes_repository.create_attribute(
            db, attribute=attribute_schemas.AttributeCreate(**payload)
        )

    servos_created, servos_skipped = _seed_demo_servos(db, user, servos_data)
    scripts_created, scripts_skipped = _seed_demo_reactor_scripts(
        db, user, scripts_data
    )
    feeds_created, feeds_skipped = _seed_demo_feeds(db, feeds_data)
    notes_created, notes_skipped = _seed_demo_analyst_data(user, analyst_data)
    reports_created = _seed_demo_event_reports(reports_data)
    runs_created, history_skipped = _seed_demo_hunt_history(db, user, history_data)

    # After the synthetic history, so the newest run is a real one with real
    # cached results; then rebuild the cache, which running the hunt leaves
    # holding only that single run.
    hunts_ran, hunts_failed = _run_demo_hunts(db, user, history_data)
    _warm_demo_hunt_history_cache(db, user, history_data)

    # Last, so the fixture notifications sit above any the hunt runs raised.
    notifs_created, _ = _seed_demo_notifications(db, user, notifications_data)

    notebooks_msg = "skipped (directory not found)"
    if notebooks_dir.is_dir():
        seed_lab_library(owner_email=DOCS_USER_EMAIL, directory=notebooks_dir)
        notebooks_msg = f"seeded from {notebooks_dir}"

    correlations_msg = "skipped"
    if not skip_correlations:
        # run_correlations writes with op_type=create and never deletes, so
        # this is additive and safe to repeat -- unlike the scheduled
        # generate_correlations task, which wipes the index first.
        runtime_settings = get_runtime_settings(db)
        correlations_repository.run_correlations(runtime_settings)
        correlations_msg = "generated"

    typer.echo("")
    typer.echo("Demo data seeded:")
    typer.echo(f"  events            {len(events_data)} upserted")
    typer.echo(f"  attributes        {len(attrs_data)} upserted")
    typer.echo(
        f"  servos            {servos_created} created / {servos_skipped} already present"
    )
    typer.echo(
        f"  reactor scripts   {scripts_created} created / {scripts_skipped} already present"
    )
    typer.echo(
        f"  feeds             {feeds_created} created / {feeds_skipped} already present (all disabled)"
    )
    typer.echo(
        f"  analyst data      {notes_created} created / {notes_skipped} already present"
    )
    typer.echo(
        f"  hunt runs         {runs_created} across "
        f"{len(history_data) - history_skipped} hunts (90-day heatmap + sparkline)"
    )
    typer.echo(
        f"  hunt results      {hunts_ran} hunts executed"
        + (f" / {hunts_failed} unavailable" if hunts_failed else "")
    )
    typer.echo(f"  event reports     {reports_created} upserted")
    typer.echo(f"  notifications     {notifs_created} created")
    typer.echo(f"  notebooks         {notebooks_msg}")
    typer.echo(f"  correlations      {correlations_msg}")
    typer.echo("")
    typer.echo(f"Login: {DOCS_USER_EMAIL} / {DOCS_USER_PASSWORD}")


def _reset_demo(
    db, client, events_data, servos_data, scripts_data, feeds_data, reports_data
) -> None:
    """Delete the demo's own rows, and only those.

    Matched by pinned uuid or by the exact fixture name, so a servo, feed or
    script someone created by hand survives even if it shares a subject with
    the demo.

    Hunt run history and notifications are not listed here: both are replaced
    wholesale on every seed, so they need no separate reset.
    """
    for ev in events_data:
        _clear_event_children(client, ev["uuid"])
        client.delete(index="misp-events", id=ev["uuid"], ignore=[404], refresh=True)

    template_slugs = {entry["template"] for entry in servos_data}
    for slug in template_slugs:
        db_servo = servos_repository.get_servo_by_slug(db, slug)
        if db_servo is not None:
            servos_repository.delete_servo(db, db_servo)

    for report in reports_data:
        client.delete(
            index="misp-event-reports", id=report["uuid"], ignore=[404], refresh=True
        )

    script_names = {s["name"] for s in scripts_data}
    db.query(reactor_models.ReactorScript).filter(
        reactor_models.ReactorScript.name.in_(script_names)
    ).delete(synchronize_session=False)

    feed_names = {f["name"] for f in feeds_data}
    db.query(feed_models.Feed).filter(feed_models.Feed.name.in_(feed_names)).delete(
        synchronize_session=False
    )

    db.commit()
    typer.echo("Reset demo rows (events, servos, reactor scripts, feeds).")


@app.command()
def sync_event_counts(
    event_uuid: Optional[str] = typer.Option(
        None, "--event-uuid", help="Only this event; every event when omitted"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Report what would change without writing"
    ),
):
    """Recount attribute_count and object_count from the indexed documents.

    Reconciles events whose totals drifted, which the per attribute increments
    used to cause on any sizeable ingest.
    """
    from app.services.opensearch import get_opensearch_client
    from opensearchpy import helpers as opensearch_helpers

    client = get_opensearch_client()

    if event_uuid:
        events = [{"_id": event_uuid, "_source": {}}]
    else:
        events = opensearch_helpers.scan(
            client=client,
            index="misp-events",
            query={
                "query": {"match_all": {}},
                "_source": ["attribute_count", "object_count", "info"],
            },
            scroll="5m",
            size=200,
        )

    checked = 0
    drifted = 0

    for event in events:
        uuid = event["_id"]
        stored = event["_source"]
        checked += 1

        attribute_count = events_repository.count_event_attributes(uuid)
        object_count = events_repository.count_event_objects(uuid)

        if (
            stored.get("attribute_count") == attribute_count
            and stored.get("object_count") == object_count
        ):
            continue

        drifted += 1
        typer.echo(
            f"{uuid} attributes {stored.get('attribute_count')} -> {attribute_count}, "
            f"objects {stored.get('object_count')} -> {object_count}"
        )

        if not dry_run:
            events_repository.sync_event_counts(uuid)

    typer.echo(
        f"{checked} event(s) checked, {drifted} corrected."
        if not dry_run
        else f"{checked} event(s) checked, {drifted} would change (dry run)."
    )


if __name__ == "__main__":
    app()
