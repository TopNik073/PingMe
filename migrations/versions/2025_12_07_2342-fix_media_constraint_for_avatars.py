"""Fix media constraint for avatars

Revision ID: d7e8f9a0b1c2
Revises: 60f6d23d9c1e
Create Date: 2025-12-07 23:42:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, None] = "60f6d23d9c1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old constraint if it exists
    op.execute("ALTER TABLE media DROP CONSTRAINT IF EXISTS check_media_reference")
    
    # Create new constraint: either message_id, story_id, or user_id must be set
    op.execute("""
        ALTER TABLE media 
        ADD CONSTRAINT check_media_reference 
        CHECK (message_id IS NOT NULL OR story_id IS NOT NULL OR user_id IS NOT NULL)
    """)
    
    # Create index on user_id for faster avatar lookups (if not exists)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_media_user_id ON media(user_id)
    """)


def downgrade() -> None:
    # Drop index if exists
    op.execute("DROP INDEX IF EXISTS ix_media_user_id")
    
    # Drop new constraint
    op.execute("ALTER TABLE media DROP CONSTRAINT IF EXISTS check_media_reference")
    
    # Restore old constraint
    op.execute("""
        ALTER TABLE media 
        ADD CONSTRAINT check_media_reference 
        CHECK (message_id IS NOT NULL OR story_id IS NOT NULL)
    """)
