from sqlalchemy.orm import Session
from app.repositories import settings as settings_repository


class RuntimeSettings:
    def __init__(self, db: Session):
        self.db = db
        self._cache = None

    def _load_settings(self):
        if self._cache is None:
            self._cache = {
                setting.namespace: setting.value
                for setting in settings_repository.get_settings(self.db)
            }
        return self._cache

    def get(self, namespace: str):
        return self._load_settings().get(namespace)

    def set(self, namespace: str, value: str):
        settings_repository.set_setting(self.db, namespace, value)
        if self._cache is not None:
            self._cache[namespace] = value

    def delete(self, namespace: str):
        settings_repository.delete_setting(self.db, namespace)
        if self._cache and namespace in self._cache:
            del self._cache[namespace]

    def all(self):
        return self._load_settings()
