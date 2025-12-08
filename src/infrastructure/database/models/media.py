from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, BIGINT
from sqlalchemy import ForeignKey, CheckConstraint

import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC


class Media(BaseModel):
    __tablename__ = 'media'

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    content_type: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(BIGINT, nullable=False)
    message_id: Mapped[UUID | None] = mapped_column(ForeignKey('messages.id', ondelete='CASCADE'), nullable=True)
    story_id: Mapped[UUID | None] = mapped_column(ForeignKey('stories.id', ondelete='SET NULL'), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True
    )

    __table_args__ = (
        # Constraint: either message_id, story_id, user_id, or conversation_id must be set
        CheckConstraint(
            '(message_id IS NOT NULL) OR (story_id IS NOT NULL) OR (user_id IS NOT NULL) OR (conversation_id IS NOT NULL)',
            name='check_media_reference',
        ),
    )

    message: Mapped['Messages'] = relationship(back_populates='media')
    story: Mapped['Stories'] = relationship(back_populates='media')
    user: Mapped['Users'] = relationship(back_populates='avatar')
    conversation: Mapped['Conversations'] = relationship(back_populates='avatar')

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC, onupdate=get_datetime_UTC)


from src.infrastructure.database.models.messages import Messages
from src.infrastructure.database.models.stories import Stories
from src.infrastructure.database.models.users import Users
from src.infrastructure.database.models.conversations import Conversations
