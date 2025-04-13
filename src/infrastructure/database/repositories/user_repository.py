from src.infrastructure.database.repositories.base import SQLAlchemyRepository
from src.infrastructure.database.models.users import Users


class UserRepository(SQLAlchemyRepository[Users]):
    """Repository for managing users"""

    model: Users = Users
