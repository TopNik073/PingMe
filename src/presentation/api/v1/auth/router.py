from typing import TYPE_CHECKING
from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError

from src.presentation.api.dependencies.services import get_auth_service
from src.presentation.schemas.responses import ResponseModel, response_success
from src.presentation.schemas.tokens import (
    JWTTokens,
    RefreshRequestSchema,
    TokenVerifySchema,
)

from src.presentation.utils.errors import raise_http_exception
from src.presentation.schemas.users import (
    UserRegisterRequestShema,
    UserLoginRequestShema,
)
from src.presentation.schemas.auth import (
    AuthResponseSchema,
    AuthVerifyRequestShema,
    AuthResponseVerifySchema,
    TokenRequestSchema,
    TokenVerifyResponseSchema,
)
from src.core.logging import get_logger

if TYPE_CHECKING:
    from src.application.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=ResponseModel[AuthResponseSchema])
async def register(
    user_data: UserRegisterRequestShema, auth_service: "AuthService" = Depends(get_auth_service)
) -> ResponseModel[AuthResponseSchema]:
    try:
        await auth_service.start_registration(user_data)
        return response_success(
            data=AuthResponseSchema(email=user_data.email),
            message="Verification code sent to your email",
        )
    except Exception as e:
        logger.error(f"Failed to start registration: {e}")
        raise_http_exception(message="Failed to start registration", error=e)


@router.post("/verify-registration", response_model=ResponseModel[AuthResponseVerifySchema])
async def verify_registration(
    credentials: AuthVerifyRequestShema, auth_service: "AuthService" = Depends(get_auth_service)
) -> ResponseModel[AuthResponseVerifySchema]:
    try:
        user, tokens = await auth_service.complete_registration(
            credentials.email, credentials.token, credentials.password
        )
        return response_success(
            data=AuthResponseVerifySchema(user=user, tokens=tokens),
            message="Registration completed successfully",
        )

    except IntegrityError:
        logger.warning(f"User already exists: {credentials.email}")
        raise_http_exception(message="User already exists")

    except Exception as e:
        logger.error(f"Failed to complete registration: {e}")
        raise_http_exception(message="Failed to complete registration", error=e)


@router.post("/login", response_model=ResponseModel[AuthResponseSchema])
async def login(
    credentials: UserLoginRequestShema, auth_service: "AuthService" = Depends(get_auth_service)
) -> ResponseModel[AuthResponseSchema]:
    try:
        user = await auth_service.login(credentials.email, credentials.password)
        return response_success(
            data=AuthResponseSchema(email=user.email),
            message="Verification code sent to your email",
        )
    except Exception as e:
        logger.error(f"Failed to login: {e}")
        raise_http_exception(message="Login failed", error=e)


@router.post("/verify-login", response_model=ResponseModel[AuthResponseVerifySchema])
async def verify_login(
    credentials: AuthVerifyRequestShema, auth_service: "AuthService" = Depends(get_auth_service)
) -> ResponseModel[AuthResponseVerifySchema]:
    try:
        user, tokens = await auth_service.verify_login(
            credentials.email, credentials.token, credentials.password
        )
        return response_success(
            data=AuthResponseVerifySchema(user=user, tokens=tokens),
            message="Login successful",
        )
    except Exception as e:
        logger.error(f"Failed to verify login: {e}")
        raise_http_exception(message="Failed to verify login", error=e)


@router.post("/refresh", response_model=ResponseModel[JWTTokens])
async def refresh_tokens(
    refresh_data: RefreshRequestSchema, auth_service: "AuthService" = Depends(get_auth_service)
) -> ResponseModel[JWTTokens]:
    try:
        tokens = await auth_service.refresh_tokens(refresh_data.refresh_token)
        return response_success(
            data=tokens,
            message="Tokens refreshed successfully",
        )
    except Exception as e:
        logger.error(f"Failed to refresh tokens: {e}")
        raise_http_exception(message="Failed to refresh tokens", error=e)


@router.post("/verify-token", response_model=ResponseModel[TokenVerifyResponseSchema])
async def verify_token(
    token: TokenRequestSchema, auth_service: "AuthService" = Depends(get_auth_service)
) -> ResponseModel[TokenVerifyResponseSchema]:
    try:
        user, expiration_time, token_type = await auth_service.verify_token(token.token)
        return response_success(
            data=TokenVerifyResponseSchema(
                user=user,
                token=TokenVerifySchema(
                    token=token.token, expires_at=expiration_time, token_type=token_type
                ),
            ),
            message="Token is valid",
        )
    except ValueError as e:
        logger.error(f"Failed to verify token: {e}")
        raise_http_exception(status_code=status.HTTP_401_UNAUTHORIZED, message=str(e), error=e)
