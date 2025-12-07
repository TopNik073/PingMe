from uuid import UUID
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from src.infrastructure.database.repositories.base import SQLAlchemyRepository
from src.infrastructure.database.models.conversations import Conversations
from src.infrastructure.database.models.user_conversation import UserConversation
from src.infrastructure.database.models.messages import Messages
from src.infrastructure.database.models.users import Users
from src.infrastructure.database.enums.Roles import Roles


class ConversationRepository(SQLAlchemyRepository[Conversations]):
    model: Conversations = Conversations

    async def add_participant(
        self, user_id: UUID, conversation_id: UUID, role: Roles = Roles.MEMBER
    ) -> UserConversation:
        """Add a participant to a conversation"""
        user_conversation = UserConversation(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
        )
        self.add_object(user_conversation)
        await self.commit()
        await self.refresh(user_conversation)
        return user_conversation

    async def remove_participant(
        self, user_id: UUID, conversation_id: UUID
    ) -> bool:
        """Remove a participant from a conversation"""
        query = select(UserConversation).where(
            and_(
                UserConversation.user_id == user_id,
                UserConversation.conversation_id == conversation_id
            )
        )
        result = await self._session.execute(query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            return False
        
        await self._session.delete(participant)
        await self.commit()
        return True

    async def update_participant_role(
        self, user_id: UUID, conversation_id: UUID, new_role: Roles
    ) -> UserConversation | None:
        """Update participant role in a conversation"""
        query = select(UserConversation).where(
            and_(
                UserConversation.user_id == user_id,
                UserConversation.conversation_id == conversation_id
            )
        )
        result = await self._session.execute(query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            return None
        
        participant.role = new_role
        await self.commit()
        await self.refresh(participant)
        return participant

    async def get_participants(
        self, conversation_id: UUID, include_user: bool = True
    ) -> list[UserConversation]:
        """Get all participants of a conversation"""
        query = select(UserConversation).where(
            UserConversation.conversation_id == conversation_id
        )
        
        if include_user:
            query = query.options(
                selectinload(UserConversation.user).selectinload(Users.avatar)
            )
        
        result = await self._session.execute(query)
        participants = result.scalars().all()
        
        return list(participants) if participants else []

    async def is_participant(self, user_id: UUID, conversation_id: UUID) -> bool:
        """Check if user is a participant of the conversation"""
        query = select(UserConversation).where(
            and_(
                UserConversation.user_id == user_id,
                UserConversation.conversation_id == conversation_id
            )
        )
        result = await self._session.execute(query)
        participant = result.scalar_one_or_none()
        return participant is not None

    async def get_user_role(
        self, user_id: UUID, conversation_id: UUID
    ) -> Roles | None:
        """Get user's role in a conversation"""
        query = select(UserConversation).where(
            and_(
                UserConversation.user_id == user_id,
                UserConversation.conversation_id == conversation_id
            )
        )
        result = await self._session.execute(query)
        participant = result.scalar_one_or_none()
        return participant.role if participant else None

    async def get_user_conversations(
        self, user_id: UUID, include_relations: list[str] | None = None
    ) -> list[Conversations]:
        """
        Get all conversations for a user, sorted by last message time (newest first).
        Conversations without messages are placed at the end.
        """
        # Subquery to get the latest message time for each conversation
        last_message_subquery = (
            select(
                func.max(Messages.created_at).label('last_message_at')
            )
            .where(Messages.conversation_id == self.model.id)
            .where(Messages.is_deleted == False)
            .scalar_subquery()
        )
        
        # Main query
        query = (
            select(self.model)
            .join(UserConversation)
            .where(UserConversation.user_id == user_id)
            .where(self.model.is_deleted == False)
            .order_by(desc(last_message_subquery).nulls_last())
        )
        
        if include_relations:
            for relation in include_relations:
                query = query.options(selectinload(getattr(self.model, relation)))
        
        result = await self._session.execute(query)
        conversations = result.scalars().unique().all()
        
        return list(conversations) if conversations else []

    async def search_conversations(
        self,
        search_query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Conversations]:
        """
        Search conversations by name.
        Uses case-insensitive ILIKE for pattern matching.
        """
        # Prepare search pattern (add % for wildcard matching)
        search_pattern = f"%{search_query}%"
        
        query = (
            select(self.model)
            .where(self.model.name.ilike(search_pattern))
            .where(self.model.is_deleted == False)
            .options(selectinload(self.model.avatar))
            .order_by(self.model.name.asc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self._session.execute(query)
        conversations = result.scalars().all()
        
        return list(conversations) if conversations else []
    
    async def update_last_read_message_id(
        self, user_id: UUID, conversation_id: UUID, message_id: UUID
    ) -> UserConversation | None:
        """
        Update last_read_message_id for a user in a conversation.
        Validates that:
        - Message exists
        - Message belongs to the conversation
        - User is a participant of the conversation
        """
        # Check if user is a participant
        participant = await self._get_participant(user_id, conversation_id)
        if not participant:
            return None
        
        # Check if message exists and belongs to conversation
        message_query = select(Messages).where(
            and_(
                Messages.id == message_id,
                Messages.conversation_id == conversation_id,
                Messages.is_deleted == False
            )
        )
        result = await self._session.execute(message_query)
        message = result.scalar_one_or_none()
        
        if not message:
            return None
        
        # Update last_read_message_id
        participant.last_read_message_id = message_id
        await self.commit()
        await self.refresh(participant)
        
        return participant
    
    async def _get_participant(
        self, user_id: UUID, conversation_id: UUID
    ) -> UserConversation | None:
        """Get participant record"""
        query = select(UserConversation).where(
            and_(
                UserConversation.user_id == user_id,
                UserConversation.conversation_id == conversation_id
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()