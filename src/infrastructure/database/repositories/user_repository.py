from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.base import SQLAlchemyRepository
from src.infrastructure.database.models.users import Users
from src.presentation.schemas.users import UserRegisterDTO, UserUpdate


class UserRepository(SQLAlchemyRepository[Users, UserRegisterDTO, UserUpdate]):
    """Repository for managing users"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Users)
