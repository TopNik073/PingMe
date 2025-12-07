from io import BytesIO
from uuid import UUID, uuid4
from fastapi import UploadFile

from src.infrastructure.database.repositories.media_repository import MediaRepository
from src.infrastructure.database.repositories.conversation_repo import ConversationRepository
from src.infrastructure.database.models.media import Media
from src.infrastructure.yandex.s3.manager import S3Manager
from src.core.logging import get_logger

logger = get_logger(__name__)

# Constants
MAX_EXTENSION_LENGTH = 10
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {
    # Images
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    # Videos
    "video/mp4",
    "video/webm",
    "video/quicktime",  # .mov
    # Audio
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    # Documents
    "application/pdf",
    "text/plain",
}


class MediaService:
    def __init__(
        self,
        media_repository: MediaRepository,
        conversation_repository: ConversationRepository,
        s3_manager: S3Manager,
    ):
        self._media_repo = media_repository
        self._conversation_repo = conversation_repository
        self._s3_manager = s3_manager

    async def get_media_by_id(
        self, media_id: UUID, user_id: UUID
    ) -> Media:
        """Get media by ID with access control check"""
        try:
            media = await self._media_repo.get_media_by_id(media_id, include_message=True)
            if not media:
                raise ValueError("Media not found")

            # Check if media belongs to a message
            if not media.message_id:
                raise ValueError("Media is not associated with a message")

            # Check if user is participant of the conversation
            conversation_id = media.message.conversation_id
            is_participant = await self._conversation_repo.is_participant(
                user_id, conversation_id
            )
            if not is_participant:
                raise ValueError("User is not a participant of this conversation")

            return media
        except Exception as e:
            logger.exception("Failed to get media by ID: %s", e)
            raise

    async def get_conversation_media(
        self, conversation_id: UUID, user_id: UUID
    ) -> list[Media]:
        """Get all media files for a conversation with access control check"""
        try:
            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(
                user_id, conversation_id
            )
            if not is_participant:
                raise ValueError("User is not a participant of this conversation")

            # Get media
            return await self._media_repo.get_conversation_media(
                conversation_id, include_message=True
            )
        except Exception as e:
            logger.exception("Failed to get conversation media: %s", e)
            raise

    async def upload_media(
        self,
        files: list[UploadFile],
        conversation_id: UUID,
        message_id: UUID,
        user_id: UUID,
    ) -> list[Media]:
        """
        Upload a media file to S3 and create a Media record.
        
        Note: Media must be created with message_id due to DB constraint.
        This method should be called when creating a message with media.
        """
        try:
            # Check if user is participant of the conversation
            is_participant = await self._conversation_repo.is_participant(
                user_id, conversation_id
            )
            if not is_participant:
                raise ValueError("User is not a participant of this conversation")

            media: list[Media] = []
            for file in files:
                # Read file content once for validation and upload
                file_content = await file.read()
                file_size = len(file_content)
                
                # Validate file size
                if file_size > MAX_FILE_SIZE:
                    raise ValueError(
                        f"File '{file.filename}' size ({file_size} bytes) exceeds maximum allowed size "
                        f"of {MAX_FILE_SIZE} bytes ({MAX_FILE_SIZE / (1024 * 1024):.1f}MB)"
                    )
                
                if file_size == 0:
                    raise ValueError(f"File '{file.filename}' is empty")
                
                # Validate content type
                content_type = file.content_type or "application/octet-stream"
                if content_type not in ALLOWED_CONTENT_TYPES:
                    raise ValueError(
                        f"File type '{content_type}' is not allowed. "
                        f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
                    )
                
                # Create BytesIO from content for S3 upload (more efficient than reading twice)
                file_stream = BytesIO(file_content)
                
                # Generate media ID for file path and DB record
                media_id = uuid4()

                # Form file path: {conversation_id}/{message_id}/{media_id}
                file_path = f"{conversation_id}/{message_id}/{media_id}"

                # Upload file to S3 using BytesIO stream
                upload_result = await self._s3_manager.upload_file(
                    file=file_stream,
                    file_path=file_path,
                    content_type=content_type,
                )

                if not upload_result:
                    raise ValueError("Failed to upload file to S3")

                # Create Media record with the same media_id used in file path
                media.append(
                        await self._media_repo.create_media(
                        content_type=upload_result["mime_type"],
                        url=upload_result["url"],
                        size=upload_result["size"],
                        message_id=message_id,
                        media_id=media_id,
                    )
                )
            
            return media
        except Exception as e:
            logger.exception("Failed to upload media: %s", e)
            raise

    async def attach_media_to_message(
        self,
        media_id: UUID,
        message_id: UUID,
        user_id: UUID,
    ) -> Media:
        """
        Attach existing media to a message.
        
        Note: This is for cases where media was uploaded separately.
        However, due to DB constraint, media must have message_id from creation.
        This method is kept for API compatibility but may not be used in practice.
        """
        try:
            # Get media
            media = await self._media_repo.get_media_by_id(media_id, include_message=True)
            if not media:
                raise ValueError("Media not found")
            
            # Check if media is already attached to a message
            if media.message_id:
                if media.message_id == message_id:
                    # Already attached to this message
                    return media
                raise ValueError("Media is already attached to another message")
            
            # Attach to message
            updated_media = await self._media_repo.attach_to_message(media_id, message_id)
            if not updated_media:
                raise ValueError("Failed to attach media to message")
            
            return updated_media
        except Exception as e:
            logger.exception("Failed to attach media to message: %s", e)
            raise

    async def get_message_media(
        self,
        message_id: UUID,
        user_id: UUID,
    ) -> list[Media]:
        """Get all media files for a specific message with access control"""
        try:
            # Get media for message
            media_list = await self._media_repo.get_message_media(message_id)
            
            if not media_list:
                return []
            
            # Verify user has access to the conversation
            # Get conversation_id from first media's message
            if media_list[0].message:
                conversation_id = media_list[0].message.conversation_id
                is_participant = await self._conversation_repo.is_participant(
                    user_id, conversation_id
                )
                if not is_participant:
                    raise ValueError("User is not a participant of this conversation")
            
            return media_list
        except Exception as e:
            logger.exception("Failed to get message media: %s", e)
            raise

    async def get_media_file(
        self, media_id: UUID, user_id: UUID
    ) -> tuple[bytes, str, str]:
        """
        Downloads file from S3 and returns content and metadata with access control check
        
        Returns:
            Tuple (file_content: bytes, content_type: str, filename: str)
        """
        try:
            # Get media with access control
            media = await self.get_media_by_id(media_id, user_id)

            # Check that media is associated with a message
            if not media.message_id:
                raise ValueError("Media is not associated with a message")

            # Form file path: {conversation_id}/{message_id}/{media_id}
            # Use media.id directly to ensure consistency with upload path
            conversation_id = media.message.conversation_id
            file_path = f"{conversation_id}/{media.message_id}/{media.id}"

            # Download file from S3
            result = await self._s3_manager.download_file(file_path)
            if not result:
                raise ValueError("Failed to download file from S3")

            file_content, content_type, _size = result

            # Form filename (can use from URL or generate)
            # Extract extension from content_type or use original name
            filename = f"{media_id}"
            if media.url:
                # Try to extract extension from URL
                url_parts = media.url.split('.')
                if len(url_parts) > 1:
                    ext = url_parts[-1].split('?')[0]  # Remove query parameters
                    if ext and len(ext) <= MAX_EXTENSION_LENGTH:  # Check if it looks like an extension
                        filename = f"{media_id}.{ext}"

            return (file_content, content_type, filename)
        except Exception as e:
            logger.exception("Failed to get media file: %s", e)
            raise

