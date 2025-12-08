"""
WebSocket protocol schemas for PingMe messenger.

All WebSocket messages follow a JSON format with a 'type' field indicating the message type.
"""

from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from src.presentation.schemas.conversations import MediaResponse


# ==================== Base Message Types ====================


class WSBaseMessage(BaseModel):
    """Base class for all WebSocket messages"""

    type: str
    sequence: int | None = Field(None, description='Sequence number for message ordering')


# ==================== Incoming Messages (Client -> Server) ====================


class WSAuthMessage(WSBaseMessage):
    """Authentication message - first message from client"""

    type: Literal['auth'] = 'auth'
    token: str = Field(..., description='JWT access token')


class WSMessageCreate(WSBaseMessage):
    """Create a new message"""

    type: Literal['message'] = 'message'
    conversation_id: UUID = Field(..., description='ID of the conversation')
    content: str = Field(..., min_length=1, max_length=1000, description='Message content (max 1000 characters)')
    forwarded_from_id: UUID | None = Field(None, description='Original message ID if forwarding')
    media_ids: list[UUID] | None = Field(None, description='List of media IDs to attach to the message')


class WSMessageEdit(WSBaseMessage):
    """Edit an existing message"""

    type: Literal['message_edit'] = 'message_edit'
    message_id: UUID = Field(..., description='ID of the message to edit')
    content: str = Field(..., min_length=1, max_length=1000, description='New message content (max 1000 characters)')


class WSMessageDelete(WSBaseMessage):
    """Delete a message"""

    type: Literal['message_delete'] = 'message_delete'
    message_id: UUID = Field(..., description='ID of the message to delete')


class WSMessageForward(WSBaseMessage):
    """Forward a message to another conversation"""

    type: Literal['message_forward'] = 'message_forward'
    message_id: UUID = Field(..., description='ID of the message to forward')
    conversation_id: UUID = Field(..., description='Target conversation ID')


class WSTypingStart(WSBaseMessage):
    """Indicate that user started typing"""

    type: Literal['typing_start'] = 'typing_start'
    conversation_id: UUID = Field(..., description='ID of the conversation')


class WSTypingStop(WSBaseMessage):
    """Indicate that user stopped typing"""

    type: Literal['typing_stop'] = 'typing_stop'
    conversation_id: UUID = Field(..., description='ID of the conversation')


class WSPing(WSBaseMessage):
    """Heartbeat ping message"""

    type: Literal['ping'] = 'ping'


class WSMarkRead(WSBaseMessage):
    """Mark message as read"""

    type: Literal['mark_read'] = 'mark_read'
    message_id: UUID = Field(..., description='ID of the message that was read')
    conversation_id: UUID = Field(..., description='ID of the conversation')


class WSAck(WSBaseMessage):
    """Acknowledge message delivery"""

    type: Literal['ack'] = 'ack'
    message_id: UUID = Field(..., description='ID of the message being acknowledged')
    sequence: int | None = Field(None, description='Sequence number of the acknowledged message')


class WSSubscribe(WSBaseMessage):
    """Subscribe to a conversation"""

    type: Literal['subscribe'] = 'subscribe'
    conversation_id: UUID = Field(..., description='ID of the conversation to subscribe to')


class WSUnsubscribe(WSBaseMessage):
    """Unsubscribe from a conversation"""

    type: Literal['unsubscribe'] = 'unsubscribe'
    conversation_id: UUID = Field(..., description='ID of the conversation to unsubscribe from')


# ==================== Outgoing Messages (Server -> Client) ====================


class WSMessageReceived(WSBaseMessage):
    """New message received"""

    type: Literal['message'] = 'message'
    id: UUID
    content: str
    sender_id: UUID
    conversation_id: UUID
    forwarded_from_id: UUID | None = None
    sender_name: str
    media: list[MediaResponse] = Field(default_factory=list, description='List of media attached to the message')
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool


