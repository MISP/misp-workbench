from sqlalchemy.orm import Session
import copy

class BaseSettings:
    def __init__(self, db: Session, default_settings: dict = None):
        self.db = db
        self.default_settings = default_settings or {}
        self._cache = None

    def _fetch_from_repository(self) -> dict:
        raise NotImplementedError

    def _store_to_repository(self, namespace: str, value: dict):
        raise NotImplementedError

    def _delete_from_repository(self, namespace: str):
        raise NotImplementedError

    def _load_settings(self):
        if self._cache is None:
            db_settings = self._fetch_from_repository()
            self._cache = copy.deepcopy(self.default_settings)
            self._cache.update(db_settings)
        return self._cache

    def get(self, namespace: str):
        return self._load_settings().get(namespace)

    def get_value(self, namespace: str, default=None):
        # dot notation support
        parts = namespace.split(".")
        current = self._load_settings()
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def set(self, namespace: str, value: dict):
        self._store_to_repository(namespace, value)
        if self._cache is not None:
            self._cache[namespace] = value

    def delete(self, namespace: str):
        self._delete_from_repository(namespace)
        if self._cache and namespace in self._cache:
            del self._cache[namespace]

    def all(self):
        return self._load_settings()
