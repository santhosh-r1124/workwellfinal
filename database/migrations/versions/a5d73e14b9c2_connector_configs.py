"""employee-owned connector configuration

The credential is stored as Fernet ciphertext, never plaintext: a private
calendar subscribe URL is a bearer credential, and a database dump of
plain URLs would hand out standing read access to employees' calendars.

Revision ID: a5d73e14b9c2
Revises: f3a91c206e84
Create Date: 2026-09-25 08:00:00.000000

"""
from typing import Sequence, Union

import pgvector  # noqa: F401  (autogenerate emits pgvector types unqualified)
import sqlalchemy as sa
from alembic import op

revision: str = 'a5d73e14b9c2'
down_revision: Union[str, None] = 'f3a91c206e84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'connector_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('employee_id', sa.String(), nullable=False),
        sa.Column('connector_key', sa.String(), nullable=False),
        sa.Column('encrypted_config', sa.String(), nullable=False),
        sa.Column('config_hint', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_sync_status', sa.String(), nullable=True),
        sa.Column('last_sync_detail', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'connector_key', name='uq_connector_per_employee'),
    )
    op.create_index(op.f('ix_connector_configs_employee_id'), 'connector_configs', ['employee_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_connector_configs_employee_id'), table_name='connector_configs')
    op.drop_table('connector_configs')
