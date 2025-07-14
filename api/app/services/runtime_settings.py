from app.repositories import runtime_settings as runtime_settings_repository
from app.services.base_settings import BaseSettings
from app.defaults.runtime_settings_defaults import DEFAULT_SETTINGS

class RuntimeSettings(BaseSettings):
    def __init__(self, db):
        super().__init__(db, default_settings=DEFAULT_SETTINGS)

    def _fetch_from_repository(self):
        return {
            setting.namespace: setting.value
            for setting in runtime_settings_repository.get_settings(self.db)
        }

    def _store_to_repository(self, namespace: str, value: dict):
        runtime_settings_repository.set_setting(self.db, namespace, value)

    def _delete_from_repository(self, namespace: str):
        runtime_settings_repository.delete_setting(self.db, namespace)
