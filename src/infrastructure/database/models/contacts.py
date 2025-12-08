from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC


class Contacts(BaseModel):
    __tablename__ = 'contacts'

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False
    )
    contact_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )

    user: Mapped['Users'] = relationship('Users', foreign_keys=[user_id], back_populates='contacts')
    contact: Mapped['Users'] = relationship('Users', foreign_keys=[contact_id], back_populates='contacted_by')

    name: Mapped[str] = mapped_column(nullable=True)  # Пользовательское имя контакта
    is_blocked: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC, onupdate=get_datetime_UTC)


from src.infrastructure.database.models.users import Users
