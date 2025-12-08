"""add avatar for users

Revision ID: 60f6d23d9c1e
Revises: 33cbd4d8b6de
Create Date: 2025-12-07 23:38:27.018076

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60f6d23d9c1e'
down_revision: Union[str, None] = '33cbd4d8b6de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to media table
    op.add_column('media', sa.Column('user_id', sa.UUID(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key('fk_media_user_id', 'media', 'users', ['user_id'], ['id'], ondelete='SET NULL')

    # Drop old constraint
    op.drop_constraint('check_media_reference', 'media', type_='check')

    # Create new constraint: either message_id, story_id, or user_id must be set
    op.execute("""
        ALTER TABLE media 
        ADD CONSTRAINT check_media_reference 
        CHECK (message_id IS NOT NULL OR story_id IS NOT NULL OR user_id IS NOT NULL)
    """)

    # Create index on user_id for faster avatar lookups
    op.create_index('ix_media_user_id', 'media', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_media_user_id', table_name='media')

    # Drop new constraint
    op.drop_constraint('check_media_reference', 'media', type_='check')

    # Restore old constraint
    op.execute("""
        ALTER TABLE media 
        ADD CONSTRAINT check_media_reference 
        CHECK (message_id IS NOT NULL OR story_id IS NOT NULL)
    """)

    # Drop foreign key
    op.drop_constraint('fk_media_user_id', 'media', type_='foreignkey')

    # Drop user_id column
    op.drop_column('media', 'user_id')
