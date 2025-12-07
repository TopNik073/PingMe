from datetime import datetime, timedelta, UTC
from typing import Any, Literal
from jose import jwt
from uuid import UUID

from src.core.config import settings


class JWTHandler:
    """Handler for JWT tokens"""

    @staticmethod
    def create_jwt_token(
        user_id: UUID, token_type: Literal["access", "refresh"]
    ) -> tuple[str, datetime]:
        """Create jwt token"""
        current_date = datetime.now()
        current_date: datetime = current_date.replace(tzinfo=None)
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        else:
            expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        expires_at: datetime = current_date + expires_delta

        jwt_data = {
            "sub": str(user_id),
            "type": token_type,
            "exp": int(expires_at.timestamp()),
        }

        token = jwt.encode(
            jwt_data, settings.JWT_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM
        )
        return token, expires_at

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        """Decode JWT token"""
        return jwt.decode(
            token, settings.JWT_SECRET_KEY.get_secret_value(), algorithms=[settings.JWT_ALGORITHM]
        )

    @staticmethod
    def is_token_expired(token: str | dict[str, Any]) -> bool:
        """Check if token is expired"""
        try:
            payload = JWTHandler.decode_token(token) if isinstance(token, str) else token
            exp = payload.get("exp")
            if not exp:
                return True

            return exp < int(datetime.now(UTC).timestamp())

        except Exception:
            return True

    @staticmethod
    def get_token_expiration(token: str) -> datetime:
        """Get token expiration time"""
        payload = JWTHandler.decode_token(token)
        exp = payload.get("exp")
        if not exp:
            raise ValueError("Token has no expiration time")

        return datetime.fromtimestamp(exp, tz=UTC)
