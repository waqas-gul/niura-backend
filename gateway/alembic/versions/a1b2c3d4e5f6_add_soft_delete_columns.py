"""add soft delete columns

Revision ID: a1b2c3d4e5f6
Revises: 67afbf298baf
Create Date: 2026-01-01 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '67afbf298baf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_deleted column
    op.add_column('users', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    # Add deleted_at column
    op.add_column('users', sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    # Remove columns
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'is_deleted')
