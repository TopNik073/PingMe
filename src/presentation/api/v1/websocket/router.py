from fastapi import APIRouter, WebSocket

from src.infrastructure.websocket.connection_manager import ConnectionManager
from src.infrastructure.websocket.handler import WebSocketHandler
from src.infrastructure.database.session import DB_DEP
from src.presentation.api.dependencies import (
    CONVERSATION_SERVICE_DEP,
    MESSAGE_SERVICE_DEP,
)
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

connection_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session: DB_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    message_service: MESSAGE_SERVICE_DEP,
):
    """
    WebSocket endpoint for real-time messaging.

    Protocol:
    - All messages are JSON with 'type' field
    - See websocket.py schemas for message formats or docs/asyncapi.yml
    """
    user_repository = UserRepository(session)

    handler = WebSocketHandler(
        websocket=websocket,
        connection_manager=connection_manager,
        session=session,
        message_service=message_service,
        conversation_service=conversation_service,
        user_repository=user_repository,
    )

    await handler.handle_connection()

