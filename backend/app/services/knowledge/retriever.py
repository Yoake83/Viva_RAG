"""Dynamic retrieval: multi-query search, relevance floor, and MMR re-ranking for diverse context."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from app.config import Settings

from .chunking import Chunk
from .embeddings import Embedder
from .store import VectorStore


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    meta: dict = field(default_factory=dict)


def mmr_select(cand_embs: np.ndarray, relevance: np.ndarray, k: int, lam: float) -> list[int]:
    """Maximal Marginal Relevance: balance relevance to the query against redundancy with chosen chunks."""
    selected: list[int] = []
    remaining = list(range(len(relevance)))
    while remaining and len(selected) < k:
        if not selected:
            best = remaining[int(np.argmax(relevance[remaining]))]
        else:
            sim = cand_embs[remaining] @ cand_embs[selected].T
            scores = lam * relevance[remaining] - (1 - lam) * sim.max(axis=1)
            best = remaining[int(np.argmax(scores))]
        selected.append(best)
        remaining.remove(best)
    return selected


class Retriever:
    def __init__(self, store: VectorStore, embedder: Embedder, settings: Settings):
        self.store = store
        self.embedder = embedder
        self.settings = settings

    def retrieve(self, queries: list[str], *, role: str, k: int, exclude_ids: Iterable[str] = ()) -> RetrievalResult:
        s = self.settings
        excluded = set(exclude_ids)
        qvecs = [self.embedder.embed_query(q) for q in queries if q.strip()]
        if not qvecs:
            return RetrievalResult([], {"queries": queries, "quality": "none", "candidates": 0})

        pool: dict[str, tuple[Chunk, np.ndarray]] = {}
        for qv in qvecs:
            for hit in self.store.query(qv, s.retrieval_fetch_k, role):
                if hit.chunk.id not in excluded:
                    pool.setdefault(hit.chunk.id, (hit.chunk, hit.embedding))
        if not pool:
            return RetrievalResult([], {"queries": queries, "quality": "none", "candidates": 0})

        items = list(pool.values())
        embs = np.vstack([e for _, e in items])
        relevance = np.max(np.vstack([embs @ qv for qv in qvecs]), axis=0)  # best match across all queries

        above = np.where(relevance >= s.retrieval_min_score)[0]
        quality = "high" if len(above) >= k else "medium" if len(above) >= 1 else "low"
        eligible = above if len(above) else np.argsort(-relevance)[:k]  # never return nothing if the KB has data
        picked = mmr_select(embs[eligible], relevance[eligible], k, s.retrieval_mmr_lambda)
        chosen = [int(eligible[i]) for i in picked]

        return RetrievalResult(
            chunks=[RetrievedChunk(chunk=items[i][0], score=float(relevance[i])) for i in chosen],
            meta={
                "queries": queries,
                "quality": quality,
                "candidates": len(items),
                "threshold": s.retrieval_min_score,
            },
        )
