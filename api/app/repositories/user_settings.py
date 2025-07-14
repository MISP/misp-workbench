from app.models import user_setting as user_settings_models
from sqlalchemy.orm import Session


def get_user_settings(db: Session, user_id: str):
    return (
        db.query(user_settings_models.UserSetting)
        .filter(user_settings_models.UserSetting.user_id == user_id)
        .all()
    )

def get_user_setting(db: Session, user_id: int, namespace: str):
    return (
        db.query(user_settings_models.UserSetting)
        .filter(user_settings_models.UserSetting.user_id == user_id)
        .filter(user_settings_models.UserSetting.namespace == namespace)
        .first()
    )


def set_user_setting(db: Session, user_id: str, namespace: str, value: dict):
    setting = get_user_setting(db, user_id, namespace)
    if setting:
        setting.value = value
    else:
        setting = user_settings_models.UserSetting(user_id=user_id, namespace=namespace, value=value)
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def delete_user_setting(db: Session, user_id: str, namespace: str):
    db.query(user_settings_models.UserSetting).filter_by(
        user_id=user_id, namespace=namespace
    ).delete()
    db.commit()
