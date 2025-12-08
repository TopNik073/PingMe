from fastapi import HTTPException, status
from src.presentation.schemas.responses import response_error


def raise_http_exception(
    status_code: int = status.HTTP_400_BAD_REQUEST,
    message: str = 'Operation failed',
    error: str | Exception = '',
) -> None:
    """
    Raise HTTP exception with standardized format

    Args:
        status_code: HTTP status code
        message: Human-readable message
        error: Error details or exception
    """
    error_str = str(error) if error else message

    raise HTTPException(status_code=status_code, detail=response_error(error=error_str, message=message))


def raise_validation_error(message: str, error: Exception) -> None:
    raise_http_exception(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, message=message, error=error)


def raise_not_found_error(message: str, error: str = '') -> None:
    raise_http_exception(status_code=status.HTTP_404_NOT_FOUND, message=message, error=error)


def raise_unauthorized_error(message: str = 'Unauthorized') -> None:
    raise_http_exception(status_code=status.HTTP_401_UNAUTHORIZED, message=message)
