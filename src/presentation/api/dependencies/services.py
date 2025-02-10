from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_db
from src.infrastructure.cache.redis.connection import get_redis
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.email.smtp_service import SMTPService
from src.infrastructure.cache.redis.auth_cache import AuthCache
from src.application.services.auth_service import AuthService


async def get_auth_service(
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> AuthService:
    """Get AuthService instance with all dependencies"""
    user_repository = UserRepository(session)
    auth_cache = AuthCache(redis)
    email_service = SMTPService()

    return AuthService(
        user_repository=user_repository,
        email_service=email_service,
        auth_cache=auth_cache,
    ) 