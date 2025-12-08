from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import TYPE_CHECKING

from src.infrastructure.database.enums.AuthProviders import AuthProvidersEnum
from src.infrastructure.database.enums.MailingMethods import MailingMethods

if TYPE_CHECKING:
    from src.infrastructure.database.models.users import Users


def set_user_avatar_url(user: 'Users') -> None:
    """Set avatar_url on user object if avatar is explicitly loaded.
    This function should be called after loading user with selectinload(Users.avatar)
    to avoid lazy loading issues.
    """
    # Only set avatar_url if avatar was explicitly loaded via selectinload
    # We can safely access avatar here because it's already loaded
    if hasattr(user, 'avatar') and user.avatar is not None:
        user.avatar_url = user.avatar.url
    else:
        user.avatar_url = None


class UserLoginRequestShema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserResetRequestSchema(BaseModel):
    email: EmailStr


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
    avatar_url: str | None = None

    @model_validator(mode='before')
    @classmethod
    def extract_avatar_url(cls, data):
        """Extract avatar URL from relationship before validation.
        Only processes dict input. For SQLAlchemy models, avatar_url must be set
        explicitly using set_user_avatar_url() after loading avatar via selectinload
        to avoid lazy loading. Never accesses avatar attribute directly.
        """
        if isinstance(data, dict):
            # If already a dict, check if it has avatar nested
            if data.get('avatar'):
                data['avatar_url'] = data['avatar'].url if hasattr(data['avatar'], 'url') else None
            return data

        # For SQLAlchemy model instances, ensure avatar_url is set
        # If avatar_url was explicitly set (via setattr), it will be used
        # If not set, default to None to avoid lazy loading
        if not hasattr(data, 'avatar_url'):
            data.avatar_url = None

        return data

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile"""

    name: str | None = Field(None, min_length=3, max_length=30)
    username: str | None = Field(None, min_length=3, max_length=30)
    phone_number: str | None = Field(None, description='Phone number in international format')
    fcm_token: str | None = Field(None, description='FCM token')


class UserBriefResponse(BaseModel):
    """Schema for brief user information (for search and profiles)"""

    id: UUID
    name: str
    username: str | None = None
    is_online: bool = False
    last_seen: datetime | None = None
    avatar_url: str | None = None

    @model_validator(mode='before')
    @classmethod
    def extract_avatar_url(cls, data):
        """Extract avatar URL from relationship before validation.
        Only processes dict input. For SQLAlchemy models, avatar_url must be set
        explicitly using set_user_avatar_url() after loading avatar via selectinload
        to avoid lazy loading. Never accesses avatar attribute directly.
        """
        if isinstance(data, dict):
            # If already a dict, check if it has avatar nested
            if data.get('avatar'):
                data['avatar_url'] = data['avatar'].url if hasattr(data['avatar'], 'url') else None
            return data

        # For SQLAlchemy model instances, ensure avatar_url is set
        # If avatar_url was explicitly set (via setattr), it will be used
        # If not set, default to None to avoid lazy loading
        if not hasattr(data, 'avatar_url'):
            data.avatar_url = None

        return data

    class Config:
        from_attributes = True
