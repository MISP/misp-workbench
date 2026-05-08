import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from app.database import SessionLocal
from app.models import lab as lab_models
from app.repositories import organisations as organisations_repository
from app.repositories import users as user_repository
from app.schemas import organisations as organisation_schemas
from app.schemas import user as user_schemas
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


if __name__ == "__main__":
    app()
