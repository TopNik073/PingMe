"""
Message request schemas for REST API
"""

from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from src.presentation.schemas.users import UserResponseSchema
from src.presentation.schemas.conversations import MediaResponse


class MessageCreateRequest(BaseModel):
    """Schema for creating a message"""
    conversation_id: UUID = Field(..., description="Conversation ID")
    content: str = Field(..., min_length=1, max_length=1000, description="Message content (max 1000 characters)")
    forwarded_from_id: UUID | None = Field(None, description="Original message ID if forwarding")
    media_ids: list[UUID] | None = Field(None, description="List of media IDs to attach to the message")


class MessageEditRequest(BaseModel):
    """Schema for editing a message"""
    content: str = Field(..., min_length=1, max_length=1000, description="New message content (max 1000 characters)")


class MessageForwardRequest(BaseModel):
    """Schema for forwarding a message"""
    conversation_id: UUID = Field(..., description="Target conversation ID")


class MessageSearchRequest(BaseModel):
    """Schema for searching messages"""
    query: str = Field(..., min_length=1, description="Search query")


class MessageReadInfo(BaseModel):
    """Schema for message read information"""
    user_id: UUID
    name: str
    username: str | None = None
    read_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Schema for message response"""
    id: UUID
    content: str
    sender_id: UUID
    conversation_id: UUID
    forwarded_from_id: UUID | None = None
    sender: UserResponseSchema
    media: list[MediaResponse] = Field(default_factory=list, description="List of media attached to the message")
    read_by: list[MessageReadInfo] = Field(default_factory=list, description="List of users who read this message")
    created_at: datetime
    updated_at: datetime
    is_edited: bool
    is_deleted: bool
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True

