from typing import TypeVar, Generic, Type
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.infrastructure.database.models.BaseModel import BaseModel as DBModel

ModelType = TypeVar("ModelType", bound=DBModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class SQLAlchemyRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self._session = session
        self._model = model

    async def create(self, schema: CreateSchemaType) -> ModelType:
        """Create a new record"""
        db_obj = self._model(**schema.model_dump())
        self._session.add(db_obj)
        await self._session.commit()
        await self._session.refresh(db_obj)
        return db_obj

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Get record by id"""
        query = select(self._model).where(self._model.id == id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_filter(self, **filters) -> ModelType | None:
        """Get record by filters"""
        query = select(self._model)
        for key, value in filters.items():
            query = query.where(getattr(self._model, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def update(self, id: UUID, schema: UpdateSchemaType) -> ModelType:
        """Update record"""
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return None

        obj_data = schema.model_dump(exclude_unset=True)
        for key, value in obj_data.items():
            setattr(db_obj, key, value)

        self._session.add(db_obj)
        await self._session.commit()
        await self._session.refresh(db_obj)
        return db_obj

    async def delete(self, id: UUID) -> bool:
        """Delete record"""
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return False

        await self._session.delete(db_obj)
        await self._session.commit()
        return True 