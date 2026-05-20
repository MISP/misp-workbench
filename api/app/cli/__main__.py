import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer

from app.database import SessionLocal
from app.models import audit_log as audit_log_models
from app.models import hunt as hunt_models
from app.models import lab as lab_models
from app.repositories import attributes as attributes_repository
from app.repositories import events as events_repository
from app.repositories import hunts as hunts_repository
from app.repositories import organisations as organisations_repository
from app.repositories import users as user_repository
from app.schemas import attribute as attribute_schemas
from app.schemas import event as event_schemas
from app.schemas import hunt as hunt_schemas
from app.schemas import organisations as organisation_schemas
from app.schemas import user as user_schemas
from app.services.opensearch import get_opensearch_client
from app.services.tech_lab.lab import nbformat_io
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

        payload = {k: v for k, v in ev.items() if k != "date_offset_days"}
        payload["date"] = when
        payload["timestamp"] = int(when.timestamp())
        payload["org_id"] = org.id
        payload["orgc_id"] = org.id
        payload["user_id"] = user.id

        client.delete(index="misp-events", id=ev["uuid"], ignore=[404], refresh=True)
        events_repository.create_event(db, event=event_schemas.EventCreate(**payload))

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
        f"hunts={hunts_created} created / {hunts_skipped} skipped, "
        f"audit_logs={len(audit_data)} re-timed."
    )
    typer.echo(f"Login: {DOCS_USER_EMAIL} / {DOCS_USER_PASSWORD}")


if __name__ == "__main__":
    app()
