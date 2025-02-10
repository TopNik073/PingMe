from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime, timezone


def get_datetime_UTC() -> datetime:
    """Get current UTC datetime"""
    date = datetime.now()
    return date.replace(tzinfo=None)


class BaseModel(AsyncAttrs, DeclarativeBase):
    """Base class for inheritance new models"""

    repr_cols_num = 1
    repr_cols = tuple()

    def __repr__(self):
        """Relationships are not used in repr() because may lead to unexpected lazy loads"""
        cols = []
        for idx, col in enumerate(self.__table__.columns.keys()):
            if col in self.repr_cols or idx < self.repr_cols_num:
                cols.append(f"{col}={getattr(self, col)}")

        return f"<{self.__class__.__name__} {', '.join(cols)}>"
