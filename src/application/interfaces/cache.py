from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel
from src.core.config import settings

CacheType = TypeVar("CacheType", bound=BaseModel)

class AbstractCache[CacheType](ABC):
    """Abstract cache interface for Pydantic models"""
    
    @abstractmethod
    async def get(self, key: str) -> CacheType | None:
        """Get value from cache"""
        raise NotImplementedError
    
    @abstractmethod
    async def set(
        self, 
        key: str, 
        value: CacheType, 
        expire: int = settings.CACHE_TTL
    ) -> None:
        """
        Set value to cache
        :param key: Key of value to set:
        :param value: Value to set:
        :param expire: Time in seconds for key to expire
        """
        raise NotImplementedError
    
    @abstractmethod
    async def update(
        self,
        key: str,
        value: CacheType,
    ) -> None:
        """
        Update value in cache while preserving its TTL
        """
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        raise NotImplementedError
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        raise NotImplementedError 