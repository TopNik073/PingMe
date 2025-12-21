from io import BytesIO
from uuid import UUID, uuid4
from fastapi import UploadFile

from src.infrastructure.database.repositories.conversation_repo import ConversationRepository
from src.infrastructure.database.repositories.message_repository import MessageRepository
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.repositories.media_repository import MediaRepository
from src.infrastructure.database.models.conversations import Conversations
from src.infrastructure.database.models.user_conversation import UserConversation
from src.infrastructure.database.models.media import Media
from src.infrastructure.database.enums.Roles import Roles
from src.infrastructure.database.enums.ConversationType import ConversationType
from src.infrastructure.yandex.s3.manager import S3Manager
from src.presentation.schemas.conversations import (
    ConversationUpdateRequest,
)
from src.presentation.schemas.messages import MessageReadInfo
from src.core.logging import get_logger
from src.infrastructure.database.models.BaseModel import get_datetime_UTC

logger = get_logger(__name__)

# Constants
DIALOG_PARTICIPANT_COUNT = 2
AVATAR_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
AVATAR_ALLOWED_CONTENT_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/heic',
    'image/heif',
}


class ConversationService:
    async def _update_conversation_type(self, conversation_id: UUID) -> None:
        """
        Update conversation type based on participant count.
        Called after adding or removing participants.
        """
        conversation = await self._conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return

        participants = await self._conversation_repo.get_participants(conversation_id)
        participant_count = len(participants)

        if participant_count == DIALOG_PARTICIPANT_COUNT:
            new_type = ConversationType.DIALOG
        else:
            new_type = ConversationType.POLYLOGUE

        # Only update if type changed
        if conversation.conversation_type != new_type:
            conversation.conversation_type = new_type
            await self._conversation_repo.flush()
            logger.info(
                'Conversation %s type updated to %s (participants: %d)',
                conversation_id,
                new_type.value,
                participant_count,
            )

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        user_repository: UserRepository,
        message_repository: MessageRepository,
        media_repository: MediaRepository | None = None,
        s3_manager: S3Manager | None = None,
    ):
        self._conversation_repo = conversation_repository
        self._user_repo = user_repository
        self._message_repo = message_repository
        self._media_repo = media_repository
        self._s3_manager = s3_manager

    async def create_conversation(
        self,
        user_id: UUID,
        name: str,
        participant_ids: list[UUID] | None = None,
    ) -> Conversations:
        """
        Create a new conversation and add creator as OWNER.
        Conversation type is automatically determined based on participant count:
        - 2 participants = DIALOG (creator: OWNER, second participant: ADMIN)
        - 3+ participants = POLYLOGUE (creator: OWNER, others: MEMBER)
        """
        try:
            # Create conversation with temporary type (will be updated after adding participants)
            conversation = Conversations(
                name=name,
                conversation_type=ConversationType.POLYLOGUE,  # Temporary, will be updated
            )
            self._conversation_repo.add_object(conversation)
            await self._conversation_repo.flush()
            await self._conversation_repo.refresh(conversation)

            # Add creator as OWNER
            await self._conversation_repo.add_participant(
                user_id=user_id,
                conversation_id=conversation.id,
                role=Roles.OWNER,
            )

            # Add additional participants if provided
            if participant_ids:
                for participant_id in participant_ids:
                    # Skip if trying to add creator again
                    if participant_id == user_id:
                        continue

                    # Verify user exists
                    user = await self._user_repo.get_by_id(participant_id)
                    if not user:
                        logger.warning('User %s not found, skipping', participant_id)
                        continue

                    await self._conversation_repo.add_participant(
                        user_id=participant_id,
                        conversation_id=conversation.id,
                        role=Roles.MEMBER,
                    )

            # Auto-determine conversation type based on participant count
            participants = await self._conversation_repo.get_participants(conversation.id)
            participant_count = len(participants)
            
            if participant_count == DIALOG_PARTICIPANT_COUNT:
                conversation.conversation_type = ConversationType.DIALOG
                # For dialogs: second participant should be ADMIN
                # Find the participant who is not the creator
                for participant in participants:
                    if participant.user_id != user_id:
                        # Update second participant's role to ADMIN
                        await self._conversation_repo.update_participant_role(
                            participant.user_id, conversation.id, Roles.ADMIN
                        )
                        logger.info(
                            'Dialog created: participant %s assigned ADMIN role in conversation %s',
                            participant.user_id,
                            conversation.id,
                        )
                        break
            else:
                conversation.conversation_type = ConversationType.POLYLOGUE

            await self._conversation_repo.commit()
            await self._conversation_repo.refresh(conversation)

            # Load avatar explicitly and set avatar_url to avoid lazy loading
            conversation = await self._conversation_repo.get_by_id(conversation.id, include_relations=['avatar'])
            if conversation and conversation.avatar:
                conversation.avatar_url = conversation.avatar.url
            else:
                conversation.avatar_url = None

            return conversation
        except Exception as e:
            await self._conversation_repo.rollback()
            logger.exception('Failed to create conversation: %s', e)
            raise

    async def update_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
        update_data: ConversationUpdateRequest,
    ) -> Conversations:
        """Update conversation (only OWNER/ADMIN can update)"""
        try:
            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Check user role
            user_role = await self._conversation_repo.get_user_role(user_id, conversation_id)
            if user_role not in [Roles.OWNER, Roles.ADMIN]:
                raise ValueError('Only OWNER or ADMIN can update conversation')

            # Get conversation
            conversation = await self._conversation_repo.get_by_id(conversation_id)
            if not conversation:
                raise ValueError('Conversation not found')

            # Update fields
            update_dict = update_data.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                setattr(conversation, key, value)

            await self._conversation_repo.commit()
            await self._conversation_repo.refresh(conversation)

            # Load avatar explicitly and set avatar_url to avoid lazy loading
            conversation = await self._conversation_repo.get_by_id(conversation_id, include_relations=['avatar'])
            if conversation and conversation.avatar:
                conversation.avatar_url = conversation.avatar.url
            else:
                conversation.avatar_url = None

            return conversation
        except Exception as e:
            await self._conversation_repo.rollback()
            logger.exception('Failed to update conversation: %s', e)
            raise

    async def get_conversation_by_id(self, conversation_id: UUID) -> Conversations | None:
        """Get conversation by ID with avatar relationship loaded"""
        conversation = await self._conversation_repo.get_by_id(conversation_id, include_relations=['avatar'])
        if conversation:
            # Set avatar_url explicitly to avoid lazy loading
            if conversation.avatar:
                conversation.avatar_url = conversation.avatar.url
            else:
                conversation.avatar_url = None
        return conversation

    async def join_conversation(self, user_id: UUID, conversation_id: UUID) -> UserConversation:
        """Join a conversation as a member"""
        try:
            # Check if already a participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if is_participant:
                raise ValueError('User is already a participant')

            # Check if conversation exists
            conversation = await self._conversation_repo.get_by_id(conversation_id)
            if not conversation:
                raise ValueError('Conversation not found')

            if conversation.is_deleted:
                raise ValueError('Conversation is deleted')

            # Add user as member
            result = await self._conversation_repo.add_participant(
                user_id=user_id,
                conversation_id=conversation_id,
                role=Roles.MEMBER,
            )

            # Update conversation type based on new participant count
            await self._update_conversation_type(conversation_id)

            return result
        except Exception as e:
            logger.exception('Failed to join conversation: %s', e)
            raise

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list:
        """
        Get messages from a conversation (only participants can view).
        Returns messages enriched with read_by information.
        """
        try:
            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Get messages with smart pagination
            messages = await self._message_repo.get_conversation_messages(
                conversation_id=conversation_id,
                user_id=user_id,
                skip=skip,
                limit=limit,
            )

            if not messages:
                return []

            # Set avatar_url for each sender to avoid lazy loading
            for message in messages:
                if message.sender:
                    if message.sender.avatar:
                        message.sender.avatar_url = message.sender.avatar.url
                    else:
                        message.sender.avatar_url = None

            # Get readers for all messages in one query
            message_ids = [msg.id for msg in messages]
            readers_map = await self._message_repo.get_message_readers(
                message_ids=message_ids,
                conversation_id=conversation_id,
            )

            # Enrich messages with read_by information
            enriched_messages = []
            for msg in messages:
                # Create a dict-like object that can be validated by MessageResponse
                # We'll add read_by as an attribute
                msg_dict = {
                    'id': msg.id,
                    'content': msg.content,
                    'sender_id': msg.sender_id,
                    'conversation_id': msg.conversation_id,
                    'forwarded_from_id': msg.forwarded_from_id,
                    'sender': msg.sender,
                    'media': msg.media,
                    'created_at': msg.created_at,
                    'updated_at': msg.updated_at,
                    'is_edited': msg.is_edited,
                    'is_deleted': msg.is_deleted,
                    'deleted_at': msg.deleted_at,
                    'read_by': [
                        MessageReadInfo(
                            user_id=reader['user_id'],
                            name=reader['name'],
                            username=reader['username'],
                            read_at=reader['read_at'],
                        )
                        for reader in readers_map.get(msg.id, [])
                    ],
                }
                enriched_messages.append(msg_dict)

            return enriched_messages
        except Exception as e:
            logger.exception('Failed to get conversation messages: %s', e)
            raise

    async def get_conversation_participants(self, conversation_id: UUID, user_id: UUID) -> list[UserConversation]:
        """Get participants of a conversation (only participants can view)"""
        try:
            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Get participants with users and avatars loaded
            participants = await self._conversation_repo.get_participants(conversation_id, include_user=True)

            # Set avatar_url explicitly for each user to avoid lazy loading
            for participant in participants:
                if participant.user:
                    if participant.user.avatar:
                        participant.user.avatar_url = participant.user.avatar.url
                    else:
                        participant.user.avatar_url = None

            return participants
        except Exception as e:
            logger.exception('Failed to get conversation participants: %s', e)
            raise

    async def get_user_conversations(self, user_id: UUID) -> list[Conversations]:
        """Get all conversations for a user with avatar relationship loaded"""
        try:
            conversations = await self._conversation_repo.get_user_conversations(
                user_id, include_relations=['users', 'messages', 'avatar']
            )
            # Set avatar_url explicitly for each conversation to avoid lazy loading
            for conversation in conversations:
                if conversation.avatar:
                    conversation.avatar_url = conversation.avatar.url
                else:
                    conversation.avatar_url = None
            return conversations
        except Exception as e:
            logger.exception('Failed to get user conversations: %s', e)
            raise

    async def delete_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Conversations:
        """Delete a conversation (only OWNER can delete)"""
        try:
            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Get conversation to check type
            conversation = await self._conversation_repo.get_by_id(conversation_id)
            if not conversation:
                raise ValueError('Conversation not found')

            # Check user role
            user_role = await self._conversation_repo.get_user_role(user_id, conversation_id)
            
            # For dialogs: OWNER or ADMIN can delete
            # For polylogues: only OWNER can delete
            if conversation.conversation_type == ConversationType.POLYLOGUE:
                if user_role != Roles.OWNER:
                    raise ValueError('Only OWNER can delete conversation')

            if conversation.is_deleted:
                raise ValueError('Conversation is already deleted')

            # Soft delete: set is_deleted=True and deleted_at=now()
            conversation.is_deleted = True
            conversation.deleted_at = get_datetime_UTC()

            await self._conversation_repo.commit()
            await self._conversation_repo.refresh(conversation)

            # Load avatar explicitly and set avatar_url to avoid lazy loading
            conversation = await self._conversation_repo.get_by_id(conversation_id, include_relations=['avatar'])
            if conversation and conversation.avatar:
                conversation.avatar_url = conversation.avatar.url
            else:
                conversation.avatar_url = None

            logger.info('Conversation %s deleted by user %s', conversation_id, user_id)
            return conversation
        except ValueError:
            await self._conversation_repo.rollback()
            raise
        except Exception as e:
            await self._conversation_repo.rollback()
            logger.exception('Failed to delete conversation: %s', e)
            raise

    async def remove_participant(
        self,
        conversation_id: UUID,
        user_id: UUID,
        remover_id: UUID,
    ) -> bool:
        """Remove a participant from a conversation"""
        try:
            # Check if remover is participant
            is_remover_participant = await self._conversation_repo.is_participant(remover_id, conversation_id)
            if not is_remover_participant:
                raise ValueError('Remover is not a participant of this conversation')

            # Check if target user is participant
            is_target_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_target_participant:
                raise ValueError('Target user is not a participant of this conversation')

            # Check permissions: OWNER/ADMIN can remove anyone, user can remove themselves
            if remover_id != user_id:
                remover_role = await self._conversation_repo.get_user_role(remover_id, conversation_id)
                if remover_role not in [Roles.OWNER, Roles.ADMIN]:
                    raise ValueError('Only OWNER or ADMIN can remove other participants')

            # Remove participant
            removed = await self._conversation_repo.remove_participant(user_id, conversation_id)
            if not removed:
                raise ValueError('Failed to remove participant')

            logger.info(
                'Participant %s removed from conversation %s by %s',
                user_id,
                conversation_id,
                remover_id,
            )

            # Update conversation type based on new participant count
            await self._update_conversation_type(conversation_id)

            return True
        except ValueError:
            raise
        except Exception as e:
            logger.exception('Failed to remove participant: %s', e)
            raise

    async def update_participant_role(
        self,
        conversation_id: UUID,
        target_user_id: UUID,
        new_role: Roles,
        updater_id: UUID,
    ) -> UserConversation:
        """Update participant role in a conversation (only OWNER/ADMIN can update)"""
        try:
            # Check if updater is participant
            is_updater_participant = await self._conversation_repo.is_participant(updater_id, conversation_id)
            if not is_updater_participant:
                raise ValueError('Updater is not a participant of this conversation')

            # Check updater role - only OWNER/ADMIN can update roles
            updater_role = await self._conversation_repo.get_user_role(updater_id, conversation_id)
            if updater_role not in [Roles.OWNER, Roles.ADMIN]:
                raise ValueError('Only OWNER or ADMIN can update participant roles')

            # Check if target user is participant
            is_target_participant = await self._conversation_repo.is_participant(target_user_id, conversation_id)
            if not is_target_participant:
                raise ValueError('Target user is not a participant of this conversation')

            # Prevent changing OWNER role (only one OWNER should exist)
            target_current_role = await self._conversation_repo.get_user_role(target_user_id, conversation_id)
            if target_current_role == Roles.OWNER and new_role != Roles.OWNER:
                raise ValueError('Cannot change OWNER role')

            # Update role
            updated_participant = await self._conversation_repo.update_participant_role(
                target_user_id, conversation_id, new_role
            )
            if not updated_participant:
                raise ValueError('Failed to update participant role')

            logger.info(
                'Participant %s role updated to %s in conversation %s by %s',
                target_user_id,
                new_role,
                conversation_id,
                updater_id,
            )
            return updated_participant
        except ValueError:
            raise
        except Exception as e:
            logger.exception('Failed to update participant role: %s', e)
            raise

    async def leave_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Leave a conversation (user removes themselves)"""
        try:
            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Check if conversation exists
            conversation = await self._conversation_repo.get_by_id(conversation_id)
            if not conversation:
                raise ValueError('Conversation not found')

            if conversation.is_deleted:
                raise ValueError('Conversation is deleted')

            # Get user role
            user_role = await self._conversation_repo.get_user_role(user_id, conversation_id)

            # OWNER cannot leave conversation (must delete it or transfer ownership)
            if user_role == Roles.OWNER:
                raise ValueError('OWNER cannot leave conversation. Delete it or transfer ownership first.')

            # Remove participant
            removed = await self._conversation_repo.remove_participant(user_id, conversation_id)
            if not removed:
                raise ValueError('Failed to leave conversation')

            logger.info('User %s left conversation %s', user_id, conversation_id)
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.exception('Failed to leave conversation: %s', e)
            raise

    async def get_conversation_brief(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Get brief information about a conversation"""
        try:
            # Get conversation with avatar loaded
            conversation = await self._conversation_repo.get_by_id(conversation_id, include_relations=['avatar'])
            if not conversation:
                raise ValueError('Conversation not found')

            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)

            result = {
                'id': conversation.id,
                'name': conversation.name,
                'conversation_type': conversation.conversation_type,
            }

            # Set avatar_url explicitly to avoid lazy loading
            if conversation.avatar:
                result['avatar_url'] = conversation.avatar.url
            else:
                result['avatar_url'] = None

            # Add participant info only if user is participant
            if is_participant:
                # Get participant count
                participants = await self._conversation_repo.get_participants(conversation_id, include_user=False)
                result['participant_count'] = len(participants)

            return result
        except ValueError:
            raise
        except Exception as e:
            logger.exception('Failed to get conversation brief: %s', e)
            raise

    async def search_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        search_query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list:
        """Search messages in a conversation (only participants can search)"""
        try:
            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Validate search query
            if not search_query or len(search_query.strip()) < 1:
                raise ValueError('Search query cannot be empty')

            # Search messages
            messages = await self._message_repo.search_messages(
                conversation_id=conversation_id,
                search_query=search_query.strip(),
                skip=skip,
                limit=limit,
            )

            # Set avatar_url for each sender to avoid lazy loading
            for message in messages:
                if message.sender:
                    if message.sender.avatar:
                        message.sender.avatar_url = message.sender.avatar.url
                    else:
                        message.sender.avatar_url = None

            return messages
        except ValueError:
            raise
        except Exception as e:
            logger.exception('Failed to search messages: %s', e)
            raise

    async def search_conversations(
        self,
        search_query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Conversations]:
        """Search conversations by name"""
        try:
            # Validate search query
            if not search_query or len(search_query.strip()) < 1:
                raise ValueError('Search query cannot be empty')

            # Search conversations
            conversations = await self._conversation_repo.search_conversations(
                search_query=search_query.strip(),
                skip=skip,
                limit=limit,
            )
            # Set avatar_url explicitly for each conversation to avoid lazy loading
            for conversation in conversations:
                if conversation.avatar:
                    conversation.avatar_url = conversation.avatar.url
                else:
                    conversation.avatar_url = None
            return conversations
        except ValueError:
            raise
        except Exception as e:
            logger.exception('Failed to search conversations: %s', e)
            raise

    async def upload_conversation_avatar(  # noqa: PLR0912
        self, conversation_id: UUID, user_id: UUID, file: UploadFile
    ) -> Media:
        """
        Upload conversation avatar to S3 and create a Media record.

        Only allowed for POLYLOGUE conversations.
        Only OWNER or ADMIN can upload avatars.
        Validates that the file is an image (jpeg, png, gif, webp) and max 10MB.
        Deletes old avatar if exists.
        """
        if not self._media_repo or not self._s3_manager:
            raise ValueError('Media repository and S3 manager are required for avatar upload')

        try:
            # Check if conversation exists
            conversation = await self._conversation_repo.get_by_id(conversation_id)
            if not conversation:
                raise ValueError('Conversation not found')

            # Check if conversation is POLYLOGUE (only group chats can have avatars)
            if conversation.conversation_type != ConversationType.POLYLOGUE:
                raise ValueError('Avatars can only be set for group conversations (POLYLOGUE)')

            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Check permissions: only OWNER or ADMIN can upload avatars
            user_role = await self._conversation_repo.get_user_role(user_id, conversation_id)
            if user_role not in [Roles.OWNER, Roles.ADMIN]:
                raise ValueError('Only OWNER or ADMIN can upload conversation avatars')

            # Read file content once for validation and upload
            file_content = await file.read()
            file_size = len(file_content)

            # Validate file size
            if file_size > AVATAR_MAX_FILE_SIZE:
                raise ValueError(
                    f'File size ({file_size} bytes) exceeds maximum allowed size '
                    f'of {AVATAR_MAX_FILE_SIZE} bytes ({AVATAR_MAX_FILE_SIZE / (1024 * 1024):.1f}MB)'
                )

            if file_size == 0:
                raise ValueError('File is empty')

            # Validate content type
            content_type = file.content_type or 'application/octet-stream'
            if content_type not in AVATAR_ALLOWED_CONTENT_TYPES:
                raise ValueError(
                    f"File type '{content_type}' is not allowed for avatars. "
                    f'Allowed types: {", ".join(sorted(AVATAR_ALLOWED_CONTENT_TYPES))}'
                )

            # Delete old avatar if exists
            old_avatar = await self._media_repo.get_conversation_avatar(conversation_id)
            if old_avatar:
                # Construct file path from known format: conversation_avatars/{conversation_id}/{media_id}
                old_file_path = f'conversation_avatars/{conversation_id}/{old_avatar.id}'

                # Delete from S3 first
                try:
                    await self._s3_manager.delete_file(old_file_path)
                    logger.info('Deleted old conversation avatar file from S3: %s', old_file_path)
                except Exception as e:
                    logger.warning('Failed to delete old conversation avatar file from S3: %s', e)
                    # Continue even if S3 deletion fails

                # Delete from database
                deleted = await self._media_repo.delete_conversation_avatar(conversation_id)
                if deleted:
                    logger.info('Deleted old conversation avatar from database for conversation: %s', conversation_id)
                else:
                    logger.warning(
                        'Failed to delete old conversation avatar from database for conversation: %s', conversation_id
                    )

            # Generate media ID for file path and DB record
            media_id = uuid4()

            # Form file path: conversation_avatars/{conversation_id}/{media_id}
            file_path = f'conversation_avatars/{conversation_id}/{media_id}'

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
                raise ValueError('Failed to upload file to S3')

            # Create Media record with the same media_id used in file path
            return await self._media_repo.create_media(
                content_type=upload_result['mime_type'],
                url=upload_result['url'],
                size=upload_result['size'],
                conversation_id=conversation_id,
                media_id=media_id,
            )
        except Exception as e:
            logger.exception('Failed to upload conversation avatar: %s', e)
            raise

    async def delete_conversation_avatar(self, conversation_id: UUID, user_id: UUID) -> bool:
        """Delete conversation avatar from S3 and database"""
        if not self._media_repo or not self._s3_manager:
            raise ValueError('Media repository and S3 manager are required for avatar deletion')

        try:
            # Check if conversation exists
            conversation = await self._conversation_repo.get_by_id(conversation_id)
            if not conversation:
                raise ValueError('Conversation not found')

            # Check if user is participant
            is_participant = await self._conversation_repo.is_participant(user_id, conversation_id)
            if not is_participant:
                raise ValueError('User is not a participant of this conversation')

            # Check permissions: only OWNER or ADMIN can delete avatars
            user_role = await self._conversation_repo.get_user_role(user_id, conversation_id)
            if user_role not in [Roles.OWNER, Roles.ADMIN]:
                raise ValueError('Only OWNER or ADMIN can delete conversation avatars')

            avatar = await self._media_repo.get_conversation_avatar(conversation_id)
            if not avatar:
                return False

            # Delete from S3
            file_path = f'conversation_avatars/{conversation_id}/{avatar.id}'
            try:
                await self._s3_manager.delete_file(file_path)
                logger.info('Deleted conversation avatar file from S3: %s', file_path)
            except Exception as e:
                logger.warning('Failed to delete conversation avatar file from S3: %s', e)
                # Continue even if S3 deletion fails

            # Delete from database
            return await self._media_repo.delete_conversation_avatar(conversation_id)
        except Exception as e:
            logger.exception('Failed to delete conversation avatar: %s', e)
            raise

    async def update_last_read_message_id(self, user_id: UUID, conversation_id: UUID, message_id: UUID) -> bool:
        """
        Update last_read_message_id for a user in a conversation.
        Returns True if successful, False otherwise.
        """
        try:
            participant = await self._conversation_repo.update_last_read_message_id(
                user_id, conversation_id, message_id
            )
            return participant is not None
        except Exception as e:
            logger.exception('Failed to update last_read_message_id: %s', e)
            return False
