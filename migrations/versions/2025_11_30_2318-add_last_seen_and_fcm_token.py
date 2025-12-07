"""Add last_seen and fcm_token to users

Revision ID: a1b2c3d4e5f6
Revises: 36d7c59c9aac
Create Date: 2025-11-30 23:18:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "36d7c59c9aac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add last_seen column to users table
    op.add_column("users", sa.Column("last_seen", sa.DateTime(), nullable=True))
    
    # Add fcm_token column to users table
    op.add_column("users", sa.Column("fcm_token", sa.String(), nullable=True))


def downgrade() -> None:
    # Remove fcm_token column
    op.drop_column("users", "fcm_token")
    
    # Remove last_seen column
    op.drop_column("users", "last_seen")

