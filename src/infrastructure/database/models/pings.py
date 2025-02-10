from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC


class Pings(BaseModel):
    __tablename__ = "pings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    sender_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    recipient_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    sender_name: Mapped[str] = mapped_column(nullable=True)
    recipient_name: Mapped[str] = mapped_column(nullable=True)

    sender: Mapped["Users"] = relationship(
        "Users",
        foreign_keys=[sender_id],
        back_populates="sent_pings"
    )
    recipient: Mapped["Users"] = relationship(
        "Users",
        foreign_keys=[recipient_id],
        back_populates="received_pings"
    )

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )


from src.infrastructure.database.models.users import Users
