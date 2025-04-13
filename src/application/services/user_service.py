from src.infrastructure.database.repositories.user_repository import UserRepository
from src.core.logging import get_logger

logger = get_logger(__name__)


class UserService:
    def __init__(self, user_repository: UserRepository):
        self._user_repo: UserRepository = user_repository

    async def find_user(self, **filters):
        try:
            user = await self._user_repo.get_by_filter(
                **filters, include_relations=["received_pings"]
            )
            return user[0] if len(user) == 1 else None
        except Exception as e:
            logger.exception(f"Cannot find user by filters: {filters}", e)
            return None
