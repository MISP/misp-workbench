from app.models import setting as setting_models
from sqlalchemy.orm import Session


def get_settings(db: Session):
    return db.query(setting_models.Setting).all()


def get_setting(db: Session, namespace: str):
    return (
        db.query(setting_models.Setting)
        .filter(setting_models.Setting.namespace == namespace)
        .first()
    )


def set_setting(db: Session, namespace: str, value: dict):
    setting = get_setting(db, namespace)
    if setting:
        setting.value = value
    else:
        setting = setting_models.Setting(namespace=namespace, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def delete_setting(db: Session, namespace: str):
    setting = get_setting(db, namespace)
    if setting:
        db.delete(setting)
        db.commit()
        return True
    return False
