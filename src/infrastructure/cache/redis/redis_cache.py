from typing import TypeVar, Type, Dict
from redis.asyncio import Redis
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase

from src.application.interfaces.cache import AbstractCache
from src.core.config import settings
from src.presentation.schemas.users import UserResponseSchema
from src.presentation.schemas.tokens import TokenResponse
from src.infrastructure.database.models.users import Users
from src.infrastructure.database.models.tokens import Tokens

CacheType = TypeVar("CacheType", bound=BaseModel)

# Маппинг SQLAlchemy моделей на Pydantic схемы
MODEL_TO_SCHEMA: Dict[Type[DeclarativeBase], Type[BaseModel]] = {
    Users: UserResponseSchema,
    Tokens: TokenResponse,
}


class RedisCache(AbstractCache[CacheType]):
    def __init__(self, redis_client: Redis, model_type: Type[CacheType]):
        self._redis = redis_client
        self._model_type = model_type

    async def get(self, key: str) -> CacheType | None:
        """Get value from cache"""
        value = await self._redis.get(key)
        if value is None:
            return None
        return self._model_type.model_validate_json(value)

    def _convert_to_schema(self, value: DeclarativeBase) -> BaseModel:
        """Convert SQLAlchemy model to Pydantic schema"""
        if isinstance(value, BaseModel):
            return value

        model_class = value.__class__
        schema_class = MODEL_TO_SCHEMA.get(model_class)

        if not schema_class:
            raise ValueError(
                f"No Pydantic schema found for model {model_class.__name__}. "
                "Please add it to MODEL_TO_SCHEMA mapping."
            )

        # Преобразуем SQLAlchemy модель в словарь
        return schema_class.model_validate(value)

    async def set(
        self, key: str, value: DeclarativeBase | BaseModel, expire: int = settings.CACHE_TTL
    ) -> None:
        """Set value to cache"""
        if value is None:  # Проверяем на None
            return

        if isinstance(value, DeclarativeBase):
            value = self._convert_to_schema(value)

        json_data = value.model_dump_json()
        if expire is not None:
            await self._redis.setex(key, expire, json_data)

    async def update(
        self, key: str, value: DeclarativeBase | BaseModel, expire: int = settings.CACHE_TTL
    ) -> None:
        """Update value in cache and reset TTL"""
        await self.set(key, value, expire=expire)

    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        await self._redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        return await self._redis.exists(key) > 0
