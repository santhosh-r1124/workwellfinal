from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.backend.core.database import Base
from apps.backend.models.mixins import TimestampMixin, gen_id

# Must match GEMINI_EMBEDDING_DIM in .env.example. Changing the embedding
# model's dimension requires a migration that alters this column.
EMBEDDING_DIM = 768


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False)


class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
