from typing import Annotated

from fastapi import Depends

from src.infrastructure.database.session import DB_DEP
from src.infrastructure.cache.redis.connection import REDIS_DEP
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.email.smtp_service import SMTPService
from src.infrastructure.cache.redis.auth_cache import AuthCache
from src.application.services.auth_service import AuthService
from src.application.services.user_service import UserService


async def get_auth_service(session: DB_DEP, redis: REDIS_DEP) -> AuthService:
    """Get AuthService instance with all dependencies"""
    user_repository = UserRepository(session)
    auth_cache = AuthCache(redis)
    email_service = SMTPService()

    return AuthService(
        user_repository=user_repository,
        email_service=email_service,
        auth_cache=auth_cache,
    )


async def get_user_service(session: DB_DEP) -> UserService:
    return UserService(user_repository=UserRepository(session))


AUTH_SERVICE_DEP = Annotated[AuthService, Depends(get_auth_service)]
USER_SERVICE_DEP = Annotated[UserService, Depends(get_user_service)]
