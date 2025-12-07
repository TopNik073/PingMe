from pydantic import BaseModel, EmailStr
from src.presentation.schemas.users import UserResponseSchema
from src.presentation.schemas.tokens import JWTTokens, TokenVerifySchema


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthVerifyRequestShema(BaseModel):
    email: EmailStr
    password: str
    token: str


class AuthResponseVerifySchema(BaseModel):
    """Schema for authentication response"""

    user: UserResponseSchema
    tokens: JWTTokens


class AuthResponseSchema(BaseModel):
    email: EmailStr


class TokenVerifyResponseSchema(BaseModel):
    """Schema for token verify response"""

    user: UserResponseSchema
    token: TokenVerifySchema


class TokenRequestSchema(BaseModel):
    token: str
