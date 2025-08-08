import redis
from app.settings import get_settings


Settings = get_settings()

RedisClient = redis.Redis(
    host=Settings.Redis.host,
    port=Settings.Redis.port,
    db=Settings.Redis.cache_db,
    decode_responses=True,
)
