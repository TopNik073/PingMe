from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from datetime import datetime

from models.BaseModel import BaseModel, get_datetime_UTC

from enums.Roles import Roles


class UserConversation(BaseModel):
    __tablename__ = "user_conversation"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        primary_key=True
    )

    user: Mapped["Users"] = relationship(back_populates="conversations")
    conversation: Mapped["Conversations"] = relationship(back_populates="users")

    last_read_message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id"),
        nullable=True
    )
    last_read_message: Mapped["Messages"] = relationship(back_populates="last_read_by")

    role: Mapped[Roles] = mapped_column(
        Enum(Roles, name="role_type", create_constraint=True),
        nullable=False, default=Roles.MEMBER
    )

    is_user_banned: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_chat_muted: Mapped[bool] = mapped_column(nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )

    __table_args__ = (
        Index('ix_user_conversation_user_id', 'user_id'),
    )

from models.users import Users
from models.conversations import Conversations
from models.messages import Messages
