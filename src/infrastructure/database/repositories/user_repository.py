from datetime import datetime
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from src.infrastructure.database.repositories.base import SQLAlchemyRepository
from src.infrastructure.database.models.users import Users
from src.infrastructure.database.models.BaseModel import get_datetime_UTC


class UserRepository(SQLAlchemyRepository[Users]):
    """Repository for managing users"""

    model: Users = Users

    async def update_online_status(self, user_id: UUID, is_online: bool) -> Users | None:
        """Update user's online status"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_online = is_online
        await self.flush()
        await self.refresh(user)

        return user

    async def update_last_seen(self, user_id: UUID, last_seen: datetime | None = None) -> Users | None:
        """Update user's last seen timestamp"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        if last_seen is None:
            last_seen = get_datetime_UTC()

        user.last_seen = last_seen
        await self.flush()
        await self.refresh(user)

        return user

    async def update_online_status_and_last_seen(
        self, user_id: UUID, is_online: bool, last_seen: datetime | None = None
    ) -> Users | None:
        """Update both online status and last seen in one operation"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_online = is_online

        if last_seen is None:
            last_seen = get_datetime_UTC()

        user.last_seen = last_seen
        await self.flush()
        await self.refresh(user)

        return user

    async def search_users(
        self,
        search_query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Users]:
        """
        Search users by name, username, or phone number.
        Uses case-insensitive ILIKE for pattern matching.
        """
        # Prepare search pattern (add % for wildcard matching)
        search_pattern = f'%{search_query}%'

        query = (
            select(self.model)
            .where(
                or_(
                    self.model.email.ilike(search_pattern),
                    self.model.name.ilike(search_pattern),
                    self.model.username.ilike(search_pattern),
                    self.model.phone_number.ilike(search_pattern),
                )
            )
            .options(selectinload(self.model.avatar))
            .order_by(self.model.name.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await self._session.execute(query)
        users = result.scalars().all()

        return list(users) if users else []
