from fastapi import APIRouter, Query, Path, UploadFile, File
from uuid import UUID

from src.presentation.api.guards.jwt_guard import CURRENT_USER_DEP
from src.presentation.api.dependencies import CONVERSATION_SERVICE_DEP, MEDIA_SERVICE_DEP
from src.presentation.schemas.conversations import (
    ConversationCreateRequest,
    ConversationUpdateRequest,
    ConversationJoinRequest,
    ConversationResponse,
    ConversationBriefResponse,
    ParticipantResponse,
    ParticipantRoleUpdateRequest,
    MediaResponse,
)
from src.presentation.schemas.messages import MessageResponse
from src.presentation.schemas.responses import ResponseModel, response_success
from src.presentation.utils.errors import (
    raise_http_exception,
    raise_not_found_error,
    raise_unauthorized_error,
)
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversation", tags=["Conversations"])


@router.get("/", response_model=ResponseModel[list[ConversationResponse]])
async def get_conversations(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
) -> ResponseModel[list[ConversationResponse]] | None:
    """Get all conversations for the current user"""
    try:
        conversations = await conversation_service.get_user_conversations(
            user_id=current_user.id
        )
        conversations_data = [
            ConversationResponse.model_validate(conv) for conv in conversations
        ]
        return response_success(
            data=conversations_data,
            message="Conversations retrieved successfully",
        )
    except Exception as e:
        logger.error("Failed to get conversations: %s", e)
        raise_http_exception(message="Failed to get conversations", error=e)


@router.post("/", response_model=ResponseModel[ConversationResponse])
async def create_conversation(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_data: ConversationCreateRequest,
) -> ResponseModel[ConversationResponse] | None:
    """Create a new conversation"""
    try:
        conversation = await conversation_service.create_conversation(
            user_id=current_user.id,
            name=conversation_data.name,
            participant_ids=conversation_data.participant_ids,
        )
        conversation_response = ConversationResponse.model_validate(conversation)
        return response_success(
            data=conversation_response,
            message="Conversation created successfully",
        )
    except ValueError as e:
        logger.warning("Failed to create conversation: %s", e)
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to create conversation: %s", e)
        raise_http_exception(message="Failed to create conversation", error=e)


@router.patch("/", response_model=ResponseModel[ConversationResponse])
async def update_conversation(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    update_data: ConversationUpdateRequest,
    conversation_id: UUID = Query(..., description="Conversation ID"),
) -> ResponseModel[ConversationResponse] | None:
    """Update a conversation (only OWNER/ADMIN can update)"""
    try:
        conversation = await conversation_service.update_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
            update_data=update_data,
        )
        conversation_response = ConversationResponse.model_validate(conversation)
        return response_success(
            data=conversation_response,
            message="Conversation updated successfully",
        )
    except ValueError as e:
        logger.warning("Failed to update conversation: %s", e)
        if "not a participant" in str(e).lower():
            raise_unauthorized_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to update conversation: %s", e)
        raise_http_exception(message="Failed to update conversation", error=e)


@router.post("/join", response_model=ResponseModel[ConversationResponse])
async def join_to_conversation(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    join_data: ConversationJoinRequest,
) -> ResponseModel[ConversationResponse] | None:
    """Join a conversation"""
    try:
        await conversation_service.join_conversation(
            user_id=current_user.id,
            conversation_id=join_data.conversation_id,
        )
        # Get the conversation to return it
        conversation = await conversation_service.get_conversation_by_id(
            join_data.conversation_id
        )
        
        if not conversation:
            raise_not_found_error(message="Conversation not found")
        
        conversation_response = ConversationResponse.model_validate(conversation)
        return response_success(
            data=conversation_response,
            message="Successfully joined conversation",
        )
    except ValueError as e:
        logger.warning("Failed to join conversation: %s", e)
        if "already a participant" in str(e).lower():
            raise_http_exception(message=str(e))
        raise_not_found_error(message=str(e))
    except Exception as e:
        logger.error("Failed to join conversation: %s", e)
        raise_http_exception(message="Failed to join conversation", error=e)


@router.get("/messages", response_model=ResponseModel[list[MessageResponse]])
async def get_messages(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID = Query(..., description="Conversation ID"),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of messages to return"),
) -> ResponseModel[list[MessageResponse]] | None:
    """Get messages from a conversation"""
    try:
        messages = await conversation_service.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
        messages_data = [MessageResponse.model_validate(msg) for msg in messages]
        return response_success(
            data=messages_data,
            message="Messages retrieved successfully",
        )
    except ValueError as e:
        logger.warning("Failed to get messages: %s", e)
        raise_unauthorized_error(message=str(e))
    except Exception as e:
        logger.error("Failed to get messages: %s", e)
        raise_http_exception(message="Failed to get messages", error=e)


