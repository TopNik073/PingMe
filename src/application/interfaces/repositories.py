from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Sequence, Any
from uuid import UUID

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class AbstractRepository(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Abstract repository class defining the base interface for working with models
    """
    
    @abstractmethod
    async def create(self, schema: CreateSchemaType) -> ModelType:
        """Creates a new record"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Gets a record by id"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_filter(self, **filters: Any) -> ModelType | None:
        """Gets a record by specified filters"""
        raise NotImplementedError
    
    @abstractmethod
    async def get_paginated(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        **filters: Any
    ) -> Sequence[ModelType]:
        """Gets a paginated list of records with optional filters"""
        raise NotImplementedError
    
    @abstractmethod
    async def update(
        self, 
        id: UUID, 
        schema: UpdateSchemaType
    ) -> ModelType:
        """Updates a record"""
        raise NotImplementedError
    
    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Deletes a record"""
        raise NotImplementedError
