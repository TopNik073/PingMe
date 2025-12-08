from fastapi import APIRouter
from uuid import UUID

from src.presentation.api.guards.jwt_guard import CURRENT_USER_DEP
from src.presentation.schemas.messages import MessageResponse
from src.presentation.schemas.messages import (
    MessageCreateRequest,
    MessageEditRequest,
    MessageForwardRequest,
)
from src.presentation.schemas.responses import ResponseModel, response_success
from src.presentation.utils.errors import (
    raise_http_exception,
    raise_not_found_error,
)
from src.core.logging import get_logger

from src.presentation.api.dependencies import MESSAGE_SERVICE_DEP

logger = get_logger(__name__)

router = APIRouter(prefix='/messages', tags=['Messages'])


@router.post('/', response_model=ResponseModel[MessageResponse])
async def create_message(
    current_user: CURRENT_USER_DEP,
    message_service: MESSAGE_SERVICE_DEP,
    message_data: MessageCreateRequest,
) -> ResponseModel[MessageResponse] | None:
    """Create a new message"""
    if current_user is None or message_service is None:
        raise_http_exception(message='Service not available')
    try:
        message = await message_service.create_message(
            user_id=current_user.id,
            conversation_id=message_data.conversation_id,
            content=message_data.content,
            forwarded_from_id=message_data.forwarded_from_id,
            media_ids=message_data.media_ids,
        )

        message_response = MessageResponse.model_validate(message)
        return response_success(
            data=message_response,
            message='Message created successfully',
        )
    except ValueError as e:
        logger.warning('Failed to create message: %s', e)
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error('Failed to create message: %s', e)
        raise_http_exception(message='Failed to create message', error=e)


@router.patch('/{message_id}', response_model=ResponseModel[MessageResponse])
async def edit_message(
    current_user: CURRENT_USER_DEP,
    message_service: MESSAGE_SERVICE_DEP,
    message_id: UUID,
    message_data: MessageEditRequest,
) -> ResponseModel[MessageResponse] | None:
    """Edit an existing message"""
    if current_user is None or message_service is None:
        raise_http_exception(message='Service not available')
    try:
        message = await message_service.edit_message(
            user_id=current_user.id,
            message_id=message_id,
            content=message_data.content,
        )

        message_response = MessageResponse.model_validate(message)
        return response_success(
            data=message_response,
            message='Message edited successfully',
        )
    except ValueError as e:
        logger.warning('Failed to edit message: %s', e)
        if 'not found' in str(e).lower():
            raise_not_found_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error('Failed to edit message: %s', e)
        raise_http_exception(message='Failed to edit message', error=e)


@router.delete('/{message_id}', response_model=ResponseModel[MessageResponse])
async def delete_message(
    current_user: CURRENT_USER_DEP,
    message_service: MESSAGE_SERVICE_DEP,
    message_id: UUID,
) -> ResponseModel[MessageResponse] | None:
    """Delete a message"""
    if current_user is None or message_service is None:
        raise_http_exception(message='Service not available')
    try:
        message = await message_service.delete_message(
            user_id=current_user.id,
            message_id=message_id,
        )

        message_response = MessageResponse.model_validate(message)
        return response_success(
            data=message_response,
            message='Message deleted successfully',
        )
    except ValueError as e:
        logger.warning('Failed to delete message: %s', e)
        if 'not found' in str(e).lower():
            raise_not_found_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error('Failed to delete message: %s', e)
        raise_http_exception(message='Failed to delete message', error=e)


@router.post('/{message_id}/forward', response_model=ResponseModel[MessageResponse])
async def forward_message(
    current_user: CURRENT_USER_DEP,
    message_service: MESSAGE_SERVICE_DEP,
    message_id: UUID,
    forward_data: MessageForwardRequest,
) -> ResponseModel[MessageResponse] | None:
    """Forward a message to another conversation"""
    if current_user is None or message_service is None:
        raise_http_exception(message='Service not available')
    try:
        message = await message_service.forward_message(
            user_id=current_user.id,
            message_id=message_id,
            target_conversation_id=forward_data.conversation_id,
        )

        message_response = MessageResponse.model_validate(message)
        return response_success(
            data=message_response,
            message='Message forwarded successfully',
        )
    except ValueError as e:
        logger.warning('Failed to forward message: %s', e)
        if 'not found' in str(e).lower():
            raise_not_found_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error('Failed to forward message: %s', e)
        raise_http_exception(message='Failed to forward message', error=e)
