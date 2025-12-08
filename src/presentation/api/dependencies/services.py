from typing import Annotated

from fastapi import Depends

from src.infrastructure.database.session import DB_DEP
from src.infrastructure.cache.redis.connection import REDIS_DEP
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.repositories.conversation_repo import ConversationRepository
from src.infrastructure.database.repositories.message_repository import MessageRepository
from src.infrastructure.database.repositories.media_repository import MediaRepository
from src.infrastructure.email.smtp_service import SMTPService
from src.infrastructure.cache.redis.auth_cache import AuthCache
from src.infrastructure.yandex.s3.manager import S3Manager
from src.infrastructure.fcm.service import FCMService
from src.application.services.auth_service import AuthService
from src.application.services.user_service import UserService
from src.application.services.conversation_service import ConversationService
from src.application.services.media_service import MediaService
from src.application.services.message_service import MessageService


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


def get_s3_manager() -> S3Manager:
    """Get S3Manager instance"""
    return S3Manager()


async def get_user_service(session: DB_DEP, s3_manager: S3Manager = Depends(get_s3_manager)) -> UserService:
    """Get UserService instance with all dependencies"""
    user_repository = UserRepository(session)
    media_repository = MediaRepository(session)

    return UserService(
        user_repository=user_repository,
        media_repository=media_repository,
        s3_manager=s3_manager,
    )


async def get_conversation_service(
    session: DB_DEP, s3_manager: S3Manager = Depends(get_s3_manager)
) -> ConversationService:
    """Get ConversationService instance with all dependencies"""
    conversation_repository = ConversationRepository(session)
    user_repository = UserRepository(session)
    message_repository = MessageRepository(session)
    media_repository = MediaRepository(session)

    return ConversationService(
        conversation_repository=conversation_repository,
        user_repository=user_repository,
        message_repository=message_repository,
        media_repository=media_repository,
        s3_manager=s3_manager,
    )


async def get_media_service(session: DB_DEP, s3_manager: S3Manager = Depends(get_s3_manager)) -> MediaService:
    """Get MediaService instance with all dependencies"""
    media_repository = MediaRepository(session)
    conversation_repository = ConversationRepository(session)

    return MediaService(
        media_repository=media_repository,
        conversation_repository=conversation_repository,
        s3_manager=s3_manager,
    )


async def get_fcm_service(session: DB_DEP) -> FCMService:
    """Get FCMService instance"""
    user_repository = UserRepository(session)
    return FCMService(user_repository=user_repository)


async def get_message_service(
    session: DB_DEP,
    fcm_service: FCMService = Depends(get_fcm_service),
) -> MessageService:
    """Get MessageService instance with all dependencies"""
    message_repository = MessageRepository(session)
    user_repository = UserRepository(session)
    conversation_repository = ConversationRepository(session)
    media_repository = MediaRepository(session)
    conversation_service = ConversationService(
        conversation_repository=conversation_repository,
        user_repository=user_repository,
        message_repository=message_repository,
    )

    from src.presentation.api.v1.websocket.router import connection_manager  # noqa: PLC0415

    return MessageService(
        message_repository=message_repository,
        conversation_repository=conversation_repository,
        user_repository=user_repository,
        conversation_service=conversation_service,
        media_repository=media_repository,
        fcm_service=fcm_service,
        connection_manager=connection_manager,
    )


AUTH_SERVICE_DEP = Annotated[AuthService, Depends(get_auth_service)]
USER_SERVICE_DEP = Annotated[UserService, Depends(get_user_service)]
S3_MANAGER_DEP = Annotated[S3Manager, Depends(get_s3_manager)]
CONVERSATION_SERVICE_DEP = Annotated[ConversationService, Depends(get_conversation_service)]
MEDIA_SERVICE_DEP = Annotated[MediaService, Depends(get_media_service)]
FCM_SERVICE_DEP = Annotated[FCMService, Depends(get_fcm_service)]
MESSAGE_SERVICE_DEP = Annotated[MessageService, Depends(get_message_service)]
