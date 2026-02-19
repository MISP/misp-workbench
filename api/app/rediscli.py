import redis
from typing import Optional
from app.settings import get_settings


Settings = get_settings()


def get_redis(db: Optional[int] = None) -> redis.Redis:
    """Return a Redis client connected to the configured host/port.

    If `db` is provided it will be used, otherwise the default
    `Settings.Redis.cache_db` is used. This keeps backward compatibility
    with the previous `RedisClient` object which uses the default DB.
    """
    use_db = Settings.Redis.cache_db if db is None else db
    return redis.Redis(
        host=Settings.Redis.host,
        port=Settings.Redis.port,
        db=use_db,
        decode_responses=True,
    )


# Backwards-compatible default client
RedisClient = get_redis()
