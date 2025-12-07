from io import BytesIO
from uuid import UUID, uuid4
from fastapi import UploadFile

from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.repositories.media_repository import MediaRepository
from src.infrastructure.database.models.users import Users
from src.infrastructure.database.models.media import Media
from src.infrastructure.yandex.s3.manager import S3Manager
from src.presentation.schemas.users import UserUpdate
from src.core.logging import get_logger

logger = get_logger(__name__)

# Constants for avatar validation
AVATAR_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
AVATAR_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
}


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        media_repository: MediaRepository | None = None,
        s3_manager: S3Manager | None = None,
    ):
        self._user_repo: UserRepository = user_repository
        self._media_repo: MediaRepository | None = media_repository
        self._s3_manager: S3Manager | None = s3_manager

    async def find_user(self, **filters):
        try:
            user = await self._user_repo.get_by_filter(
                **filters, include_relations=["received_pings", "avatar"]
            )
            return user[0] if len(user) == 1 else None
        except Exception as e:
            logger.exception("Cannot find user by filters: %s", filters, exc_info=e)
            return None

    async def update_user(self, user_id: UUID, update_data: UserUpdate) -> Users:
        """Update user profile"""
        try:
            user = await self._user_repo.update(id=user_id, data=update_data)
            if not user:
                raise ValueError("User not found")
            
            # Load avatar explicitly and set avatar_url to avoid lazy loading
            user = await self._user_repo.get_by_id(user_id, include_relations=["avatar"])
            if user and user.avatar:
                user.avatar_url = user.avatar.url
            else:
                user.avatar_url = None
            
            return user
        except Exception as e:
            logger.exception("Failed to update user: %s", e)
            raise

    async def get_user_by_id(self, user_id: UUID) -> Users:
        """Get user by ID with avatar relationship loaded"""
        try:
            user = await self._user_repo.get_by_id(user_id, include_relations=["avatar"])
            if not user:
                raise ValueError("User not found")
            
            # Set avatar_url explicitly to avoid lazy loading
            if user.avatar:
                user.avatar_url = user.avatar.url
            else:
                user.avatar_url = None
            
            return user
        except ValueError:
            raise
        except Exception as e:
            logger.exception("Failed to get user by ID: %s", e)
            raise

    async def search_users(
        self,
        search_query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Users]:
        """Search users by name, username, or phone number"""
        try:
            # Validate search query
            if not search_query or len(search_query.strip()) < 1:
                raise ValueError("Search query cannot be empty")
            
            # Search users
            return await self._user_repo.search_users(
                search_query=search_query.strip(),
                skip=skip,
                limit=limit,
            )
        except ValueError:
            raise
        except Exception as e:
            logger.exception("Failed to search users: %s", e)
            raise

    async def upload_avatar(self, user_id: UUID, file: UploadFile) -> Media:
        """
        Upload user avatar to S3 and create a Media record.
        
        Validates that the file is an image (jpeg, png, gif, webp) and max 10MB.
        Deletes old avatar if exists.
        """
        if not self._media_repo or not self._s3_manager:
            raise ValueError("Media repository and S3 manager are required for avatar upload")
        
        try:
            # Read file content once for validation and upload
            file_content = await file.read()
            file_size = len(file_content)
            
            # Validate file size
            if file_size > AVATAR_MAX_FILE_SIZE:
                raise ValueError(
                    f"File size ({file_size} bytes) exceeds maximum allowed size "
                    f"of {AVATAR_MAX_FILE_SIZE} bytes ({AVATAR_MAX_FILE_SIZE / (1024 * 1024):.1f}MB)"
                )
            
            if file_size == 0:
                raise ValueError("File is empty")
            
            # Validate content type
            content_type = file.content_type or "application/octet-stream"
            if content_type not in AVATAR_ALLOWED_CONTENT_TYPES:
                raise ValueError(
                    f"File type '{content_type}' is not allowed for avatars. "
                    f"Allowed types: {', '.join(sorted(AVATAR_ALLOWED_CONTENT_TYPES))}"
                )
            
            # Delete old avatar if exists
            old_avatar = await self._media_repo.get_user_avatar(user_id)
            if old_avatar:
                # Construct file path from known format: avatars/{user_id}/{media_id}
                # This is more reliable than parsing URL
                old_file_path = f"avatars/{user_id}/{old_avatar.id}"
                
                # Delete from S3 first
                try:
                    await self._s3_manager.delete_file(old_file_path)
                    logger.info("Deleted old avatar file from S3: %s", old_file_path)
                except Exception as e:
                    logger.warning("Failed to delete old avatar file from S3: %s", e)
                    # Continue even if S3 deletion fails
                
                # Delete from database
                deleted = await self._media_repo.delete_user_avatar(user_id)
                if deleted:
                    logger.info("Deleted old avatar from database for user: %s", user_id)
                else:
                    logger.warning("Failed to delete old avatar from database for user: %s", user_id)
            
            # Generate media ID for file path and DB record
            media_id = uuid4()
            
            # Form file path: avatars/{user_id}/{media_id}
            file_path = f"avatars/{user_id}/{media_id}"
            
            # Create BytesIO from content for S3 upload
            file_stream = BytesIO(file_content)
            
            # Upload file to S3 with public read access for avatars
            upload_result = await self._s3_manager.upload_file(
                file=file_stream,
                file_path=file_path,
                content_type=content_type,
                public_read=True,  # Avatars should be publicly accessible
            )
            
            if not upload_result:
                raise ValueError("Failed to upload file to S3")
            
            # Create Media record with the same media_id used in file path
            return await self._media_repo.create_media(
                content_type=upload_result["mime_type"],
                url=upload_result["url"],
                size=upload_result["size"],
                user_id=user_id,
                media_id=media_id,
            )
        except Exception as e:
            logger.exception("Failed to upload avatar: %s", e)
            raise

    async def delete_avatar(self, user_id: UUID) -> bool:
        """Delete user avatar from S3 and database"""
        if not self._media_repo or not self._s3_manager:
            raise ValueError("Media repository and S3 manager are required for avatar deletion")
        
        try:
            avatar = await self._media_repo.get_user_avatar(user_id)
            if not avatar:
                return False
            
            # Delete from S3
            if avatar.url:
                url_parts = avatar.url.split("/")
                MIN_URL_PARTS = 3
                if len(url_parts) >= MIN_URL_PARTS:
                    file_path = "/".join(url_parts[MIN_URL_PARTS:])
                    await self._s3_manager.delete_file(file_path)
            
            # Delete from database
            return await self._media_repo.delete_user_avatar(user_id)
        except Exception as e:
            logger.exception("Failed to delete avatar: %s", e)
            raise
