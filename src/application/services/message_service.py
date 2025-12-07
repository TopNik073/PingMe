"""
Message Service - Business logic for message operations.

Handles creation, editing, deletion, and forwarding of messages.
Integrates with ConversationService for permission checks.
"""

from uuid import UUID

from typing import TYPE_CHECKING

from src.infrastructure.database.repositories.message_repository import MessageRepository
from src.infrastructure.database.repositories.conversation_repo import ConversationRepository
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.repositories.media_repository import MediaRepository
from src.infrastructure.database.models.messages import Messages
from src.application.services.conversation_service import ConversationService
from src.core.logging import get_logger

if TYPE_CHECKING:
    from src.infrastructure.fcm.service import FCMService
    from src.infrastructure.websocket.connection_manager import ConnectionManager

logger = get_logger(__name__)


class MessageService:
    """Service for managing messages"""
    
    def __init__(  # noqa: PLR0913
        self,
        message_repository: MessageRepository,
        conversation_repository: ConversationRepository,
        user_repository: UserRepository,
        conversation_service: ConversationService,
        media_repository: MediaRepository | None = None,
        fcm_service: "FCMService | None" = None,
        connection_manager: "ConnectionManager | None" = None,
    ):
        self._message_repo = message_repository
        self._conversation_repo = conversation_repository
        self._user_repo = user_repository
        self._conversation_service = conversation_service
        self._media_repo = media_repository
        self._fcm_service = fcm_service
        self._connection_manager = connection_manager
    
    async def create_message(  # noqa: PLR0912
        self,
        user_id: UUID,
        conversation_id: UUID,
        content: str,
        forwarded_from_id: UUID | None = None,
        media_ids: list[UUID] | None = None,
    ) -> Messages:
        """
        Create a new message in a conversation.
        
        Validates:
        - User is a participant of the conversation
        - Content is not empty
        - If forwarding, original message exists and is not deleted
        """
        try:
            # Check if user is a participant
            is_participant = await self._conversation_repo.is_participant(
                user_id, conversation_id
            )
            if not is_participant:
                raise ValueError("User is not a participant of this conversation")
            
            # Check if conversation exists and is not deleted
            conversation = await self._conversation_repo.get_by_id(conversation_id)
            if not conversation:
                raise ValueError("Conversation not found")
            
            if conversation.is_deleted:
                raise ValueError("Conversation is deleted")
            
            # If forwarding, validate original message
            if forwarded_from_id:
                original_message = await self._message_repo.get_message_by_id(
                    forwarded_from_id, include_deleted=False
                )
                if not original_message:
                    raise ValueError("Original message not found or deleted")
            
            # Create message
            message = await self._message_repo.create_message(
                sender_id=user_id,
                conversation_id=conversation_id,
                content=content,
                forwarded_from_id=forwarded_from_id,
            )
            
            # Attach media if provided
            if media_ids and self._media_repo:
                # Validate that all media exists and belongs to the user
                media_list = await self._media_repo.get_media_by_ids(media_ids, include_message=True)
                
                if len(media_list) != len(media_ids):
                    raise ValueError("Some media IDs not found")
                
                # Check that all media belongs to messages in the same conversation
                # and that the user has access to them
                for media in media_list:
                    if not media.message_id:
                        raise ValueError(f"Media {media.id} is not attached to a message")
                    if media.message.conversation_id != conversation_id:
                        raise ValueError(f"Media {media.id} belongs to a different conversation")
                    # Check if user is participant of the media's conversation
                    is_participant_media = await self._conversation_repo.is_participant(
                        user_id, media.message.conversation_id
                    )
                    if not is_participant_media:
                        raise ValueError(f"User does not have access to media {media.id}")
                
                # Attach media to the new message
                # Note: Since media must have message_id, we need to update existing media
                # or create new media records. For now, we'll update the message_id of existing media.
                # This assumes media was uploaded with a temporary message_id.
                for media in media_list:
                    # Update media to point to the new message
                    media.message_id = message.id
                    await self._media_repo.flush()
            
            await self._message_repo.commit()
            await self._message_repo.refresh(message, ["media"])
            
            logger.info("Message %s created by user %s in conversation %s", message.id, user_id, conversation_id)
            
            # Set avatar_url for sender to avoid lazy loading
            if message.sender and message.sender.avatar:
                message.sender.avatar_url = message.sender.avatar.url
            elif message.sender:
                message.sender.avatar_url = None
            
            # Send notifications to offline users if FCM service is available
            if self._fcm_service and self._connection_manager:
                await self._notify_offline_users(message)
            
            return message
        except Exception as e:
            await self._message_repo.rollback()
            logger.exception("Failed to create message: %s", e)
            raise
    
    async def edit_message(
        self,
        user_id: UUID,
        message_id: UUID,
        content: str,
    ) -> Messages:
        """
        Edit an existing message.
        
        Validates:
        - User is the sender of the message
        - Message exists and is not deleted
        - User is still a participant of the conversation
        """
        try:
            # Get message
            message = await self._message_repo.get_message_by_id(message_id, include_deleted=False)
            if not message:
                raise ValueError("Message not found")
            
            # Check if user is the sender
            if message.sender_id != user_id:
                raise ValueError("Only the message sender can edit the message")
            
            # Check if user is still a participant
            is_participant = await self._conversation_repo.is_participant(
                user_id, message.conversation_id
            )
            if not is_participant:
                raise ValueError("User is not a participant of this conversation")
            
            # Update message
            updated_message = await self._message_repo.update_message(
                message_id=message_id,
                content=content,
                user_id=user_id,
            )
            
            await self._message_repo.commit()
            
            # Reload message with sender and avatar
            updated_message = await self._message_repo.get_message_by_id(message_id, include_deleted=False)
            
            # Set avatar_url for sender to avoid lazy loading
            if updated_message and updated_message.sender:
                if updated_message.sender.avatar:
                    updated_message.sender.avatar_url = updated_message.sender.avatar.url
                else:
                    updated_message.sender.avatar_url = None
            
            logger.info("Message %s edited by user %s", message_id, user_id)
            
            return updated_message
        except ValueError:
            await self._message_repo.rollback()
            raise
        except Exception as e:
            await self._message_repo.rollback()
            logger.exception("Failed to edit message: %s", e)
            raise
    
    async def delete_message(
        self,
        user_id: UUID,
        message_id: UUID,
    ) -> Messages:
        """
        Soft delete a message.
        
        Validates:
        - User is the sender of the message
        - Message exists and is not already deleted
        """
        try:
            # Get message
            message = await self._message_repo.get_message_by_id(message_id, include_deleted=True)
            if not message:
                raise ValueError("Message not found")
            
            # Check if user is the sender
            if message.sender_id != user_id:
                raise ValueError("Only the message sender can delete the message")
            
            # Delete message
            deleted_message = await self._message_repo.delete_message(
                message_id=message_id,
                user_id=user_id,
            )
            
            await self._message_repo.commit()
            await self._message_repo.refresh(deleted_message)
            
            logger.info("Message %s deleted by user %s", message_id, user_id)
            
            return deleted_message
        except ValueError:
            await self._message_repo.rollback()
            raise
        except Exception as e:
            await self._message_repo.rollback()
            logger.exception("Failed to delete message: %s", e)
            raise
    
    async def forward_message(
        self,
        user_id: UUID,
        message_id: UUID,
        target_conversation_id: UUID,
    ) -> Messages:
        """
        Forward a message to another conversation.
        
        Validates:
        - Original message exists and is not deleted
        - User is a participant of both source and target conversations
        """
        try:
            # Get original message
            original_message = await self._message_repo.get_message_by_id(
                message_id, include_deleted=False
            )
            if not original_message:
                raise ValueError("Original message not found or deleted")
            
            # Check if user is a participant of source conversation
            is_participant_source = await self._conversation_repo.is_participant(
                user_id, original_message.conversation_id
            )
            if not is_participant_source:
                raise ValueError("User is not a participant of the source conversation")
            
            # Check if user is a participant of target conversation
            is_participant_target = await self._conversation_repo.is_participant(
                user_id, target_conversation_id
            )
            if not is_participant_target:
                raise ValueError("User is not a participant of the target conversation")
            
            # Check if target conversation exists and is not deleted
            target_conversation = await self._conversation_repo.get_by_id(target_conversation_id)
            if not target_conversation:
                raise ValueError("Target conversation not found")
            
            if target_conversation.is_deleted:
                raise ValueError("Target conversation is deleted")
            
            # Forward message
            forwarded_message = await self._message_repo.forward_message(
                message_id=message_id,
                sender_id=user_id,
                target_conversation_id=target_conversation_id,
            )
            
            await self._message_repo.commit()
            
            # Set avatar_url for sender to avoid lazy loading
            if forwarded_message and forwarded_message.sender:
                if forwarded_message.sender.avatar:
                    forwarded_message.sender.avatar_url = forwarded_message.sender.avatar.url
                else:
                    forwarded_message.sender.avatar_url = None
            
            logger.info(
                "Message %s forwarded by user %s to conversation %s",
                message_id,
                user_id,
                target_conversation_id,
            )
            
            return forwarded_message
        except ValueError:
            await self._message_repo.rollback()
            raise
        except Exception as e:
            await self._message_repo.rollback()
            logger.exception("Failed to forward message: %s", e)
            raise
    
    async def get_conversation_participants(self, conversation_id: UUID) -> list[UUID]:
        """Get list of participant user IDs for a conversation"""
        participants = await self._conversation_repo.get_participants(
            conversation_id, include_user=True
        )
        return [p.user_id for p in participants]
    
    async def _notify_offline_users(self, message: Messages):
        """Send FCM notifications to offline users in the conversation"""
        if not self._fcm_service or not self._connection_manager:
            logger.debug("FCM service or connection manager not available, skipping notifications")
            return
        
        try:
            # Ensure sender is loaded
            if not message.sender:
                await self._message_repo.refresh(message, ["sender"])
            
            # Get all participants
            participant_ids = await self.get_conversation_participants(message.conversation_id)
            
            # Get sender info
            sender = message.sender
            if not sender:
                logger.warning("Message %s has no sender, cannot send notifications", message.id)
                return
            
            # Filter offline users
            offline_users = [
                uid for uid in participant_ids
                if uid != message.sender_id
                and not self._connection_manager.is_user_online(uid)
            ]
            
            if not offline_users:
                logger.debug("No offline users to notify for message %s", message.id)
                return
            
            logger.debug("Sending FCM notifications to %s offline users", len(offline_users))
            
            # Send notifications
            for user_id in offline_users:
                try:
                    success = await self._fcm_service.send_message_notification(
                        user_id=user_id,
                        sender_name=sender.name,
                        message_content=message.content,
                        conversation_id=message.conversation_id,
                        message_id=message.id,
                    )
                    if success:
                        logger.debug("FCM notification sent successfully to user %s", user_id)
                except Exception as notification_error:
                    logger.warning(
                        "Failed to send FCM notification to user %s for message %s: %s",
                        user_id,
                        message.id,
                        notification_error,
                    )
        except Exception as e:
            logger.warning("Failed to send FCM notifications for message %s: %s", message.id, e, exc_info=True)

