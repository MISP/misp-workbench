from app.models import role as role_models
from app.schemas import role as role_schemas
from sqlalchemy.orm import Session


def get_roles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(role_models.Role).offset(skip).limit(limit).all()


def get_role_by_id(db: Session, role_id: int):
    return db.query(role_models.Role).filter(role_models.Role.id == role_id).first()


def update_role(db: Session, role_id: int, role_update: role_schemas.RoleUpdate):
    db_role = get_role_by_id(db, role_id)
    if db_role is None:
        return None
    update_data = role_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_role, field, value)
    db.commit()
    db.refresh(db_role)
    return db_role


def delete_role(db: Session, role_id: int):
    db_role = get_role_by_id(db, role_id)
    if db_role is None:
        return None
    db.delete(db_role)
    db.commit()
    return db_role
