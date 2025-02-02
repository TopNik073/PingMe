from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC


class Pings(BaseModel):
    __tablename__ = "pings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    sender: Mapped["Users"] = relationship(back_populates="sent_pings")
    recipient: Mapped["Users"] = relationship(back_populates="received_pings")

    is_delivered: Mapped[bool] = mapped_column(nullable=False, default=False)
    delivered_at: Mapped[datetime] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=get_datetime_UTC)

from src.infrastructure.database.models.users import Users
