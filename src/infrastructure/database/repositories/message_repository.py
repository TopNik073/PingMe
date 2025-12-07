from uuid import UUID
from sqlalchemy import select, text, bindparam, and_
from sqlalchemy.orm import selectinload

from src.infrastructure.database.repositories.base import SQLAlchemyRepository
from src.infrastructure.database.models.messages import Messages
from src.infrastructure.database.models.user_conversation import UserConversation
from src.infrastructure.database.models.users import Users
from src.infrastructure.database.models.BaseModel import get_datetime_UTC


class MessageRepository(SQLAlchemyRepository[Messages]):
    model: Messages = Messages

    async def get_conversation_messages(
        self,
        conversation_id: UUID,
        user_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Messages]:
        """
        Get messages for a conversation with smart pagination.
        If user_id is provided and has last_read_message_id, shows unread messages first.
        """
        # Base query conditions
        base_conditions = [self.model.conversation_id == conversation_id, self.model.is_deleted == False]
        
        # Get last_read_message_id if user_id is provided
        last_read_message = None
        if user_id:
            participant_query = select(UserConversation).where(
                and_(
                    UserConversation.user_id == user_id,
                    UserConversation.conversation_id == conversation_id
                )
            )
            participant_result = await self._session.execute(participant_query)
            participant = participant_result.scalar_one_or_none()
            
            if participant and participant.last_read_message_id:
                # Get the last read message to get its created_at
                last_read_query = select(self.model).where(
                    self.model.id == participant.last_read_message_id
                )
                last_read_result = await self._session.execute(last_read_query)
                last_read_message = last_read_result.scalar_one_or_none()
        
        messages = []
        
        # Smart pagination: if we have last_read_message, get unread messages first
        if last_read_message:
            # Get unread messages (created after last_read_message)
            unread_query = select(self.model).where(
                and_(
                    *base_conditions,
                    self.model.created_at > last_read_message.created_at
                )
            )
            unread_query = unread_query.options(
                selectinload(self.model.sender).selectinload(Users.avatar),
                selectinload(self.model.media)
            )
            
            unread_result = await self._session.execute(unread_query)
            unread_messages = list(unread_result.scalars().all())
            
            # If we have unread messages, show them first (most recent first for mobile)
            if unread_messages:
                # Sort unread messages by created_at desc (newest first)
                unread_messages.sort(key=lambda m: m.created_at, reverse=True)
                
                # If we have fewer unread messages than limit, fill with recent read messages
                if len(unread_messages) < limit:
                    remaining = limit - len(unread_messages)
                    # Get recent read messages (up to last_read_message, inclusive)
                    recent_query = select(self.model).where(
                        and_(
                            *base_conditions,
                            self.model.created_at <= last_read_message.created_at
                        )
                    )
                    recent_query = recent_query.options(
                        selectinload(self.model.sender).selectinload(Users.avatar),
                        selectinload(self.model.media)
                    ).order_by(self.model.created_at.desc()).limit(remaining)
                    
                    recent_result = await self._session.execute(recent_query)
                    recent_messages = list(recent_result.scalars().all())
                    
                    # Combine: unread first (newest first), then recent read (newest first)
                    messages = unread_messages + recent_messages
                else:
                    # Only unread messages, limit to requested limit
                    messages = unread_messages[:limit]
            else:
                # No unread messages, show recent messages (standard behavior)
                query = select(self.model).where(and_(*base_conditions))
                query = query.options(
                    selectinload(self.model.sender).selectinload(Users.avatar),
                    selectinload(self.model.media)
                ).order_by(self.model.created_at.desc()).offset(skip).limit(limit)
                
                result = await self._session.execute(query)
                messages = list(result.scalars().all())
        else:
            # No last_read_message: use standard pagination (most recent first)
            query = select(self.model).where(and_(*base_conditions))
            query = query.options(
                selectinload(self.model.sender).selectinload(Users.avatar),
                selectinload(self.model.media)
            ).order_by(self.model.created_at.desc()).offset(skip).limit(limit)
            
            result = await self._session.execute(query)
            messages = list(result.scalars().all())
        
        return messages

    async def get_conversation_messages_count(
        self,
        conversation_id: UUID,
        include_deleted: bool = False,
    ) -> int:
        """Get total count of messages in a conversation"""
        query = select(self.model).where(
            self.model.conversation_id == conversation_id
        )
        
        if not include_deleted:
            query = query.where(self.model.is_deleted == False)
        
        result = await self._session.execute(query)
        messages = result.scalars().all()
        
        return len(messages) if messages else 0

    async def create_message(
        self,
        sender_id: UUID,
        conversation_id: UUID,
        content: str,
        forwarded_from_id: UUID | None = None,
    ) -> Messages:
        """Create a new message"""
        message = Messages(
            sender_id=sender_id,
            conversation_id=conversation_id,
            content=content,
            forwarded_from_id=forwarded_from_id,
            is_edited=False,
            is_deleted=False,
        )
        self.add_object(message)
        await self.flush()
        await self.refresh(message)
        
        # Load relationships with avatar
        query = select(self.model).where(self.model.id == message.id)
        query = query.options(
            selectinload(self.model.sender).selectinload(Users.avatar),
            selectinload(self.model.media)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def update_message(
        self,
        message_id: UUID,
        content: str,
        user_id: UUID,
    ) -> Messages | None:
        """Update an existing message (only by sender)"""
        message = await self.get_by_id(message_id, include_relations=["sender", "media"])
        
        if not message:
            return None
        
        # Check if user is the sender
        if message.sender_id != user_id:
            raise ValueError("Only the message sender can edit the message")
        
        # Check if message is deleted
        if message.is_deleted:
            raise ValueError("Cannot edit a deleted message")
        
        message.content = content
        message.is_edited = True
        message.updated_at = get_datetime_UTC()
        
        await self.flush()
        
        # Reload message with sender and avatar
        return await self.get_message_by_id(message_id, include_deleted=False)

    async def delete_message(
        self,
        message_id: UUID,
        user_id: UUID,
    ) -> Messages | None:
        """Soft delete a message (only by sender)"""
        message = await self.get_by_id(message_id, include_relations=["sender", "media"])
        
        if not message:
            return None
        
        # Check if user is the sender
        if message.sender_id != user_id:
            raise ValueError("Only the message sender can delete the message")
        
        # Check if already deleted
        if message.is_deleted:
            return message
        
        message.is_deleted = True
        message.deleted_at = get_datetime_UTC()
        message.updated_at = get_datetime_UTC()
        
        await self.flush()
        await self.refresh(message)
        
        return message

    async def forward_message(
        self,
        message_id: UUID,
        sender_id: UUID,
        target_conversation_id: UUID,
    ) -> Messages | None:
        """Forward a message to another conversation"""
        # Get the original message with sender and avatar
        original_message = await self.get_message_by_id(message_id)
        
        if not original_message:
            return None
        
        if original_message.is_deleted:
            raise ValueError("Cannot forward a deleted message")
        
        # Create a new message with forwarded content
        forwarded_message = Messages(
            sender_id=sender_id,
            conversation_id=target_conversation_id,
            content=original_message.content,
            forwarded_from_id=original_message.sender_id,
            media=original_message.media,
            is_edited=False,
            is_deleted=False,
        )
        
        self.add_object(forwarded_message)
        await self.flush()
        await self.refresh(forwarded_message)
        
        # Load relationships with avatar
        query = select(self.model).where(self.model.id == forwarded_message.id)
        query = query.options(
            selectinload(self.model.sender).selectinload(Users.avatar),
            selectinload(self.model.media)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_message_by_id(
        self,
        message_id: UUID,
        include_deleted: bool = False,
    ) -> Messages | None:
        """Get a message by ID"""
        query = select(self.model).where(self.model.id == message_id)
        
        if not include_deleted:
            query = query.where(self.model.is_deleted == False)
        
        query = query.options(
            selectinload(self.model.sender).selectinload(Users.avatar),
            selectinload(self.model.media),
            selectinload(self.model.conversation),
        )
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_message_readers(
        self,
        message_ids: list[UUID],
        conversation_id: UUID,
    ) -> dict[UUID, list[dict]]:
        """
        Get readers for multiple messages in one query.
        Returns a dict mapping message_id to list of readers with user_id, user_name, read_at.
        A user is considered to have read a message if their last_read_message_id
        points to a message with created_at >= this message's created_at.
        """
        if not message_ids:
            return {}
        
        # Get all messages to compare created_at
        messages_query = select(self.model).where(
            and_(
                self.model.id.in_(message_ids),
                self.model.conversation_id == conversation_id
            )
        )
        messages_result = await self._session.execute(messages_query)
        messages = {msg.id: msg for msg in messages_result.scalars().all()}
        
        if not messages:
            return {}
        
        # Get all participants with their last_read_message_id
        participants_query = select(
            UserConversation.user_id,
            UserConversation.last_read_message_id,
            UserConversation.updated_at,
            Users.name,
            Users.username
        ).join(
            Users, UserConversation.user_id == Users.id
        ).where(
            UserConversation.conversation_id == conversation_id,
            UserConversation.last_read_message_id.isnot(None)
        )
        
        participants_result = await self._session.execute(participants_query)
        participants = participants_result.all()
        
        # Get last_read_message for each participant to compare created_at
        last_read_message_ids = {
            p.last_read_message_id for p in participants if p.last_read_message_id
        }
        
        if not last_read_message_ids:
            return {msg_id: [] for msg_id in message_ids}
        
        last_read_messages_query = select(self.model).where(
            self.model.id.in_(last_read_message_ids)
        )
        last_read_messages_result = await self._session.execute(last_read_messages_query)
        last_read_messages = {
            msg.id: msg for msg in last_read_messages_result.scalars().all()
        }
        
        # Build result: for each message, find participants who read it
        result: dict[UUID, list[dict]] = {msg_id: [] for msg_id in message_ids}
        
        for participant in participants:
            if not participant.last_read_message_id:
                continue
            
            last_read_msg = last_read_messages.get(participant.last_read_message_id)
            if not last_read_msg:
                continue
            
            # Check which messages this participant has read
            # (messages with created_at <= last_read_message.created_at)
            for msg_id, message in messages.items():
                if message.created_at <= last_read_msg.created_at:
                    result[msg_id].append({
                        'user_id': participant.user_id,
                        'name': participant.name,
                        'username': participant.username,
                        'read_at': participant.updated_at
                    })
        
        return result

    async def search_messages(
        self,
        conversation_id: UUID,
        search_query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Messages]:
        """Search messages in a conversation using PostgreSQL trigram similarity"""
        # Use PostgreSQL trigram operator % for similarity search
        # This uses the GIN index on content field
        query = (
            select(self.model)
            .where(self.model.conversation_id == conversation_id)
            .where(self.model.is_deleted == False)
            .where(text("content % :search_query", bindparams=[bindparam("search_query", search_query)]))
            .options(
                selectinload(self.model.sender).selectinload(Users.avatar),
                selectinload(self.model.media)
            )
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self._session.execute(query)
        messages = result.scalars().all()
        
        return list(messages) if messages else []

