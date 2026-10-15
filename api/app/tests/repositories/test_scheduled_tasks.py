from app.repositories import tasks as tasks_repository


class FakeRedis:
    def __init__(self, keys):
        self._keys = keys

    def keys(self, pattern):
        return list(self._keys)


class FakeEntry:
    def __init__(self, key):
        self.key = key


def test_scheduled_tasks_skip_redbeats_own_keys(monkeypatch):
    keys = [
        "redbeat::lock",
        "redbeat::beat",
        "redbeat::schedule",
        # Newer redbeat versions keep a set here; reading it as an entry
        # failed the whole list.
        "redbeat::statics",
        "redbeat:run_hunt_7",
        "redbeat:export_3",
    ]
    read = []

    def from_key(key, app=None):
        read.append(key)
        return FakeEntry(key)

    monkeypatch.setattr(tasks_repository, "get_redis", lambda db: FakeRedis(keys))
    monkeypatch.setattr(
        tasks_repository.RedBeatSchedulerEntry, "from_key", staticmethod(from_key)
    )
    monkeypatch.setattr(
        tasks_repository, "scheduled_task_to_dict", lambda entry: entry.key
    )

    assert tasks_repository.get_scheduled_tasks() == [
        "redbeat:run_hunt_7",
        "redbeat:export_3",
    ]
    assert read == ["redbeat:run_hunt_7", "redbeat:export_3"]
