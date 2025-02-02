from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum
import uuid
from datetime import datetime

from models.BaseModel import BaseModel, get_datetime_UTC
from enums.AuthProviders import AuthProvidersEnum

class Users(BaseModel):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    auth_provider: Mapped[AuthProvidersEnum] = mapped_column(
        Enum(AuthProvidersEnum, name="auth_provider_type", create_constraint=True),
        nullable=False
    )
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    phone_number: Mapped[str] = mapped_column(nullable=True, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)

    name: Mapped[str] = mapped_column(nullable=False)
    username: Mapped[str] = mapped_column(nullable=False)

    is_online: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(nullable=False, default=False)

    messages: Mapped[List["Messages"]] = relationship(back_populates="sender")
    forwarded_messages: Mapped[List["Messages"]] = relationship(back_populates="forwarded_from")

    conversations: Mapped[List["UserConversation"]] = relationship(back_populates="user")
    sent_pings: Mapped[List["Pings"]] = relationship(back_populates="sender")
    received_pings: Mapped[List["Pings"]] = relationship(back_populates="recipient")
    stories: Mapped[List["Stories"]] = relationship(back_populates="user")
    contacts: Mapped[List["Contacts"]] = relationship(back_populates="user")
    contacted_by: Mapped[List["Contacts"]] = relationship(back_populates="contact")
    tokens: Mapped[List["Tokens"]] = relationship(back_populates="user")

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )

from models.messages import Messages
from models.pings import Pings
from models.user_conversation import UserConversation
from models.stories import Stories
from models.tokens import Tokens
from models.contacts import Contacts
