from typing import Any, Sequence, Type, TypeVar, AsyncGenerator
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.interfaces.repositories import AbstractRepository
from src.infrastructure.database.models.BaseModel import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class SQLAlchemyRepository(AbstractRepository[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, session_factory: async_sessionmaker, model: Type[ModelType]):
        self._session_factory = session_factory
        self._model = model

    @property
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except:
                await session.rollback()
                raise

    async def create(self, schema: CreateSchemaType) -> ModelType:
        async for session in self.session:
            db_obj = self._model(**schema.model_dump())
            session.add(db_obj)
            await session.flush()
            return db_obj

    async def get_by_id(self, id: UUID) -> ModelType | None:
        async for session in self.session:
            query = select(self._model).where(self._model.id == id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_by_filter(self, **filters: Any) -> ModelType | None:
        query = select(self._model)
        for field, value in filters.items():
            query = query.where(getattr(self._model, field) == value)
        async for session in self.session:
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_paginated(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        **filters: Any
    ) -> Sequence[ModelType]:
        should_return_all = limit == 0
        query = select(self._model)
        for field, value in filters.items():
            query = query.where(getattr(self._model, field) == value)
        if not should_return_all:
            query = query.offset(skip).limit(limit)
        async for session in self.session:
            result = await session.execute(query)
            return result.scalars().all()

    async def update(self, id: UUID, schema: UpdateSchemaType) -> ModelType:
        db_obj = await self.get_by_id(id)
        if db_obj:
            obj_data = schema.model_dump(exclude_unset=True)
            for field, value in obj_data.items():
                setattr(db_obj, field, value)
            async for session in self.session:
                await session.flush()
        return db_obj

    async def delete(self, id: UUID) -> None:
        db_obj = await self.get_by_id(id)
        if db_obj:
            async for session in self.session:
                await session.delete(db_obj)
                await session.flush() 