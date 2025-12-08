"""Add trigram extension

Revision ID: b26aa53191da
Revises:
Create Date: 2025-02-02 20:39:41.066606

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b26aa53191da'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')


def downgrade():
    op.execute('DROP EXTENSION pg_trgm')
