from typing import Type, List, AsyncGenerator
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction
from sqlalchemy.orm import selectinload

from src.application.interfaces.repositories import AbstractRepository, MODEL_TYPE, PYDANTIC_TYPE


class SQLAlchemyRepository(AbstractRepository[MODEL_TYPE]):
    model = type[MODEL_TYPE]

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_transaction(self) -> AsyncGenerator[AsyncSessionTransaction, None]:
        async with self._session.begin() as transaction:
            yield transaction

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        yield self._session

    async def create(self, schema: PYDANTIC_TYPE) -> MODEL_TYPE:
        """Create a new record"""
        db_obj = self.model(**schema.model_dump())
        self._session.add(db_obj)
        await self._session.commit()
        await self._session.refresh(db_obj)
        return db_obj

    async def get_by_id(
        self, id: UUID, include_relations: list[str] | None = None
    ) -> MODEL_TYPE | None:
        """Get record by id"""
        query = select(self.model).where(self.model.id == id)
        if include_relations:
            for relation in include_relations:
                query = query.options(selectinload(getattr(self.model, relation)))
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_filter(
        self, include_relations: list[str] | None = None, **filters
    ) -> List[MODEL_TYPE] | None:
        """Get records by filters with optional related data loading"""
        query = select(self.model)

        # Add relation loading if specified
        if include_relations:
            for relation in include_relations:
                query = query.options(selectinload(getattr(self.model, relation)))

        # Add filters
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)

        result = await self._session.execute(query)
        records = result.scalars().all()

        return list(records) if records else None

    async def update(
        self, id: UUID | None = None, data: PYDANTIC_TYPE | MODEL_TYPE = None
    ) -> MODEL_TYPE:
        """
        Update record.
        Can accept either a Pydantic schema or an already updated model instance.
        If model instance is provided, id parameter is ignored.
        """
        if data is None:
            raise ValueError("Data must be provided")

        if type(data) is self.model:
            # If we already have a model instance, just update it
            db_obj = data
            self._session.add(db_obj)
        else:
            # If we have a schema, proceed with normal update
            update_data = data.model_dump(exclude_unset=True)

            query = select(self.model).where(self.model.id == id).with_for_update()

            result = await self._session.execute(query)
            db_obj = result.scalar_one_or_none()

            if db_obj is None:
                return None

            for key, value in update_data.items():
                setattr(db_obj, key, value)

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

    async def get_paginated(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        include_relations: list[str] | None = None,
        **filters,
    ) -> List[MODEL_TYPE]:
        """Get paginated records with optional filters and related data loading"""
        query = select(self.model)

        # Add relation loading if specified
        if include_relations:
            for relation in include_relations:
                query = query.options(selectinload(getattr(self.model, relation)))

        # Add filters
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)

        # Add pagination
        query = query.offset(skip).limit(limit)

        result = await self._session.execute(query)
        records = result.scalars().all()

        res = [
            {
                "total": len(records),
                "page": skip // limit + 1,
                "limit": limit,
            }
        ]

        return res.append(records)
