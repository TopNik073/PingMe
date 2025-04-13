from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, AsyncGenerator
from uuid import UUID

from src.infrastructure.database.models.BaseModel import BaseModel as DBModel
from pydantic import BaseModel as PydanticBaseModel

MODEL_TYPE = TypeVar("MODEL_TYPE", bound=DBModel)
PYDANTIC_TYPE = TypeVar("PYDANTIC_TYPE", bound=PydanticBaseModel)
SessionType = TypeVar("SessionType")


class AbstractRepository(ABC, Generic[MODEL_TYPE]):
    """
    Abstract repository class defining the base interface for working with models
    """

    @abstractmethod
    async def get_transaction(self) -> AsyncGenerator[SessionType, None]:
        """Gets a transaction, used for multiple operations in a single transaction"""
        raise NotImplementedError

    @abstractmethod
    async def get_session(self) -> AsyncGenerator[SessionType, None]:
        """Gets a session, used for single operations"""
        raise NotImplementedError

    @abstractmethod
    async def create(self, schema: PYDANTIC_TYPE) -> MODEL_TYPE:
        """Creates a new record"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self, id: UUID, include_relations: list[str] | None = None
    ) -> MODEL_TYPE | None:
        """Gets a record by id with optional related data"""
        raise NotImplementedError

    @abstractmethod
    async def get_by_filter(
        self, include_relations: list[str] | None = None, **filters: dict
    ) -> List[MODEL_TYPE] | None:
        """Gets a record by specified filters with optional related data"""
        raise NotImplementedError

    @abstractmethod
    async def get_paginated(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        include_relations: list[str] | None = None,
        **filters: dict,
    ) -> List[MODEL_TYPE]:
        """Gets a paginated list of records with optional filters and related data"""
        raise NotImplementedError

    @abstractmethod
    async def update(self, id: UUID, schema: PYDANTIC_TYPE) -> MODEL_TYPE:
        """Updates a record"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Deletes a record"""
        raise NotImplementedError
