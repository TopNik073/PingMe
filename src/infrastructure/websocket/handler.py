"""
WebSocket Handler - Main handler for WebSocket connections.

Handles authentication, message routing, typing indicators, and user status updates.
"""

import json
import asyncio
import time
import contextlib
from typing import Any
from collections.abc import Callable
from uuid import UUID
from pydantic import ValidationError

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.websocket.connection_manager import ConnectionManager
from src.infrastructure.websocket.rate_limiter import RateLimiter
from src.infrastructure.security.jwt import JWTHandler
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.application.services.message_service import MessageService
from src.application.services.conversation_service import ConversationService
from src.presentation.schemas.conversations import MediaResponse
from src.presentation.schemas.websocket import (
    WSBaseMessage,
    WSAuthMessage,
    WSMessageCreate,
    WSMessageEdit,
    WSMessageDelete,
    WSMessageForward,
    WSTypingStart,
    WSTypingStop,
    WSPing,
    WSMarkRead,
    WSAck,
    WSSubscribe,
    WSUnsubscribe,
    WSMessageReceived,
    WSMessageEdited,
    WSMessageDeleted,
    WSMessageForwarded,
    WSTypingIndicator,
    WSPong,
    WSAuthSuccess,
    WSMarkReadSuccess,
    WSMessageRead,
    WSMessageAck,
    WSError,
    WSErrorCode,
)
from src.core.config import settings
from src.core.logging import get_logger
from src.presentation.middlewares.ws_logging import set_websocket_user_id

logger = get_logger(__name__)

jwt_handler = JWTHandler()

# Global rate limiter instance
rate_limiter = RateLimiter(
    messages_per_minute=settings.WS_RATE_LIMIT_MESSAGES_PER_MINUTE,
    typing_per_minute=settings.WS_RATE_LIMIT_TYPING_PER_MINUTE,
    general_per_minute=settings.WS_RATE_LIMIT_GENERAL_PER_MINUTE,
)


