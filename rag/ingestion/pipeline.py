from pathlib import Path

from sqlalchemy.orm import Session

from agents.providers import get_provider
from apps.backend.repositories import knowledge_repo
from rag.ingestion.chunker import chunk_text
from rag.ingestion.parser import parse_file

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"
SUPPORTED_EXTENSIONS = {".md", ".txt", ".html", ".pdf", ".docx"}


def _extract_title_and_source(raw_text: str, fallback: str) -> tuple[str, str | None]:
    source_url = None
    lines = raw_text.splitlines()
    for line in lines[:3]:
        stripped = line.strip()
        if stripped.startswith("<!-- source:") and stripped.endswith("-->"):
            candidate = stripped[len("<!-- source:") : -len("-->")].strip()
            # Only surface it as a citable link if it actually is one - most
            # seed docs are original/paraphrased content with a provenance
            # note, not a verbatim quote of an external URL.
            if candidate.startswith("http://") or candidate.startswith("https://"):
                source_url = candidate
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip(), source_url
    return fallback, source_url


def ingest_knowledge_base(db: Session, root: Path | None = None) -> int:
    """PDF/DOCX/HTML/Markdown -> parse -> chunk -> embed -> pgvector (Phase 7.1).
    Idempotent-ish for demo purposes: re-running adds duplicate documents, so
    callers should clear knowledge tables first if re-ingesting."""
    root = root or KNOWLEDGE_ROOT
    provider = get_provider()
    total_chunks = 0

    for category_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        category = category_dir.name
        for doc_path in sorted(category_dir.glob("*")):
            if doc_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            raw_text = parse_file(doc_path)
            title, source_url = _extract_title_and_source(raw_text, doc_path.stem)
            chunks = chunk_text(raw_text)
            if not chunks:
                continue

            document = knowledge_repo.create_document(
                db, title=title, source_url=source_url, category=category
            )
            embeddings = provider.embed(chunks)
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                knowledge_repo.create_chunk(
                    db,
                    document_id=document.id,
                    content=chunk,
                    meta={"chunk_index": idx, "title": title},
                    embedding=embedding,
                )
                total_chunks += 1

    return total_chunks
