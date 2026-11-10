from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings

from .chunking import PageText, build_chunks, embedding_text, make_section_lookup
from .embeddings import Embedder
from .store import VectorStore

log = logging.getLogger(__name__)


def load_pdf(path: Path) -> tuple[list[PageText], list]:
    import fitz  # PyMuPDF

    with fitz.open(path) as doc:
        pages = [PageText(i + 1, page.get_text("text")) for i, page in enumerate(doc)]
        toc = doc.get_toc(simple=True)
    return pages, toc


def ingest_book(path: Path, meta: dict, store: VectorStore, embedder: Embedder, settings: Settings) -> int:
    """Load -> chunk -> embed -> store. Re-running replaces that book's chunks (idempotent)."""
    pages, toc = load_pdf(path)
    source = meta.get("title") or path.stem
    chunks = build_chunks(
        pages,
        source=source,
        lookup=make_section_lookup(toc, pages),
        target_words=settings.chunk_target_words,
        overlap_words=settings.chunk_overlap_words,
        min_words=settings.chunk_min_words,
        roles=list(meta.get("roles", [])),
    )
    if not chunks:
        log.warning("No usable text found in %s (scanned PDF?).", path.name)
        return 0
    embeddings = embedder.embed_documents([embedding_text(c) for c in chunks])
    store.delete_source(source)
    store.add(chunks, embeddings)
    return len(chunks)
