from fastapi import APIRouter, status
from sqlalchemy.exc import IntegrityError

from src.presentation.api.dependencies import AUTH_SERVICE_DEP
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
    UserResetRequestSchema,
    UserResponseSchema,
)
from src.presentation.schemas.auth import (
    AuthResponseSchema,
    AuthVerifyRequestShema,
    AuthResponseVerifySchema,
    TokenRequestSchema,
    TokenVerifyResponseSchema,
)
from src.core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/register", response_model=ResponseModel[AuthResponseSchema])
async def register(
    user_data: UserRegisterRequestShema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[AuthResponseSchema] | None:
    try:
        await auth_service.start_registration(user_data)
        return response_success(
            data=AuthResponseSchema(email=user_data.email),
            message="Verification code sent to your email",
        )
    except Exception as e:
        logger.error("Failed to start registration: %s", e)
        raise_http_exception(message="Failed to start registration", error=e)


@router.post("/verify-registration", response_model=ResponseModel[AuthResponseVerifySchema])
async def verify_registration(
    credentials: AuthVerifyRequestShema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[AuthResponseVerifySchema] | None:
    try:
        user, tokens = await auth_service.complete_registration(
            str(credentials.email), credentials.token, credentials.password
        )
        return response_success(
            data=AuthResponseVerifySchema(
                user=UserResponseSchema.model_validate(user), tokens=tokens
            ),
            message="Registration completed successfully",
        )

    except IntegrityError:
        logger.warning("User already exists: %s", credentials.email)
        raise_http_exception(message="User already exists")

    except Exception as e:
        logger.error("Failed to complete registration: %s", e)
        raise_http_exception(message="Failed to complete registration", error=e)


@router.post("/login", response_model=ResponseModel[AuthResponseSchema])
async def login(
    credentials: UserLoginRequestShema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[AuthResponseSchema] | None:
    try:
        user = await auth_service.login(str(credentials.email), credentials.password)
        return response_success(
            data=AuthResponseSchema(email=user.email),
            message="Verification code sent to your email",
        )
    except Exception as e:
        logger.error("Failed to login: %s", e)
        raise_http_exception(message="Login failed", error=e)


@router.post("/verify-login", response_model=ResponseModel[AuthResponseVerifySchema])
async def verify_login(
    credentials: AuthVerifyRequestShema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[AuthResponseVerifySchema] | None:
    try:
        user, tokens = await auth_service.verify_login(
            str(credentials.email), credentials.token, credentials.password
        )
        return response_success(
            data=AuthResponseVerifySchema(
                user=UserResponseSchema.model_validate(user), tokens=tokens
            ),
            message="Login successful",
        )
    except Exception as e:
        logger.error("Failed to verify login: %s", e)
        raise_http_exception(message="Failed to verify login", error=e)


@router.post("/reset-password", response_model=ResponseModel[AuthResponseSchema])
async def reset_password(
    credentials: UserResetRequestSchema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[AuthResponseSchema] | None:
    try:
        user = await auth_service.reset_password(str(credentials.email))
        return response_success(
            data=AuthResponseSchema(email=user.email),
            message="Verification code sent to your email",
        )
    except Exception as e:
        logger.error("Failed to verify reset password: %s", e)
        raise_http_exception(message="Failed to reset password", error=e)


@router.post("/verify-reset-password", response_model=ResponseModel[AuthResponseVerifySchema])
async def verify_reset_password(
    credentials: AuthVerifyRequestShema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[AuthResponseVerifySchema] | None:
    try:
        user, tokens = await auth_service.verify_reset_password(
            str(credentials.email), credentials.token, credentials.password
        )
        return response_success(
            data=AuthResponseVerifySchema(
                user=UserResponseSchema.model_validate(user), tokens=tokens
            ),
            message="Password reset successfully",
        )
    except Exception as e:
        logger.error("Failed to verify reset password: %s", e)
        raise_http_exception(message="Failed to verify reset password", error=e)


@router.post("/refresh", response_model=ResponseModel[JWTTokens])
async def refresh_tokens(
    refresh_data: RefreshRequestSchema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[JWTTokens] | None:
    try:
        tokens = await auth_service.refresh_tokens(refresh_data.refresh_token)
        return response_success(
            data=tokens,
            message="Tokens refreshed successfully",
        )
    except Exception as e:
        logger.error("Failed to refresh tokens: %s", e)
        raise_http_exception(message="Failed to refresh tokens", error=e)


@router.post("/verify-token", response_model=ResponseModel[TokenVerifyResponseSchema])
async def verify_token(
    token: TokenRequestSchema, auth_service: AUTH_SERVICE_DEP
) -> ResponseModel[TokenVerifyResponseSchema] | None:
    try:
        user, expiration_time, token_type = await auth_service.verify_token(token.token)
        return response_success(
            data=TokenVerifyResponseSchema(
                user=UserResponseSchema.model_validate(user),
                token=TokenVerifySchema(
                    token=token.token, expires_at=expiration_time, token_type=token_type
                ),
            ),
            message="Token is valid",
        )
    except ValueError as e:
        logger.error("Failed to verify token: %s", e)
        raise_http_exception(status_code=status.HTTP_401_UNAUTHORIZED, message=str(e), error=e)
