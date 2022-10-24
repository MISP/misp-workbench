import typer
from app.database import SessionLocal
from app.repositories import organisations as organisations_repository
from app.repositories import users as user_repository
from app.schemas import organisations as organisation_schemas
from app.schemas import user as user_schemas

app = typer.Typer()


@app.command()
def create_organisation(name: str, created_by: int = 0, local: bool = True):
    db = SessionLocal()
    organisation = organisation_schemas.OrganisationCreate(
        name=name, created_by=created_by, local=local
    )
    organisation_db = organisations_repository.create_organisation(
        db, organisation=organisation
    )
    print(f"Created organisation id={organisation_db.id}")  # noqa: T201


@app.command()
def create_user(email: str, password: str, organisation_id: int, role_id: int):
    db = SessionLocal()
    user = user_schemas.UserCreate(
        email=email, password=password, org_id=organisation_id, role_id=role_id
    )
    user_db = user_repository.create_user(db, user=user)
    print(f"Created user id={user_db.id}")  # noqa: T201


if __name__ == "__main__":
    app()
