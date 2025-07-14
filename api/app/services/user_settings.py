from app.repositories import user_settings as user_settings_repository
from app.services.base_settings import BaseSettings
from app.services.runtime_settings import RuntimeSettings


class UserSettings(BaseSettings):
    def __init__(self, db, user_id: str, runtime_settings: RuntimeSettings):
        super().__init__(db)
        self.user_id = user_id
        self.runtime_settings = runtime_settings

    def _fetch_from_repository(self):
        return {
            setting.namespace: setting.value
            for setting in user_settings_repository.get_user_settings(
                self.db, self.user_id
            )
        }

    def _store_to_repository(self, namespace: str, value: dict):
        user_settings_repository.set_user_setting(
            self.db, self.user_id, namespace, value
        )

    def _delete_from_repository(self, namespace: str):
        user_settings_repository.delete_user_setting(self.db, self.user_id, namespace)

    def get_value(self, namespace: str, default=None):
        val = super().get_value(namespace)
        if val is not None:
            return val
        return self.runtime_settings.get_value(namespace, default)
