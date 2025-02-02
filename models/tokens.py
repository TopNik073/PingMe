from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

import uuid
from datetime import datetime

from models.BaseModel import BaseModel, get_datetime_UTC


class Tokens(BaseModel):
    __tablename__ = "tokens"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )
    
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["Users"] = relationship(back_populates="tokens")

    token: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=get_datetime_UTC)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

from models.users import Users
