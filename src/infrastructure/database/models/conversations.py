from typing import List

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum
import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC
from src.infrastructure.database.enums.ConversationType import ConversationType


class Conversations(BaseModel):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    name: Mapped[str] = mapped_column(nullable=False)

    users: Mapped[List["UserConversation"]] = relationship(back_populates="conversation")
    messages: Mapped[List["Messages"]] = relationship(back_populates="conversation")

    conversation_type: Mapped[ConversationType] = mapped_column(
        Enum(ConversationType, name="conversation_type", create_constraint=True),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )

    is_deleted: Mapped[bool] = mapped_column(nullable=False, default=False)
    deleted_at: Mapped[datetime] = mapped_column(nullable=True)

from src.infrastructure.database.models.user_conversation import UserConversation
from src.infrastructure.database.models.messages import Messages
