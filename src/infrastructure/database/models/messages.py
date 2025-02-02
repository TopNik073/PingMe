from typing import List

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, TEXT

import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC

class Messages(BaseModel):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    content: Mapped[str] = mapped_column(TEXT, nullable=True)

    sender_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False
    )

    sender: Mapped["Users"] = relationship(back_populates="messages")
    forwarded_from_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )
    forwarded_from: Mapped["Users"] = relationship(back_populates="forwarded_messages")
    conversation: Mapped["Conversations"] = relationship(back_populates="messages")
    media: Mapped[List["Media"]] = relationship(back_populates="message")

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )

    is_deleted: Mapped[bool] = mapped_column(nullable=False, default=False)
    deleted_at: Mapped[datetime] = mapped_column(nullable=True)

    last_read_by: Mapped[List["UserConversation"]] = relationship(back_populates="last_read_message")

    __table_args__ = (
        Index(
            'ix_messages_content_trgm',
            text('content gin_trgm_ops'),
            postgresql_using='gin'
        ),
    )

from src.infrastructure.database.models.users import Users
from src.infrastructure.database.models.conversations import Conversations
from src.infrastructure.database.models.user_conversation import UserConversation
from src.infrastructure.database.models.media import Media