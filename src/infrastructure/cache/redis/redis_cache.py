from typing import TypeVar, Type, Dict, Any, Generic, Union
from redis.asyncio import Redis
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase
import json

from src.application.interfaces.cache import AbstractCache, CacheType
from src.core.config import settings

T = TypeVar('T')

class RedisCache(AbstractCache[CacheType], Generic[T, CacheType]):
    """
    Universal class for caching in Redis
    Supports working with Pydantic models, SQLAlchemy models and primitive types
    """
    def __init__(self, redis_client: Redis, model_type: Type[Union[T, CacheType]] = None):
        self._redis = redis_client
        self._model_type = model_type

    async def get(self, key: str) -> Union[T, CacheType]:
        """Get value from cache"""
        value = await self._redis.get(key)
        if value is None:
            return None
            
        # If type is not specified, return string
        if self._model_type is None:
            return value.decode('utf-8')  # type: ignore
            
        # If type is Pydantic model
        if issubclass(self._model_type, BaseModel):
            return self._model_type.model_validate_json(value)  # type: ignore
            
        # If this is a primitive type
        try:
            data = json.loads(value)
            return data  # type: ignore
        except:
            return value.decode('utf-8')  # type: ignore

    async def set(
        self, key: str, value: Any, expire: int = settings.CACHE_TTL
    ) -> None:
        """Set value to cache"""
        if value is None:
            return

        # Convert value to string for storage
        if isinstance(value, BaseModel):
            # Pydantic model
            data = value.model_dump_json()
        elif isinstance(value, DeclarativeBase):
            # SQLAlchemy model
            if hasattr(value, "to_dict"):
                # If there is a to_dict method
                data = json.dumps(value.to_dict())
            else:
                # Otherwise, try to serialize through __dict__
                data = json.dumps({
                    c.name: getattr(value, c.name) 
                    for c in value.__table__.columns
                }, default=str)
        elif isinstance(value, (dict, list)):
            # Dictionary or list
            data = json.dumps(value, default=str)
        else:
            # Primitive type
            data = str(value)

        # Save to Redis
        if expire is not None:
            await self._redis.setex(key, expire, data)
        else:
            await self._redis.set(key, data)

    async def update(
        self, key: str, value: Any, expire: int = settings.CACHE_TTL
    ) -> None:
        """Update value in cache and reset TTL"""
        await self.set(key, value, expire=expire)

    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        return await self._redis.exists(key) > 0
        
    async def get_dict(self, key: str) -> Dict[str, Any] | None:
        """Get dictionary from cache"""
        value = await self._redis.get(key)
        if value is None:
            return None
        return json.loads(value)
