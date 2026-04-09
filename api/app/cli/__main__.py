from typing import Optional

import typer
from app.database import SessionLocal
from app.repositories import organisations as organisations_repository
from app.repositories import users as user_repository
from app.schemas import organisations as organisation_schemas
from app.schemas import user as user_schemas
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


if __name__ == "__main__":
    app()
