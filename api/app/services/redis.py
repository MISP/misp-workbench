import redis
from app.rediscli import get_redis
from typing import Optional

def get_redis_client(db: Optional[int] = None) -> redis.Redis:
    return get_redis()
