"""Make media message_id required

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-01 00:32:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, delete any media records that don't have message_id or story_id
    op.execute("""
        DELETE FROM media 
        WHERE message_id IS NULL AND story_id IS NULL
    """)

    # Add check constraint: either message_id or story_id must be set
    op.execute("""
        ALTER TABLE media 
        ADD CONSTRAINT check_media_reference 
        CHECK (message_id IS NOT NULL OR story_id IS NOT NULL)
    """)


def downgrade() -> None:
    # Remove check constraint
    op.execute('ALTER TABLE media DROP CONSTRAINT IF EXISTS check_media_reference')
