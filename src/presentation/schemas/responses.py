from typing import Generic, TypeVar, Any
from pydantic import BaseModel

DataT = TypeVar("DataT")


class ResponseModel(BaseModel, Generic[DataT]):
    """Base response model"""

    success: bool
    message: str | None = None
    data: DataT | None = None
    error: str | None = None


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = False
    message: str | None = None
    error: str
    data: None = None


class SuccessResponse(BaseModel, Generic[DataT]):
    """Success response model"""

    success: bool = True
    message: str | None = None
    data: DataT
    error: None = None


def response_success(
    data: Any,
    message: str | None = None,
) -> dict:
    """Create success response"""
    return {"success": True, "message": message, "data": data, "error": None}


def response_error(
    error: str,
    message: str | None = None,
) -> dict:
    """Create error response"""
    return {"success": False, "message": message, "data": None, "error": error}
