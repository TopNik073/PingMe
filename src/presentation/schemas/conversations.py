from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from typing import TYPE_CHECKING

from src.infrastructure.database.enums.ConversationType import ConversationType
from src.infrastructure.database.enums.Roles import Roles
from src.presentation.schemas.users import UserResponseSchema

if TYPE_CHECKING:
    from src.infrastructure.database.models.conversations import Conversations


def set_conversation_avatar_url(conversation: "Conversations") -> None:
    """Set avatar_url on conversation object if avatar is explicitly loaded.
    This function should be called after loading conversation with selectinload(Conversations.avatar)
    to avoid lazy loading issues.
    """
    # Only set avatar_url if avatar was explicitly loaded via selectinload
    # We can safely access avatar here because it's already loaded
    if hasattr(conversation, "avatar") and conversation.avatar is not None:
        conversation.avatar_url = conversation.avatar.url
    else:
        conversation.avatar_url = None


class ConversationCreateRequest(BaseModel):
    """Schema for creating a conversation
    
    Note: conversation_type is determined automatically by the server based on participant count:
    - 2 participants = DIALOG
    - 3+ participants = POLYLOGUE
    """
    name: str | None = Field(..., max_length=50)
    participant_ids: list[UUID] | None = Field(default=None, description="Optional list of user IDs to add as participants")


class ConversationUpdateRequest(BaseModel):
    """Schema for updating a conversation"""
    name: str | None = Field(None, min_length=1, max_length=100)
    conversation_type: ConversationType | None = None
    is_deleted: bool | None = None


class ConversationJoinRequest(BaseModel):
    """Schema for joining a conversation"""
    conversation_id: UUID


class ParticipantRoleUpdateRequest(BaseModel):
    """Schema for updating participant role"""
    role: Roles = Field(..., description="New role for the participant")


class ParticipantResponse(BaseModel):
    """Schema for conversation participant"""
    user_id: UUID
    conversation_id: UUID
    role: Roles
    is_user_banned: bool
    is_chat_muted: bool
    last_read_message_id: UUID | None = None
    user: UserResponseSchema
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# MessageResponse moved to src.presentation.schemas.messages


class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    id: UUID
    name: str
    conversation_type: ConversationType
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: datetime | None = None
    avatar_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_avatar_url(cls, data):
        """Extract avatar URL from relationship before validation.
        Only processes dict input. For SQLAlchemy models, avatar_url must be set
        explicitly using set_conversation_avatar_url() after loading avatar via selectinload
        to avoid lazy loading. Never accesses avatar attribute directly.
        """
        if isinstance(data, dict):
            # If already a dict, check if it has avatar nested
            if data.get("avatar"):
                data["avatar_url"] = data["avatar"].url if hasattr(data["avatar"], "url") else None
            return data
        
        # For SQLAlchemy model instances, do nothing - never access avatar attribute
        # avatar_url must be set explicitly before validation using set_conversation_avatar_url()
        # This completely avoids any risk of triggering lazy loading
        return data

    class Config:
        from_attributes = True


class MediaResponse(BaseModel):
    """Schema for media response"""
    id: UUID
    content_type: str
    url: str
    size: int
    message_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationBriefResponse(BaseModel):
    """Schema for brief conversation information (for search and profiles)"""
    id: UUID
    name: str
    conversation_type: ConversationType
    participant_count: int | None = Field(None, description="Number of participants (only if user is participant)")
    avatar_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_avatar_url(cls, data):
        """Extract avatar URL from relationship before validation.
        Only processes dict input. For SQLAlchemy models, avatar_url must be set
        explicitly using set_conversation_avatar_url() after loading avatar via selectinload
        to avoid lazy loading. Never accesses avatar attribute directly.
        """
        if isinstance(data, dict):
            # If already a dict, check if it has avatar nested
            if data.get("avatar"):
                data["avatar_url"] = data["avatar"].url if hasattr(data["avatar"], "url") else None
            return data
        
        # For SQLAlchemy model instances, do nothing - never access avatar attribute
        # avatar_url must be set explicitly before validation using set_conversation_avatar_url()
        # This completely avoids any risk of triggering lazy loading
        return data

    class Config:
        from_attributes = True

