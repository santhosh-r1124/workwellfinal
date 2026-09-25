"""deactivatable accounts and a notification opt-out

Someone who leaves the company must stop being analysed. Backfills true so
every existing account keeps working; the server_default keeps inserts that
predate the model change valid.

Revision ID: c7f1a2b93d40
Revises: baf4d563b820
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

import pgvector  # noqa: F401  (autogenerate emits pgvector types unqualified)
import sqlalchemy as sa
from alembic import op

revision: str = 'c7f1a2b93d40'
down_revision: Union[str, None] = 'baf4d563b820'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.add_column(
        'users',
        sa.Column(
            'notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'notifications_enabled')
    op.drop_column('users', 'is_active')
