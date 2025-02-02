from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.schema import UniqueConstraint

import uuid
from datetime import datetime

from models.BaseModel import BaseModel, get_datetime_UTC


class Contacts(BaseModel):
    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    contact_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    user: Mapped["Users"] = relationship(back_populates="contacts")
    contact: Mapped["Users"] = relationship(back_populates="contacted_by")

    contact_name: Mapped[str] = mapped_column(nullable=False)
    contact_phone_number: Mapped[str] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'contact_id', name='uq_user_contact'),
    )

from models.users import Users
