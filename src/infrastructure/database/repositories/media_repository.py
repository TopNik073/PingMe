from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.infrastructure.database.repositories.base import SQLAlchemyRepository
from src.infrastructure.database.models.media import Media
from src.infrastructure.database.models.messages import Messages


class MediaRepository(SQLAlchemyRepository[Media]):
    model: Media = Media

    async def create_media(  # noqa: PLR0913
        self,
        content_type: str,
        url: str,
        size: int,
        message_id: UUID | None = None,
        story_id: UUID | None = None,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
        media_id: UUID | None = None,
    ) -> Media:
        """
        Create a new media record.
        
        Note: Either message_id, story_id, user_id, or conversation_id must be provided (enforced by DB constraint).
        For message media, message_id should be provided.
        For user avatars, user_id should be provided.
        For conversation avatars, conversation_id should be provided.
        """
        if not message_id and not story_id and not user_id and not conversation_id:
            raise ValueError("Either message_id, story_id, user_id, or conversation_id must be provided")
        
        media = Media(
            id=media_id if media_id else None,  # If None, DB will generate it
            content_type=content_type,
            url=url,
            size=size,
            message_id=message_id,
            story_id=story_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        self.add_object(media)
        await self.flush()
        await self.refresh(media)
        
        return media

    async def attach_to_message(
        self,
        media_id: UUID,
        message_id: UUID,
    ) -> Media | None:
        """Attach existing media to a message"""
        media = await self.get_media_by_id(media_id, include_message=False)
        if not media:
            return None
        
        # Check if media is already attached to a message
        if media.message_id:
            raise ValueError("Media is already attached to a message")
        
        # Check if media is attached to a story
        if media.story_id:
            raise ValueError("Media is attached to a story and cannot be attached to a message")
        
        media.message_id = message_id
        await self.flush()
        await self.refresh(media)
        
        return media

    async def get_message_media(
        self,
        message_id: UUID,
    ) -> list[Media]:
        """Get all media files for a specific message"""
        query = select(self.model).where(
            self.model.message_id == message_id
        )
        
        result = await self._session.execute(query)
        media = result.scalars().all()
        
        return list(media) if media else []

    async def get_conversation_media(
        self, conversation_id: UUID, include_message: bool = True
    ) -> list[Media]:
        """Get all media files for a conversation"""
        # Media are linked to messages, and messages are linked to conversations
        query = (
            select(self.model)
            .join(Messages, self.model.message_id == Messages.id)
            .where(Messages.conversation_id == conversation_id)
            .where(self.model.message_id.isnot(None))
        )
        
        if include_message:
            query = query.options(selectinload(self.model.message))
        
        result = await self._session.execute(query)
        media = result.scalars().unique().all()
        
        return list(media) if media else []

    async def get_media_by_id(
        self, media_id: UUID, include_message: bool = True
    ) -> Media | None:
        """Get media by ID with optional message relation"""
        query = select(self.model).where(self.model.id == media_id)
        
        if include_message:
            query = query.options(selectinload(self.model.message))
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_media_by_ids(
        self, media_ids: list[UUID], include_message: bool = True
    ) -> list[Media]:
        """Get multiple media records by their IDs"""
        if not media_ids:
            return []
        
        query = select(self.model).where(self.model.id.in_(media_ids))
        
        if include_message:
            query = query.options(selectinload(self.model.message))
        
        result = await self._session.execute(query)
        media = result.scalars().all()
        
        return list(media) if media else []

    async def get_user_avatar(self, user_id: UUID) -> Media | None:
        """Get user avatar by user_id"""
        query = select(self.model).where(
            self.model.user_id == user_id
        )
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def delete_user_avatar(self, user_id: UUID) -> bool:
        """Delete user avatar by user_id"""
        avatar = await self.get_user_avatar(user_id)
        if not avatar:
            return False
        
        await self._session.delete(avatar)
        await self.flush()
        return True

    async def get_conversation_avatar(self, conversation_id: UUID) -> Media | None:
        """Get conversation avatar by conversation_id"""
        query = select(self.model).where(
            self.model.conversation_id == conversation_id
        )
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def delete_conversation_avatar(self, conversation_id: UUID) -> bool:
        """Delete conversation avatar by conversation_id"""
        avatar = await self.get_conversation_avatar(conversation_id)
        if not avatar:
            return False
        
        await self._session.delete(avatar)
        await self.flush()
        return True

