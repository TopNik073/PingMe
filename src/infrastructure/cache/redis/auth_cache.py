from redis.asyncio import Redis
import json
from datetime import datetime, timedelta


class AuthCache:
    """Cache for registration data"""

    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    @staticmethod
    def _get_key(email: str) -> str:
        """Get cache key for email"""
        return f"registration:{email}"

    async def save_auth(self, email: str, data: dict, expire: int = 600) -> None:  # 10 minutes
        """Save registration data to cache"""
        key = self._get_key(email)
        await self._redis.setex(key, expire, json.dumps(data))

    async def get_auth(self, email: str) -> dict | None:
        """Get registration data from cache"""
        key = self._get_key(email)
        data = await self._redis.get(key)

        if data is None:
            return None

        return json.loads(data)

    async def delete_auth(self, email: str) -> None:
        """Delete registration data from cache"""
        key = self._get_key(email)
        await self._redis.delete(key)
