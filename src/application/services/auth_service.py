from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID
import random
import string
from datetime import datetime, timedelta
from argon2 import PasswordHasher

from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.enums.MailingMethods import MailingMethods
from src.infrastructure.database.enums.AuthProviders import AuthProvidersEnum
from src.infrastructure.cache.redis.auth_cache import AuthCache
from src.infrastructure.email.smtp_service import SMTPService
from src.infrastructure.security.jwt import JWTHandler

from src.presentation.schemas.users import (
    UserRegisterDTO,
    UserRegisterRequestShema,
    UserLoginRequestShema,
)

from src.presentation.schemas.tokens import JWTTokens, JWTToken

if TYPE_CHECKING:
    from src.infrastructure.database.models.users import Users


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        email_service: SMTPService,
        auth_cache: AuthCache,
        jwt_handler: JWTHandler = JWTHandler(),
    ):
        self._repository = user_repository
        self._email_service = email_service
        self._auth_cache = auth_cache
        self._password_hasher = PasswordHasher()
        self._jwt = jwt_handler

    @staticmethod
    def generate_token() -> str:
        """Generate a random token"""
        token = ""
        for _ in range(6):
            token += random.choice(string.digits)
        return token

    async def get_user_by_email_from_cache(self, email: str) -> Optional["Users"]:
        cache_key = f"user:email:{email}"
        user = await self._auth_cache.get_auth(cache_key)
        return user

    async def get_user_by_email_from_db(self, email: str) -> Optional["Users"]:
        return await self._repository.get_by_filter(email=email)

    async def create_tokens(self, user_id: UUID) -> JWTTokens:
        """Create access and refresh tokens with expiration times"""
        access_token, access_expires = self._jwt.create_jwt_token(user_id, "access")
        refresh_token, refresh_expires = self._jwt.create_jwt_token(user_id, "refresh")

        return JWTTokens(
            access=JWTToken(token=access_token, expires_at=access_expires),
            refresh=JWTToken(token=refresh_token, expires_at=refresh_expires),
        )

    async def start_registration(self, user_data: UserRegisterRequestShema) -> str:
        """Start registration process"""
        if await self.get_user_by_email_from_db(user_data.email):
            raise ValueError("User already exists")

        if await self.get_user_by_email_from_cache(user_data.email):
            await self._auth_cache.delete(f"user:email:{user_data.email}")

        token = self.generate_token()
        user_data.password = self._password_hasher.hash(user_data.password)

        registration_data = {
            "user_data": user_data.model_dump(),
            "token": token,
            "token_type": "registration",
            "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat(),
        }

        await self._auth_cache.save_auth(user_data.email, registration_data)
        # Add SMS mailing for token
        await self._email_service.send_verification_email(user_data, token)

        return token

    async def complete_registration(
        self, email: str, token: str, password: str
    ) -> tuple["Users", JWTTokens]:
        """Complete registration process"""
        registration_data = await self._auth_cache.get_auth(email)

        if not registration_data:
            raise ValueError("Registration session not found or expired")

        if registration_data["token_type"] != "registration":
            raise ValueError("Invalid token type")

        if registration_data["token"] != token:
            raise ValueError("Invalid verification token")

        if datetime.fromisoformat(registration_data["expires_at"]) < datetime.now():
            await self._auth_cache.delete(f"user:email:{email}")
            raise ValueError("Verification token expired")

        user_data = registration_data["user_data"]

        if not self._password_hasher.verify(user_data["password"], password):
            raise ValueError("Passwords doesn't match")

        user_data["is_online"] = True
        user_data["is_verified"] = True
        user_data = UserRegisterDTO(**user_data)
        user = await self._repository.create(user_data)

        await self._auth_cache.delete_auth(email)
        tokens = await self.create_tokens(user.id)

        return user, tokens

    async def login(self, email: str, password: str) -> "Users":
        """Login user and start login session"""
        user: "Users" = await self.get_user_by_email_from_db(email)
        if not user:
            raise ValueError("Invalid email or password")

        if await self._auth_cache.get_auth(email):
            await self._auth_cache.delete_auth(email)

        try:
            self._password_hasher.verify(user.password, password)
        except:
            raise ValueError("Invalid email or password")

        token = self.generate_token()
        if user.mailing_method == MailingMethods.EMAIL:
            await self._email_service.send_verification_email(user, token)
        elif user.mailing_method == MailingMethods.SMS:
            # TODO: implement SMS mailing
            pass

        login_data = {
            "token": token,
            "token_type": "login",
            "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat(),
        }

        await self._auth_cache.save_auth(email, login_data)
        return user

    async def verify_login(
        self, email: str, token: str, password: str
    ) -> tuple["Users", JWTTokens]:
        """Complete login session"""
        user_data = await self._auth_cache.get_auth(email)
        if not user_data:
            raise ValueError("Login session not find or expired")

        if user_data["token_type"] != "login":
            raise ValueError("Invalid token type")

        if user_data["token"] != token:
            raise ValueError("Invalid token")

        user: "Users" = await self.get_user_by_email_from_db(email)
        if not user:
            raise ValueError("User not found")

        if not self._password_hasher.verify(user.password, password):
            raise ValueError("Passwords doesn't match")

        tokens = await self.create_tokens(user.id)
        await self._auth_cache.delete_auth(email)
        return user, tokens

    async def refresh_tokens(self, refresh_token: str) -> JWTTokens:
        """Refresh access and refresh tokens"""
        try:
            payload = self._jwt.decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")

            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid token")

            return await self.create_tokens(UUID(user_id))

        except Exception:
            raise ValueError("Invalid refresh token")

    async def verify_token(self, token: str) -> tuple["Users", datetime, str]:
        """Verify token and return user with token expiration"""
        try:
            payload = self._jwt.decode_token(token)
            if not payload or "sub" not in payload:
                raise ValueError("Invalid token")

            # Проверяем срок действия токена
            if self._jwt.is_token_expired(token):
                raise ValueError("Token expired")

            user_id = payload["sub"]
            user = await self._repository.get_by_id(UUID(user_id))
            if not user:
                raise ValueError("User not found")

            expiration = self._jwt.get_token_expiration(token)
            return user, expiration, payload["type"]

        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")
