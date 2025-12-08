"""Add conversation avatar support

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2025-12-08 00:11:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add conversation_id column to media table
    op.add_column('media', sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_media_conversation_id', 'media', 'conversations', ['conversation_id'], ['id'], ondelete='SET NULL'
    )

    # Drop old constraint
    op.execute('ALTER TABLE media DROP CONSTRAINT IF EXISTS check_media_reference')

    # Create new constraint: either message_id, story_id, user_id, or conversation_id must be set
    op.execute("""
        ALTER TABLE media 
        ADD CONSTRAINT check_media_reference 
        CHECK (message_id IS NOT NULL OR story_id IS NOT NULL OR user_id IS NOT NULL OR conversation_id IS NOT NULL)
    """)

    # Create index on conversation_id for faster avatar lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_media_conversation_id ON media(conversation_id)
    """)


def downgrade() -> None:
    # Drop index
    op.execute('DROP INDEX IF EXISTS ix_media_conversation_id')

    # Drop new constraint
    op.execute('ALTER TABLE media DROP CONSTRAINT IF EXISTS check_media_reference')

    # Restore old constraint
    op.execute("""
        ALTER TABLE media 
        ADD CONSTRAINT check_media_reference 
        CHECK (message_id IS NOT NULL OR story_id IS NOT NULL OR user_id IS NOT NULL)
    """)

    # Drop foreign key
    op.drop_constraint('fk_media_conversation_id', 'media', type_='foreignkey')

    # Drop conversation_id column
    op.drop_column('media', 'conversation_id')
