from src.infrastructure.database.repositories.base import SQLAlchemyRepository
from src.infrastructure.database.models.conversations import Conversations


class ConversationRepository(SQLAlchemyRepository[Conversations]):
    model: Conversations = Conversations
