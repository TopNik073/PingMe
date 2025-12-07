from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from uuid import UUID

from src.presentation.api.guards.jwt_guard import CURRENT_USER_DEP
from src.presentation.api.dependencies import MEDIA_SERVICE_DEP
from src.presentation.schemas.conversations import MediaResponse
from src.presentation.schemas.responses import ResponseModel, response_success
from src.presentation.utils.errors import (
    raise_http_exception,
    raise_not_found_error,
    raise_unauthorized_error,
)
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/upload", response_model=ResponseModel[list[MediaResponse]])
async def upload_media(
    current_user: CURRENT_USER_DEP,
    media_service: MEDIA_SERVICE_DEP,
    files: list[UploadFile] = File(...),  # noqa: B008
    conversation_id: UUID = Query(..., description="Conversation ID"),
    message_id: UUID = Query(..., description="Message ID to attach media to"),
) -> ResponseModel[list[MediaResponse]] | None:
    """
    Upload a media file to S3 and attach it to a message.
    
    Note: Media must be attached to a message due to DB constraints.
    The message should be created first, then media can be uploaded and attached.
    """
    if current_user is None or media_service is None:
        raise_http_exception(message="Service not available")
    try:
        media = await media_service.upload_media(
            files=files,
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=current_user.id,
        )
        media_response = [MediaResponse.model_validate(m) for m in media]
        return response_success(
            data=media_response,
            message="Media uploaded successfully",
        )
    except ValueError as e:
        error_msg = str(e)
        logger.warning("Failed to upload media: %s", error_msg)
        if "not a participant" in error_msg.lower():
            raise_unauthorized_error(message=error_msg)
        raise_http_exception(message=error_msg)
    except Exception as e:
        logger.error("Failed to upload media: %s", e)
        raise_http_exception(message="Failed to upload media", error=e)


@router.get("/{media_id}")
async def get_media_file(
    current_user: CURRENT_USER_DEP,
    media_service: MEDIA_SERVICE_DEP,
    media_id: UUID,
) -> StreamingResponse:
    """
    Get media file by ID. Downloads file from S3 and streams it to client.
    
    Args:
        media_service: dependency
        current_user: dependency
        media_id: ID of the media file
    """
    try:
        file_content, content_type, filename = await media_service.get_media_file(
            media_id=media_id,
            user_id=current_user.id,
        )
        
        file_stream = BytesIO(file_content)
        
        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            }
        )
    except ValueError as e:
        error_msg = str(e)
        logger.warning("Failed to get media file: %s", error_msg)
        if "not found" in error_msg.lower():
            raise_not_found_error(message=error_msg)
        raise_unauthorized_error(message=error_msg)
    except Exception as e:
        logger.error("Failed to get media file: %s", e)
        raise_http_exception(message="Failed to get media file", error=e)

