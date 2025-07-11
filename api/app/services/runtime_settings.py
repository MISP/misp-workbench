from sqlalchemy.orm import Session
from app.repositories import settings as settings_repository
from app.defaults.runtime_settings_defaults import DEFAULT_SETTINGS
import copy


class RuntimeSettings:
    def __init__(self, db: Session):
        self.db = db
        self._cache = None

    def _load_settings(self):
        if self._cache is None:
            db_settings = {
                setting.namespace: setting.value
                for setting in settings_repository.get_settings(self.db)
            }
            # Merge DB over defaults
            self._cache = copy.deepcopy(DEFAULT_SETTINGS)
            self._cache.update(db_settings)  # Shallow merge
        return self._cache

    def get(self, namespace: str):
        return self._load_settings().get(namespace)

    def get_value(self, namespace: str, default=None):
        # support dot notation for nested settings
        if "." in namespace:
            parts = namespace.split(".")
            settings = self._load_settings()
            for part in parts:
                if isinstance(settings, dict) and part in settings:
                    settings = settings[part]
                else:
                    return default
            return settings

        return self._load_settings().get(namespace, default)

    def set(self, namespace: str, value: dict):
        settings_repository.set_setting(self.db, namespace, value)
        if self._cache is not None:
            self._cache[namespace] = value

    def delete(self, namespace: str):
        settings_repository.delete_setting(self.db, namespace)
        if self._cache and namespace in self._cache:
            del self._cache[namespace]

    def all(self):
        return self._load_settings()
