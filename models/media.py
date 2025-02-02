from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, BIGINT
from sqlalchemy import ForeignKey

import uuid
from datetime import datetime

from models.BaseModel import BaseModel, get_datetime_UTC


class Media(BaseModel):
    __tablename__ = "media"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    content_type: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(BIGINT, nullable=False)
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True
    )
    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"),
        nullable=True
    )

    message: Mapped["Messages"] = relationship(back_populates="media")
    story: Mapped["Stories"] = relationship(back_populates="media")

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )

from models.messages import Messages
from models.stories import Stories