@router.get("/{conversation_id}/messages/search", response_model=ResponseModel[list[MessageResponse]])
async def search_messages(  # noqa: PLR0913
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID,
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of messages to return"),
) -> ResponseModel[list[MessageResponse]] | None:
    """Search messages in a conversation"""
    try:
        messages = await conversation_service.search_messages(
            conversation_id=conversation_id,
            user_id=current_user.id,
            search_query=query,
            skip=skip,
            limit=limit,
        )
        messages_data = [MessageResponse.model_validate(msg) for msg in messages]
        return response_success(
            data=messages_data,
            message="Messages found successfully",
        )
    except ValueError as e:
        logger.warning("Failed to search messages: %s", e)
        if "not a participant" in str(e).lower():
            raise_unauthorized_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to search messages: %s", e)
        raise_http_exception(message="Failed to search messages", error=e)


@router.get("/participants", response_model=ResponseModel[list[ParticipantResponse]])
async def get_participants(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID = Query(..., description="Conversation ID"),
) -> ResponseModel[list[ParticipantResponse]] | None:
    """Get participants of a conversation"""
    try:
        participants = await conversation_service.get_conversation_participants(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        participants_data = [
            ParticipantResponse.model_validate(participant) for participant in participants
        ]
        return response_success(
            data=participants_data,
            message="Participants retrieved successfully",
        )
    except ValueError as e:
        logger.warning("Failed to get participants: %s", e)
        raise_unauthorized_error(message=str(e))
    except Exception as e:
        logger.error("Failed to get participants: %s", e)
        raise_http_exception(message="Failed to get participants", error=e)


@router.get("/media", response_model=ResponseModel[list[MediaResponse]])
async def get_media(
    current_user: CURRENT_USER_DEP,
    media_service: MEDIA_SERVICE_DEP,
    conversation_id: UUID = Query(..., description="Conversation ID"),
) -> ResponseModel[list[MediaResponse]] | None:
    """Get media from a conversation"""
    try:
        media_list = await media_service.get_conversation_media(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        
        media_data = [MediaResponse.model_validate(media) for media in media_list]
        
        return response_success(
            data=media_data,
            message="Media retrieved successfully",
        )
    except ValueError as e:
        logger.warning("Failed to get media: %s", e)
        raise_unauthorized_error(message=str(e))
    except Exception as e:
        logger.error("Failed to get media: %s", e)
        raise_http_exception(message="Failed to get media", error=e)


@router.delete("/{conversation_id}", response_model=ResponseModel[ConversationResponse])
async def delete_conversation(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID,
) -> ResponseModel[ConversationResponse] | None:
    """Delete a conversation (only OWNER can delete)"""
    try:
        conversation = await conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        conversation_response = ConversationResponse.model_validate(conversation)
        return response_success(
            data=conversation_response,
            message="Conversation deleted successfully",
        )
    except ValueError as e:
        logger.warning("Failed to delete conversation: %s", e)
        if "not a participant" in str(e).lower() or "only owner" in str(e).lower():
            raise_unauthorized_error(message=str(e))
        if "not found" in str(e).lower():
            raise_not_found_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to delete conversation: %s", e)
        raise_http_exception(message="Failed to delete conversation", error=e)


@router.delete("/{conversation_id}/participants/{user_id}", response_model=ResponseModel[dict])
async def remove_participant(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID,
    user_id: UUID,
) -> ResponseModel[dict] | None:
    """Remove a participant from a conversation"""
    try:
        await conversation_service.remove_participant(
            conversation_id=conversation_id,
            user_id=user_id,
            remover_id=current_user.id,
        )
        return response_success(
            data={"conversation_id": conversation_id, "removed_user_id": user_id},
            message="Participant removed successfully",
        )
    except ValueError as e:
        logger.warning("Failed to remove participant: %s", e)
        if "not a participant" in str(e).lower() or "only owner" in str(e).lower() or "only admin" in str(e).lower():
            raise_unauthorized_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to remove participant: %s", e)
        raise_http_exception(message="Failed to remove participant", error=e)


@router.patch("/{conversation_id}/participants/{user_id}/role", response_model=ResponseModel[ParticipantResponse])
async def update_participant_role(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID,
    user_id: UUID,
    role_data: ParticipantRoleUpdateRequest,
) -> ResponseModel[ParticipantResponse] | None:
    """Update participant role in a conversation (only OWNER/ADMIN can update)"""
    try:
        updated_participant = await conversation_service.update_participant_role(
            conversation_id=conversation_id,
            target_user_id=user_id,
            new_role=role_data.role,
            updater_id=current_user.id,
        )
        participant_response = ParticipantResponse.model_validate(updated_participant)
        return response_success(
            data=participant_response,
            message="Participant role updated successfully",
        )
    except ValueError as e:
        logger.warning("Failed to update participant role: %s", e)
        if "not a participant" in str(e).lower() or "only owner" in str(e).lower() or "only admin" in str(e).lower():
            raise_unauthorized_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to update participant role: %s", e)
        raise_http_exception(message="Failed to update participant role", error=e)


@router.post("/{conversation_id}/leave", response_model=ResponseModel[dict])
async def leave_conversation(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID,
) -> ResponseModel[dict] | None:
    """Leave a conversation"""
    try:
        await conversation_service.leave_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        return response_success(
            data={"conversation_id": conversation_id},
            message="Successfully left conversation",
        )
    except ValueError as e:
        logger.warning("Failed to leave conversation: %s", e)
        if "not a participant" in str(e).lower():
            raise_unauthorized_error(message=str(e))
        if "owner cannot leave" in str(e).lower():
            raise_http_exception(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to leave conversation: %s", e)
        raise_http_exception(message="Failed to leave conversation", error=e)


@router.get("/{conversation_id}/brief", response_model=ResponseModel[ConversationBriefResponse])
async def get_conversation_brief(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID = Path(..., description="Conversation ID"),  # noqa: B008
) -> ResponseModel[ConversationBriefResponse] | None:
    """Get brief information about a conversation (for search and profiles)"""
    if current_user is None or conversation_service is None:
        raise_http_exception(message="Service not available")
    try:
        brief_data = await conversation_service.get_conversation_brief(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        conversation_brief = ConversationBriefResponse.model_validate(brief_data)
        return response_success(
            data=conversation_brief,
            message="Conversation information retrieved successfully",
        )
    except ValueError as e:
        logger.warning("Failed to get conversation brief: %s", e)
        if "not found" in str(e).lower():
            raise_not_found_error(message=str(e))
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to get conversation brief: %s", e)
        raise_http_exception(message="Failed to get conversation information", error=e)


@router.get("/search", response_model=ResponseModel[list[ConversationBriefResponse]])
async def search_conversations(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    query: str = Query(..., min_length=1, description="Search query (conversation name)"),
    skip: int = Query(0, ge=0, description="Number of conversations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of conversations to return"),
) -> ResponseModel[list[ConversationBriefResponse]] | None:
    """Search conversations by name"""
    if conversation_service is None:
        raise_http_exception(message="Service not available")
    try:
        conversations = await conversation_service.search_conversations(
            search_query=query,
            skip=skip,
            limit=limit,
        )

        conversations_brief = [
            ConversationBriefResponse.model_validate(conv) for conv in conversations
        ]
        
        return response_success(
            data=conversations_brief,
            message="Conversations found successfully",
        )
    except ValueError as e:
        logger.warning("Failed to search conversations: %s", e)
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to search conversations: %s", e)
        raise_http_exception(message="Failed to search conversations", error=e)


@router.post("/{conversation_id}/avatar", response_model=ResponseModel[MediaResponse])
async def upload_conversation_avatar(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID = Path(..., description="Conversation ID"),  # noqa: B008
    file: UploadFile = File(..., description="Avatar image file"),  # noqa: B008
) -> ResponseModel[MediaResponse] | None:
    """Upload conversation avatar (only for POLYLOGUE, requires OWNER/ADMIN role)"""
    if conversation_service is None:
        raise_http_exception(message="Service not available")
    try:
        avatar = await conversation_service.upload_conversation_avatar(
            conversation_id=conversation_id,
            user_id=current_user.id,
            file=file,
        )
        avatar_response = MediaResponse.model_validate(avatar)
        return response_success(
            data=avatar_response,
            message="Conversation avatar uploaded successfully",
        )
    except ValueError as e:
        logger.warning("Failed to upload conversation avatar: %s", e)
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to upload conversation avatar: %s", e)
        raise_http_exception(message="Failed to upload conversation avatar", error=e)


@router.delete("/{conversation_id}/avatar", response_model=ResponseModel[dict])
async def delete_conversation_avatar(
    current_user: CURRENT_USER_DEP,
    conversation_service: CONVERSATION_SERVICE_DEP,
    conversation_id: UUID = Path(..., description="Conversation ID"),  # noqa: B008
) -> ResponseModel[dict] | None:
    """Delete conversation avatar (requires OWNER/ADMIN role)"""
    if conversation_service is None:
        raise_http_exception(message="Service not available")
    try:
        deleted = await conversation_service.delete_conversation_avatar(
            conversation_id=conversation_id,
            user_id=current_user.id,
        )
        if not deleted:
            raise_not_found_error(message="Avatar not found")
        return response_success(
            data={"deleted": True},
            message="Conversation avatar deleted successfully",
        )
    except ValueError as e:
        logger.warning("Failed to delete conversation avatar: %s", e)
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to delete conversation avatar: %s", e)
        raise_http_exception(message="Failed to delete conversation avatar", error=e)
