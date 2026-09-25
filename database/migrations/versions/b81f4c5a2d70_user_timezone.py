"""per-employee timezone

The unit of analysis is a day, so the boundary has to be drawn where the
employee's day actually ends. Existing rows get UTC, which is what the
code assumed before this column existed.

Revision ID: b81f4c5a2d70
Revises: a5d73e14b9c2
Create Date: 2026-09-25 09:00:00.000000

"""
from typing import Sequence, Union

import pgvector  # noqa: F401  (autogenerate emits pgvector types unqualified)
import sqlalchemy as sa
from alembic import op

revision: str = 'b81f4c5a2d70'
down_revision: Union[str, None] = 'a5d73e14b9c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'),
    )


def downgrade() -> None:
    op.drop_column('users', 'timezone')
