from typing import Annotated

from fastapi import Depends

from redis.asyncio import Redis, ConnectionPool
from src.core.config import settings


async def init_redis_pool() -> Redis:
    """Initialize Redis connection pool"""
    pool = ConnectionPool.from_url(str(settings.REDIS_URL), encoding='utf-8', decode_responses=True)
    return Redis(connection_pool=pool)


async def close_redis_pool(redis: Redis) -> None:
    """Close Redis connection pool"""
    await redis.close()


async def get_redis() -> Redis:
    """Dependency for getting a Redis connection"""
    return await init_redis_pool()


REDIS_DEP = Annotated[Redis, Depends(get_redis)]
