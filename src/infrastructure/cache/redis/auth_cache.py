from redis.asyncio import Redis
from src.infrastructure.cache.redis.redis_cache import RedisCache
from typing import Dict, Any


class AuthCache:
    """Cache for authentication data"""

    def __init__(self, redis_client: Redis):
        self._cache = RedisCache(redis_client)
        self._prefix = "auth:"

    def _get_key(self, email: str) -> str:
        """Get cache key for email"""
        return f"{self._prefix}{email}"

    async def save_auth(self, email: str, data: Dict[str, Any], expire: int = 600) -> None:  # 10 minutes
        """Save authentication data to cache"""
        key = self._get_key(email)
        await self._cache.set(key, data, expire=expire)

    async def get_auth(self, email: str) -> Dict[str, Any]:
        """Get authentication data from cache"""
        key = self._get_key(email)
        return await self._cache.get_dict(key)

    async def delete_auth(self, email: str) -> None:
        """Delete authentication data from cache"""
        key = self._get_key(email)
        await self._cache.delete(key)
