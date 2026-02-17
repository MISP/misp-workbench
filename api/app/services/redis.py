import redis as redis_lib
from app.rediscli import get_redis
from typing import Optional

def get_redis_client(db: Optional[int] = None) -> redis_lib.Redis:
    return get_redis()
