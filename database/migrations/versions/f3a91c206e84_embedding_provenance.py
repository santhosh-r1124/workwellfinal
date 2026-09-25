"""record which model produced each embedding

Vectors from two different embedding models are not comparable, and
comparing them does not fail - it returns a confidently wrong top_k. Rows
that predate this column are stamped 'unknown' and will not match any
current model, which is correct: they were embedded by something nobody
recorded, so re-ingest.

Revision ID: f3a91c206e84
Revises: e2b8c4d71f05
Create Date: 2026-09-25 07:00:00.000000

"""
from typing import Sequence, Union

import pgvector  # noqa: F401  (autogenerate emits pgvector types unqualified)
import sqlalchemy as sa
from alembic import op

revision: str = 'f3a91c206e84'
down_revision: Union[str, None] = 'e2b8c4d71f05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'knowledge_chunks',
        sa.Column(
            'embedding_model', sa.String(), nullable=False, server_default='unknown'
        ),
    )
    op.create_index(
        op.f('ix_knowledge_chunks_embedding_model'), 'knowledge_chunks', ['embedding_model']
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_knowledge_chunks_embedding_model'), table_name='knowledge_chunks')
    op.drop_column('knowledge_chunks', 'embedding_model')
