from uuid import UUID

from fastapi import APIRouter, Path, Query, UploadFile, File

from src.presentation.api.guards.jwt_guard import CURRENT_USER_DEP
from src.presentation.api.dependencies import USER_SERVICE_DEP
from src.presentation.schemas.users import UserResponseSchema, UserUpdate, UserBriefResponse
from src.presentation.schemas.conversations import MediaResponse
from src.presentation.schemas.responses import ResponseModel, response_success
from src.presentation.utils.errors import raise_http_exception, raise_not_found_error
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ResponseModel[UserResponseSchema])
async def get_me(
    current_user: CURRENT_USER_DEP,
) -> ResponseModel[UserResponseSchema] | None:
    """Get current user profile"""
    try:
        # Set avatar_url explicitly to avoid lazy loading
        # current_user already has avatar loaded via find_user in jwt_guard
        if current_user.avatar:
            current_user.avatar_url = current_user.avatar.url
        else:
            current_user.avatar_url = None
        
        user_data = UserResponseSchema.model_validate(current_user)
        return response_success(
            data=user_data,
            message="User profile retrieved successfully",
        )
    except Exception as e:
        logger.error("Failed to get user profile: %s", e)
        raise_http_exception(message="Failed to get user profile", error=e)


@router.patch("/me", response_model=ResponseModel[UserResponseSchema])
async def update_me(
    current_user: CURRENT_USER_DEP,
    user_service: USER_SERVICE_DEP,
    update_data: UserUpdate,
) -> ResponseModel[UserResponseSchema] | None:
    """Update current user profile"""
    try:
        updated_user = await user_service.update_user(
            user_id=current_user.id,
            update_data=update_data,
        )
        user_data = UserResponseSchema.model_validate(updated_user)
        return response_success(
            data=user_data,
            message="User profile updated successfully",
        )
    except ValueError as e:
        logger.warning("Failed to update user profile: %s", e)
        raise_not_found_error(message=str(e))
    except Exception as e:
        logger.error("Failed to update user profile: %s", e)
        raise_http_exception(message="Failed to update user profile", error=e)


@router.get("/search", response_model=ResponseModel[list[UserBriefResponse]])
async def search_users(
    current_user: CURRENT_USER_DEP,
    user_service: USER_SERVICE_DEP,
    query: str = Query(..., min_length=1, description="Search query (name, username, or phone number)"),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of users to return"),
) -> ResponseModel[list[UserBriefResponse]] | None:
    """Search users by name, username, or phone number"""
    try:
        users = await user_service.search_users(
            search_query=query,
            skip=skip,
            limit=limit,
        )
        # Set avatar_url explicitly for each user to avoid lazy loading
        for user in users:
            if user.avatar:
                user.avatar_url = user.avatar.url
            else:
                user.avatar_url = None
        
        users_brief = [UserBriefResponse.model_validate(user) for user in users]
        return response_success(
            data=users_brief,
            message="Users found successfully",
        )
    except ValueError as e:
        logger.warning("Failed to search users: %s", e)
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to search users: %s", e)
        raise_http_exception(message="Failed to search users", error=e)


@router.post("/me/avatar", response_model=ResponseModel[MediaResponse])
async def upload_avatar(
    current_user: CURRENT_USER_DEP,
    user_service: USER_SERVICE_DEP,
    file: UploadFile = File(..., description="Avatar image file"),  # noqa: B008
) -> ResponseModel[MediaResponse] | None:
    """Upload user avatar"""
    if user_service is None:
        raise_http_exception(message="Service not available")
    try:
        avatar = await user_service.upload_avatar(
            user_id=current_user.id,
            file=file,
        )
        avatar_response = MediaResponse.model_validate(avatar)
        return response_success(
            data=avatar_response,
            message="Avatar uploaded successfully",
        )
    except ValueError as e:
        logger.warning("Failed to upload avatar: %s", e)
        raise_http_exception(message=str(e))
    except Exception as e:
        logger.error("Failed to upload avatar: %s", e)
        raise_http_exception(message="Failed to upload avatar", error=e)


@router.delete("/me/avatar", response_model=ResponseModel[dict])
async def delete_avatar(
    current_user: CURRENT_USER_DEP,
    user_service: USER_SERVICE_DEP,
) -> ResponseModel[dict] | None:
    """Delete user avatar"""
    if user_service is None:
        raise_http_exception(message="Service not available")
    try:
        deleted = await user_service.delete_avatar(user_id=current_user.id)
        if not deleted:
            raise_not_found_error(message="Avatar not found")
        return response_success(
            data={"deleted": True},
            message="Avatar deleted successfully",
        )
    except ValueError as e:
        logger.warning("Failed to delete avatar: %s", e)
        raise_not_found_error(message=str(e))
    except Exception as e:
        logger.error("Failed to delete avatar: %s", e)
        raise_http_exception(message="Failed to delete avatar", error=e)


@router.get("/{user_id}", response_model=ResponseModel[UserBriefResponse])
async def get_user_brief(
    current_user: CURRENT_USER_DEP,
    user_service: USER_SERVICE_DEP,
    user_id: UUID = Path(..., description="User ID"),  # noqa: B008
) -> ResponseModel[UserBriefResponse] | None:
    """Get brief information about a user (for search and profiles)"""
    if user_service is None:
        raise_http_exception(message="Service not available")
    try:
        user = await user_service.get_user_by_id(user_id=user_id)
        # Set avatar_url explicitly to avoid lazy loading
        if user.avatar:
            user.avatar_url = user.avatar.url
        else:
            user.avatar_url = None
        
        user_brief = UserBriefResponse.model_validate(user)
        return response_success(
            data=user_brief,
            message="User information retrieved successfully",
        )
    except ValueError as e:
        logger.warning("Failed to get user brief: %s", e)
        raise_not_found_error(message=str(e))
    except Exception as e:
        logger.error("Failed to get user brief: %s", e)
        raise_http_exception(message="Failed to get user information", error=e)
