from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC


class Stories(BaseModel):
    __tablename__ = 'stories'

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    user: Mapped['Users'] = relationship(back_populates='stories')
    content: Mapped[str] = mapped_column(nullable=True)
    media: Mapped['Media'] = relationship(back_populates='story')

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC, onupdate=get_datetime_UTC)


from src.infrastructure.database.models.users import Users
from src.infrastructure.database.models.media import Media
