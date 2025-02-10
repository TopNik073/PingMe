from typing import Generic, TypeVar
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class JWTToken(BaseModel):
    token: str
    expires_at: datetime


class JWTTokens(BaseModel):
    access: JWTToken
    refresh: JWTToken


class TokenVerifySchema(JWTToken):
    token_type: str


class RefreshRequestSchema(BaseModel):
    refresh_token: str
