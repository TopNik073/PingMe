from typing import Annotated
from collections.abc import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=bool(settings.DEBUG and settings.SQLALCHEMY_ECHO),
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for getting a database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DB_DEP = Annotated[AsyncSession, Depends(get_db)]