class WSMessageEdited(WSBaseMessage):
    """Message was edited"""

    type: Literal['message_edit'] = 'message_edit'
    message_id: UUID
    content: str
    updated_at: datetime


class WSMessageDeleted(WSBaseMessage):
    """Message was deleted"""

    type: Literal['message_delete'] = 'message_delete'
    message_id: UUID
    conversation_id: UUID
    deleted_at: datetime


class WSMessageForwarded(WSBaseMessage):
    """Message was forwarded"""

    type: Literal['message_forward'] = 'message_forward'
    original_message_id: UUID
    new_message_id: UUID
    conversation_id: UUID
    forwarded_from_id: UUID
    content: str
    created_at: datetime


class WSTypingIndicator(WSBaseMessage):
    """User typing indicator"""

    type: Literal['typing_start', 'typing_stop'] = Field(..., description='Typing event type')
    user_id: UUID
    user_name: str
    conversation_id: UUID


class WSUserOnline(WSBaseMessage):
    """User came online"""

    type: Literal['user_online'] = 'user_online'
    user_id: UUID
    user_name: str
    last_seen: datetime | None = None


class WSUserOffline(WSBaseMessage):
    """User went offline"""

    type: Literal['user_offline'] = 'user_offline'
    user_id: UUID
    user_name: str
    last_seen: datetime


class WSPong(WSBaseMessage):
    """Heartbeat pong response"""

    type: Literal['pong'] = 'pong'


class WSAuthSuccess(WSBaseMessage):
    """Authentication successful"""

    type: Literal['auth_success'] = 'auth_success'
    user_id: UUID
    user_name: str


class WSMarkReadSuccess(WSBaseMessage):
    """Message marked as read successfully"""

    type: Literal['mark_read_success'] = 'mark_read_success'
    message_id: UUID
    conversation_id: UUID


class WSMessageRead(WSBaseMessage):
    """Broadcast: message was read by a user"""

    type: Literal['message_read'] = 'message_read'
    message_id: UUID
    conversation_id: UUID
    reader_id: UUID
    reader_name: str


class WSMessageAck(WSBaseMessage):
    """Message acknowledgment response"""

    type: Literal['message_ack'] = 'message_ack'
    message_id: UUID
    status: Literal['delivered', 'read'] = Field('delivered', description='Acknowledgment status')


class WSError(WSBaseMessage):
    """Error message"""

    type: Literal['error'] = 'error'
    code: str = Field(..., description='Error code')
    message: str = Field(..., description='Human-readable error message')
    details: dict | None = Field(None, description='Additional error details')


# ==================== Error Codes ====================


class WSErrorCode:
    """WebSocket error codes"""

    AUTH_REQUIRED = 'AUTH_REQUIRED'
    AUTH_FAILED = 'AUTH_FAILED'
    INVALID_MESSAGE = 'INVALID_MESSAGE'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    CONVERSATION_NOT_FOUND = 'CONVERSATION_NOT_FOUND'
    MESSAGE_NOT_FOUND = 'MESSAGE_NOT_FOUND'
    USER_NOT_FOUND = 'USER_NOT_FOUND'
    INVALID_CONTENT = 'INVALID_CONTENT'
    RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
    INTERNAL_ERROR = 'INTERNAL_ERROR'


# ==================== Union Types for Message Parsing ====================

WSIncomingMessage = (
    WSAuthMessage
    | WSMessageCreate
    | WSMessageEdit
    | WSMessageDelete
    | WSMessageForward
    | WSTypingStart
    | WSTypingStop
    | WSPing
    | WSMarkRead
    | WSAck
    | WSSubscribe
    | WSUnsubscribe
)

WSOutgoingMessage = (
    WSMessageReceived
    | WSMessageEdited
    | WSMessageDeleted
    | WSMessageForwarded
    | WSTypingIndicator
    | WSUserOnline
    | WSUserOffline
    | WSPong
    | WSAuthSuccess
    | WSMarkReadSuccess
    | WSMessageRead
    | WSMessageAck
    | WSError
)
