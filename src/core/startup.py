"""
Application startup utilities.

Contains functions for initializing services and dependencies during application startup.
"""

from fastapi import FastAPI

from src.infrastructure.fcm.service import FCMService
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.core.logging import get_logger

logger = get_logger(__name__)


async def initialize_fcm_service(app: FastAPI) -> None:
    """
    Initialize FCM (Firebase Cloud Messaging) service.

    Creates a temporary database session, initializes FCM service,
    and stores it in app.state if initialization is successful.

    Args:
        app: FastAPI application instance
    """
    try:
        # Create a temporary session for FCM initialization
        async with AsyncSessionLocal() as session:
            try:
                user_repository = UserRepository(session)
                fcm_service = FCMService(user_repository=user_repository)
                initialized = await fcm_service.initialize()

                if initialized:
                    app.state.fcm_service = fcm_service
                    logger.info('FCM service initialized successfully')
                else:
                    logger.warning('FCM service initialization failed or skipped')
            except Exception as e:
                logger.warning('Failed to initialize FCM service: %s', e)
            finally:
                await session.close()
    except Exception as e:
        logger.warning('Failed to create session for FCM initialization: %s', e)
