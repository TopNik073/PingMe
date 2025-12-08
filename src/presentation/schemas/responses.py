from typing import TypeVar
from pydantic import BaseModel

DataT = TypeVar('DataT')


class ResponseModel[DataT](BaseModel):
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


class SuccessResponse[DataT](BaseModel):
    """Success response model"""

    success: bool = True
    message: str | None = None
    data: DataT
    error: None = None


def response_success[DataT](
    data: DataT,
    message: str | None = None,
) -> ResponseModel[DataT]:
    """Create success response"""
    return ResponseModel(
        success=True,
        message=message,
        data=data,
        error=None,
    ).model_dump()


def response_error(
    error: str,
    message: str | None = None,
) -> ResponseModel[None]:
    """Create error response"""
    return ResponseModel(
        success=False,
        message=message,
        error=error,
        data=None,
    ).model_dump()
