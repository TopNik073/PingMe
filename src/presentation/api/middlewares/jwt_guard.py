from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.application.services.user_service import UserService
from src.infrastructure.security.jwt import JWTHandler
from src.presentation.api.dependencies.services import get_user_service
from src.presentation.utils.errors import raise_unauthorized_error, raise_http_exception

security = HTTPBearer()
jwt_handler = JWTHandler()


def verify_token(payload: dict) -> bool:
    if (token_type := payload.get("type")) is None:
        return False

    if token_type != "access":
        return False

    if jwt_handler.is_token_expired(payload):
        return False

    if payload.get("sub") is None:
        return False

    return True


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """
    Get current user from JWT token
    """
    try:
        token = credentials.credentials
        payload = jwt_handler.decode_token(token)
        if not verify_token(payload):
            return raise_unauthorized_error()

        user_id = payload.get("sub")
        if user_id is None:
            return raise_unauthorized_error()

        user = await user_service.find_user(id=user_id)
        if user is None:
            return raise_unauthorized_error()

        return user
    except:
        return raise_unauthorized_error()
