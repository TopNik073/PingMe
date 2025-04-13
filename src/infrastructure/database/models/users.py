from typing import List

from alembic.operations.toimpl import create_constraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum, ForeignKey

import uuid
from datetime import datetime

from src.infrastructure.database.models.BaseModel import BaseModel, get_datetime_UTC
from src.infrastructure.database.enums.AuthProviders import AuthProvidersEnum
from src.infrastructure.database.enums.MailingMethods import MailingMethods


class Users(BaseModel):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False
    )

    auth_provider: Mapped[AuthProvidersEnum] = mapped_column(
        Enum(AuthProvidersEnum, name="auth_provider_type", create_constraint=True), nullable=False
    )
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    phone_number: Mapped[str] = mapped_column(nullable=True, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)

    name: Mapped[str] = mapped_column(nullable=False)
    username: Mapped[str] = mapped_column(nullable=True)

    is_online: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(nullable=False, default=False)

    mailing_method: Mapped[MailingMethods] = mapped_column(
        Enum(MailingMethods, name="mailing_method_type", create_constraint=True),
        nullable=False,
        default=MailingMethods.EMAIL,
    )

    messages: Mapped[List["Messages"]] = relationship(
        back_populates="sender", foreign_keys="Messages.sender_id"
    )
    forwarded_messages: Mapped[List["Messages"]] = relationship(
        back_populates="forwarded_from", foreign_keys="Messages.forwarded_from_id"
    )

    conversations: Mapped[List["UserConversation"]] = relationship(back_populates="user")
    sent_pings: Mapped[List["Pings"]] = relationship(
        back_populates="sender", foreign_keys="Pings.sender_id"
    )
    received_pings: Mapped[List["Pings"]] = relationship(
        back_populates="recipient", foreign_keys="Pings.recipient_id"
    )
    stories: Mapped[List["Stories"]] = relationship(back_populates="user")
    contacts: Mapped[List["Contacts"]] = relationship(
        back_populates="user", foreign_keys="Contacts.user_id"
    )
    contacted_by: Mapped[List["Contacts"]] = relationship(
        back_populates="contact", foreign_keys="Contacts.contact_id"
    )

    created_at: Mapped[datetime] = mapped_column(default=get_datetime_UTC)
    updated_at: Mapped[datetime] = mapped_column(
        default=get_datetime_UTC, onupdate=get_datetime_UTC
    )


from src.infrastructure.database.models.messages import Messages
from src.infrastructure.database.models.pings import Pings
from src.infrastructure.database.models.user_conversation import UserConversation
from src.infrastructure.database.models.stories import Stories
from src.infrastructure.database.models.contacts import Contacts
