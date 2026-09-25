"""per-device agent credentials

Replaces a single shared agent token. Nothing is migrated: existing
installs must provision a device token per machine, which is the point -
the old credential could write telemetry for anyone.

Revision ID: e2b8c4d71f05
Revises: c7f1a2b93d40
Create Date: 2026-09-25 06:00:00.000000

"""
from typing import Sequence, Union

import pgvector  # noqa: F401  (autogenerate emits pgvector types unqualified)
import sqlalchemy as sa
from alembic import op

revision: str = 'e2b8c4d71f05'
down_revision: Union[str, None] = 'c7f1a2b93d40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('employee_id', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_device_tokens_employee_id'), 'device_tokens', ['employee_id'])
    op.create_index(op.f('ix_device_tokens_token_hash'), 'device_tokens', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_device_tokens_token_hash'), table_name='device_tokens')
    op.drop_index(op.f('ix_device_tokens_employee_id'), table_name='device_tokens')
    op.drop_table('device_tokens')
