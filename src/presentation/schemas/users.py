from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

from src.infrastructure.database.enums.AuthProviders import AuthProvidersEnum
from src.infrastructure.database.enums.MailingMethods import MailingMethods


class UserLoginRequestShema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserRegisterRequestShema(UserLoginRequestShema):
    """Schema for user creation"""

    name: str = Field(..., min_length=3, max_length=30)


class UserRegisterDTO(UserRegisterRequestShema):
    is_online: bool
    is_verified: bool
    auth_provider: AuthProvidersEnum = AuthProvidersEnum.MANUAL


class UserResponseSchema(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    username: str | None = None
    phone_number: str | None = None
    is_online: bool = False
    is_verified: bool = False
    auth_provider: AuthProvidersEnum
    mailing_method: MailingMethods
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    pass