class WebSocketHandler:
    """
    Handles WebSocket connections and message processing.
    
    Features:
    - JWT authentication
    - Message creation, editing, deletion, forwarding
    - Typing indicators with auto-timeout
    - User online/offline status management
    - Heartbeat (ping/pong)
    """
    
    def __init__(  # noqa: PLR0913
        self,
        websocket: WebSocket,
        connection_manager: ConnectionManager,
        session: AsyncSession,
        message_service: MessageService,
        conversation_service: ConversationService,
        user_repository: UserRepository,
    ):
        self.websocket = websocket
        self.connection_manager = connection_manager
        self.session = session
        self.message_service = message_service
        self.conversation_service = conversation_service
        self.user_repository = user_repository
        
        self.user_id: UUID | None = None
        self.user_name: str | None = None
        self.authenticated = False
        
        # Typing indicator tracking: conversation_id -> asyncio.Task
        self.typing_tasks: dict[UUID, asyncio.Task] = {}
        
        # Heartbeat tracking
        self.last_ping_time: float | None = None
        self.heartbeat_monitor_task: asyncio.Task | None = None
        
        # Sequence counter for outgoing messages
        self._sequence_counter: int = 0
        
        # Message handlers mapping: message_type -> (schema_class, handler_method)
        self.message_handlers: dict[str, tuple[type, Callable[[Any], Any]]] = {
            "auth": (WSAuthMessage, self.handle_auth),
            "message": (WSMessageCreate, self.handle_message_create),
            "message_edit": (WSMessageEdit, self.handle_message_edit),
            "message_delete": (WSMessageDelete, self.handle_message_delete),
            "message_forward": (WSMessageForward, self.handle_message_forward),
            "typing_start": (WSTypingStart, self.handle_typing_start),
            "typing_stop": (WSTypingStop, self.handle_typing_stop),
            "ping": (WSPing, self.handle_ping),
            "mark_read": (WSMarkRead, self.handle_mark_read),
            "ack": (WSAck, self.handle_ack),
            "subscribe": (WSSubscribe, self.handle_subscribe),
            "unsubscribe": (WSUnsubscribe, self.handle_unsubscribe),
        }
    
    async def authenticate(self, token: str) -> bool:
        """Authenticate user via JWT token"""
        try:
            payload = jwt_handler.decode_token(token)
            
            # Verify token
            if payload.get("type") != "access":
                return False
            
            if jwt_handler.is_token_expired(payload):
                return False
            
            user_id_str = payload.get("sub")
            if not user_id_str:
                return False
            
            user_id = UUID(user_id_str)
            
            # Get user from database
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                return False
            
            self.user_id = user_id
            self.user_name = user.name
            self.authenticated = True
            
            # Set user_id for logging
            set_websocket_user_id(self.websocket, str(user_id))
            
            # Update user status
            await self.user_repository.update_online_status_and_last_seen(
                user_id, is_online=True
            )
            await self.session.commit()
            
            # Connect to connection manager
            await self.connection_manager.connect(self.websocket, user_id)
            
            # Start heartbeat monitoring
            self.last_ping_time = time.time()
            self.heartbeat_monitor_task = asyncio.create_task(self._heartbeat_monitor())
            
            logger.info("User %s authenticated via WebSocket", user_id)
            
            return True
        except Exception as e:
            logger.error("Authentication failed: %s", e)
            return False
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number"""
        self._sequence_counter += 1
        return self._sequence_counter
    
    async def _send_message_with_sequence(self, message: WSBaseMessage):
        """Send message with sequence number (except ping/pong)"""
        if message.type not in ["ping", "pong"]:
            message.sequence = self._get_next_sequence()
        message_data = message.model_dump(mode='json', exclude_none=True)
        await self.websocket.send_json(message_data)
    
    async def send_error(self, code: str, message: str, details: dict | None = None):
        """Send error message to client"""
        error = WSError(code=code, message=message, details=details)
        await self._send_message_with_sequence(error)
    
    async def handle_auth(self, message: WSAuthMessage):
        """Handle authentication message"""
        if self.authenticated:
            await self.send_error(
                WSErrorCode.INVALID_MESSAGE,
                "Already authenticated"
            )
            return
        
        success = await self.authenticate(message.token)
        if success:
            auth_success = WSAuthSuccess(
                user_id=self.user_id,
                user_name=self.user_name
            )
            await self._send_message_with_sequence(auth_success)
        else:
            await self.send_error(
                WSErrorCode.AUTH_FAILED,
                "Authentication failed. Invalid or expired token."
            )
    
    async def handle_message_create(self, message: WSMessageCreate):
        """Handle message creation"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            # Create message
            created_message = await self.message_service.create_message(
                user_id=self.user_id,
                conversation_id=message.conversation_id,
                content=message.content,
                forwarded_from_id=message.forwarded_from_id,
                media_ids=message.media_ids,
            )
            
            # Subscribe to conversation if not already subscribed
            await self.connection_manager.subscribe_to_conversation(
                self.user_id, message.conversation_id
            )
            
            # Get participants
            participant_ids = await self.message_service.get_conversation_participants(
                message.conversation_id
            )
            
            # Prepare media list for response
            media_list = []
            if created_message.media:
                media_list = [
                    MediaResponse.model_validate(media)
                    for media in created_message.media
                ]
            
            # Prepare message response
            message_response = WSMessageReceived(
                id=created_message.id,
                content=created_message.content,
                sender_id=created_message.sender_id,
                conversation_id=created_message.conversation_id,
                forwarded_from_id=created_message.forwarded_from_id,
                sender_name=created_message.sender.name,
                media=media_list,
                created_at=created_message.created_at,
                updated_at=created_message.updated_at,
                is_edited=created_message.is_edited,
                is_deleted=created_message.is_deleted,
                sequence=self._get_next_sequence(),
            )
            
            # Broadcast to all participants except sender
            await self.connection_manager.broadcast_to_conversation_participants(
                message_response.model_dump(mode='json', exclude_none=True),
                participant_ids,
                exclude_user_id=[],
            )
            
        except ValueError as e:
            await self.send_error(WSErrorCode.INVALID_MESSAGE, str(e))
        except Exception as e:
            logger.exception("Failed to create message: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to create message"
            )
    
    async def handle_message_edit(self, message: WSMessageEdit):
        """Handle message editing"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            edited_message = await self.message_service.edit_message(
                user_id=self.user_id,
                message_id=message.message_id,
                content=message.content,
            )
            
            # Get participants
            participant_ids = await self.message_service.get_conversation_participants(
                edited_message.conversation_id
            )
            
            # Prepare edit response
            edit_response = WSMessageEdited(
                message_id=edited_message.id,
                content=edited_message.content,
                updated_at=edited_message.updated_at,
                sequence=self._get_next_sequence(),
            )
            
            # Broadcast to all participants
            await self.connection_manager.broadcast_to_conversation_participants(
                edit_response.model_dump(mode='json', exclude_none=True),
                participant_ids,
            )
            
        except ValueError as e:
            await self.send_error(WSErrorCode.INVALID_MESSAGE, str(e))
        except Exception as e:
            logger.exception("Failed to edit message: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to edit message"
            )
    
    async def handle_message_delete(self, message: WSMessageDelete):
        """Handle message deletion"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            deleted_message = await self.message_service.delete_message(
                user_id=self.user_id,
                message_id=message.message_id,
            )
            
            # Get participants
            participant_ids = await self.message_service.get_conversation_participants(
                deleted_message.conversation_id
            )
            
            # Prepare delete response
            delete_response = WSMessageDeleted(
                message_id=deleted_message.id,
                conversation_id=deleted_message.conversation_id,
                deleted_at=deleted_message.deleted_at,
                sequence=self._get_next_sequence(),
            )
            
            # Broadcast to all participants
            await self.connection_manager.broadcast_to_conversation_participants(
                delete_response.model_dump(mode='json', exclude_none=True),
                participant_ids,
            )
            
        except ValueError as e:
            await self.send_error(WSErrorCode.INVALID_MESSAGE, str(e))
        except Exception as e:
            logger.exception("Failed to delete message: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to delete message"
            )
    
    async def handle_message_forward(self, message: WSMessageForward):
        """Handle message forwarding"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            forwarded_message = await self.message_service.forward_message(
                user_id=self.user_id,
                message_id=message.message_id,
                target_conversation_id=message.conversation_id,
            )
            
            # Subscribe to target conversation if not already subscribed
            await self.connection_manager.subscribe_to_conversation(
                self.user_id, message.conversation_id
            )
            
            # Get participants
            participant_ids = await self.message_service.get_conversation_participants(
                message.conversation_id
            )
            
            # Prepare forward response
            forward_response = WSMessageForwarded(
                original_message_id=message.message_id,
                new_message_id=forwarded_message.id,
                conversation_id=forwarded_message.conversation_id,
                forwarded_from_id=forwarded_message.forwarded_from_id,
                content=forwarded_message.content,
                created_at=forwarded_message.created_at,
                sequence=self._get_next_sequence(),
            )
            
            # Broadcast to all participants except sender
            await self.connection_manager.broadcast_to_conversation_participants(
                forward_response.model_dump(mode='json', exclude_none=True),
                participant_ids,
            )
            
        except ValueError as e:
            await self.send_error(WSErrorCode.INVALID_MESSAGE, str(e))
        except Exception as e:
            logger.exception("Failed to forward message: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to forward message"
            )
    
    async def _typing_timeout(self, conversation_id: UUID):
        """Auto-stop typing indicator after timeout"""
        await asyncio.sleep(settings.WS_TYPING_TIMEOUT)
        
        # Check if task still exists (not cancelled)
        if conversation_id in self.typing_tasks:
            await self.handle_typing_stop_internal(conversation_id)
    
    async def handle_typing_start(self, message: WSTypingStart):
        """Handle typing start indicator"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            # Cancel existing typing task if any
            if message.conversation_id in self.typing_tasks:
                self.typing_tasks[message.conversation_id].cancel()
            
            # Get participants
            participant_ids = await self.message_service.get_conversation_participants(
                message.conversation_id
            )
            
            # Create typing indicator
            typing_indicator = WSTypingIndicator(
                type="typing_start",
                user_id=self.user_id,
                user_name=self.user_name,
                conversation_id=message.conversation_id,
                sequence=self._get_next_sequence(),
            )
            
            # Broadcast to all participants except sender
            await self.connection_manager.broadcast_to_conversation_participants(
                typing_indicator.model_dump(mode='json', exclude_none=True),
                participant_ids,
                exclude_user_id=[self.user_id],
            )
            
            # Schedule auto-stop
            task = asyncio.create_task(self._typing_timeout(message.conversation_id))
            self.typing_tasks[message.conversation_id] = task
            
        except Exception as e:
            logger.exception("Failed to handle typing start: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to handle typing indicator"
            )
    
    async def handle_typing_stop_internal(self, conversation_id: UUID):
        """Internal method to stop typing indicator"""
        if conversation_id not in self.typing_tasks:
            return
        
        # Cancel and remove task
        task = self.typing_tasks.pop(conversation_id, None)
        if task:
            task.cancel()
        
        try:
            # Get participants
            participant_ids = await self.message_service.get_conversation_participants(
                conversation_id
            )
            
            # Create typing stop indicator
            typing_indicator = WSTypingIndicator(
                type="typing_stop",
                user_id=self.user_id,
                user_name=self.user_name,
                conversation_id=conversation_id,
                sequence=self._get_next_sequence(),
            )
            
            # Broadcast to all participants except sender
            await self.connection_manager.broadcast_to_conversation_participants(
                typing_indicator.model_dump(mode='json', exclude_none=True),
                participant_ids,
                exclude_user_id=[self.user_id],
            )
        except Exception as e:
            logger.warning("Failed to send typing stop: %s", e)
    
    async def handle_typing_stop(self, message: WSTypingStop):
        """Handle typing stop indicator"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        await self.handle_typing_stop_internal(message.conversation_id)
    
    async def handle_ping(self, message: WSPing):
        """Handle ping (heartbeat)"""
        # Update last ping time
        self.last_ping_time = time.time()
        
        pong = WSPong()
        pong_data = pong.model_dump(mode='json')
        await self.websocket.send_json(pong_data)
    
    async def _heartbeat_monitor(self):
        """Monitor heartbeat and disconnect if timeout"""
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            
            if not self.authenticated:
                break
            
            if self.last_ping_time is None:
                # No ping received yet, start timer from now
                self.last_ping_time = time.time()
                continue
            
            time_since_ping = time.time() - self.last_ping_time
            
            if time_since_ping > settings.WS_HEARTBEAT_TIMEOUT:
                logger.warning(
                    "Heartbeat timeout for user %s (%.1f seconds since last ping)",
                    self.user_id, time_since_ping
                )
                await self.websocket.close()
                break
    
    async def handle_mark_read(self, message: WSMarkRead):
        """Handle marking message as read"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            success = await self.conversation_service.update_last_read_message_id(
                user_id=self.user_id,
                conversation_id=message.conversation_id,
                message_id=message.message_id,
            )
            
            if success:
                # Send success response to the user who marked as read
                mark_read_success = WSMarkReadSuccess(
                    message_id=message.message_id,
                    conversation_id=message.conversation_id,
                )
                await self._send_message_with_sequence(mark_read_success)
                
                # Broadcast to all participants (except the reader)
                participant_ids = await self.message_service.get_conversation_participants(
                    message.conversation_id
                )
                
                read_notification = WSMessageRead(
                    message_id=message.message_id,
                    conversation_id=message.conversation_id,
                    reader_id=self.user_id,
                    reader_name=self.user_name,
                    sequence=self._get_next_sequence(),
                )
                
                await self.connection_manager.broadcast_to_conversation_participants(
                    read_notification.model_dump(mode='json', exclude_none=True),
                    participant_ids,
                    exclude_user_id=[self.user_id],
                )
            else:
                await self.send_error(
                    WSErrorCode.MESSAGE_NOT_FOUND,
                    "Message not found or you don't have permission to mark it as read"
                )
        except Exception as e:
            logger.exception("Failed to mark message as read: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to mark message as read"
            )
    
    async def handle_ack(self, message: WSAck):
        """Handle message acknowledgment"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        # Log acknowledgment for debugging
        logger.debug(
            "Message %s acknowledged by user %s (sequence: %s)",
            message.message_id, self.user_id, message.sequence
        )
        
        # Send acknowledgment response
        ack_response = WSMessageAck(
            message_id=message.message_id,
            status="delivered",
        )
        await self._send_message_with_sequence(ack_response)
    
    async def handle_subscribe(self, message: WSSubscribe):
        """Handle subscription to a conversation"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            # Check if user is a participant by trying to get conversation
            # If user is not a participant, get_conversation_by_id will return None
            # or we can check via message service
            participant_ids = await self.message_service.get_conversation_participants(
                message.conversation_id
            )
            
            if self.user_id not in participant_ids:
                await self.send_error(
                    WSErrorCode.PERMISSION_DENIED,
                    "You are not a participant of this conversation"
                )
                return
            
            # Subscribe to conversation
            await self.connection_manager.subscribe_to_conversation(
                self.user_id, message.conversation_id
            )
            
            logger.debug(
                "User %s subscribed to conversation %s",
                self.user_id, message.conversation_id
            )
        except Exception as e:
            logger.exception("Failed to subscribe to conversation: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to subscribe to conversation"
            )
    
    async def handle_unsubscribe(self, message: WSUnsubscribe):
        """Handle unsubscription from a conversation"""
        if not self.authenticated:
            await self.send_error(WSErrorCode.AUTH_REQUIRED, "Authentication required")
            return
        
        try:
            # Unsubscribe from conversation
            await self.connection_manager.unsubscribe_from_conversation(
                self.user_id, message.conversation_id
            )
            
            logger.debug(
                "User %s unsubscribed from conversation %s",
                self.user_id, message.conversation_id
            )
        except Exception as e:
            logger.exception("Failed to unsubscribe from conversation: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Failed to unsubscribe from conversation"
            )
    
    async def process_message(self, raw_message: str):
        """Process incoming WebSocket message"""
        
        try:
            # Check message size
            if len(raw_message.encode('utf-8')) > settings.WS_MAX_MESSAGE_SIZE:
                await self.send_error(
                    WSErrorCode.INVALID_MESSAGE,
                    f"Message size exceeds maximum allowed size of {settings.WS_MAX_MESSAGE_SIZE} bytes"
                )
                return
            
            data = json.loads(raw_message)
            message_type = data.get("type")
            
            if not message_type:
                await self.send_error(
                    WSErrorCode.INVALID_MESSAGE,
                    "Message type is required"
                )
                return
            
            # Check rate limit (skip for pong responses)
            if message_type != "pong" and not rate_limiter.is_allowed(self.user_id, message_type):
                await self.send_error(
                    WSErrorCode.RATE_LIMIT_EXCEEDED,
                    f"Rate limit exceeded for message type '{message_type}'"
                )
                return
            
            # Route to appropriate handler using dictionary
            handler_info = self.message_handlers.get(message_type)
            
            if handler_info:
                schema_class, handler_method = handler_info
                try:
                    # Parse message with appropriate schema
                    message = schema_class(**data)
                    # Call handler method
                    await handler_method(message)
                except ValidationError as e:
                    logger.warning("Validation error for %s message: %s", message_type, e)
                    await self.send_error(
                        WSErrorCode.INVALID_MESSAGE,
                        f"Invalid message format for type '{message_type}': {e!s}"
                    )
                except Exception as e:
                    logger.exception("Failed to process %s message: %s", message_type, e)
                    await self.send_error(
                        WSErrorCode.INTERNAL_ERROR,
                        f"Internal error processing {message_type} message"
                    )
            else:
                await self.send_error(
                    WSErrorCode.INVALID_MESSAGE,
                    f"Unknown message type: {message_type}"
                )
        except json.JSONDecodeError:
            await self.send_error(
                WSErrorCode.INVALID_MESSAGE,
                "Invalid JSON format"
            )
        except Exception as e:
            logger.exception("Error processing message: %s", e)
            await self.send_error(
                WSErrorCode.INTERNAL_ERROR,
                "Internal server error"
            )
    
    async def handle_connection(self):
        """
        Main connection handler.
        
        If token is provided (from query parameter), authenticate immediately.
        Otherwise, wait for auth message.
        """
        await self.websocket.accept()
        
        try:
            while True:
                raw_message = await self.websocket.receive_text()
                await self.process_message(raw_message)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected for user %s", self.user_id)
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup on disconnect"""
        # Stop heartbeat monitor
        if self.heartbeat_monitor_task:
            self.heartbeat_monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.heartbeat_monitor_task
        
        # Cancel all typing tasks
        for task in self.typing_tasks.values():
            task.cancel()
        self.typing_tasks.clear()
        
        # Clear rate limiter for this user
        if self.user_id:
            rate_limiter.reset_user(self.user_id)
        
        # Disconnect from connection manager
        if self.user_id:
            disconnected_user_id = await self.connection_manager.disconnect(self.websocket)
            
            # Update user status
            if disconnected_user_id:
                # Check if user has any remaining connections
                if not self.connection_manager.is_user_online(disconnected_user_id):
                    await self.user_repository.update_online_status_and_last_seen(
                        disconnected_user_id, is_online=False
                    )
                    await self.session.commit()
                    
                    # Notify other users (this would require getting user's conversations)
                    # For now, we'll skip this to avoid complexity
                    
                logger.info("User %s disconnected and status updated", disconnected_user_id)

