from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .chunking import Chunk


@dataclass
class Hit:
    chunk: Chunk
    score: float  # cosine similarity
    embedding: np.ndarray


class VectorStore(Protocol):
    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None: ...
    def query(self, embedding: np.ndarray, n: int, role: str | None) -> list[Hit]: ...
    def delete_source(self, source: str) -> None: ...
    def stats(self, role_ids: list[str]) -> dict: ...


class ChromaStore:
    """Persistent Chroma collection using cosine space. Roles are stored as boolean metadata flags
    (role_<id>=True) so role-specific retrieval is a metadata filter, not a separate index."""

    def __init__(self, path: str, collection: str):
        self._path = path
        self._collection_name = collection
        self._col = None

    @property
    def col(self):
        if self._col is None:
            import chromadb

            client = chromadb.PersistentClient(path=self._path)
            self._col = client.get_or_create_collection(name=self._collection_name, metadata={"hnsw:space": "cosine"})
        return self._col

    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        for i in range(0, len(chunks), 500):
            batch = chunks[i : i + 500]
            self.col.add(
                ids=[c.id for c in batch],
                documents=[c.text for c in batch],
                embeddings=embeddings[i : i + 500].tolist(),
                metadatas=[
                    {
                        "source": c.source,
                        "section": c.section,
                        "page_start": c.page_start,
                        "page_end": c.page_end,
                        **{f"role_{r}": True for r in c.roles},
                    }
                    for c in batch
                ],
            )

    def query(self, embedding: np.ndarray, n: int, role: str | None) -> list[Hit]:
        total = self.col.count()
        if total == 0:
            return []
        res = self.col.query(
            query_embeddings=[embedding.tolist()],
            n_results=min(n, total),
            where={f"role_{role}": True} if role else None,
            include=["documents", "metadatas", "distances", "embeddings"],
        )
        hits: list[Hit] = []
        for cid, doc, md, dist, emb in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0], res["embeddings"][0]
        ):
            chunk = Chunk(
                id=cid,
                text=doc,
                source=md["source"],
                section=md["section"],
                page_start=int(md["page_start"]),
                page_end=int(md["page_end"]),
                roles=[k[5:] for k, v in md.items() if k.startswith("role_") and v],
            )
            hits.append(Hit(chunk=chunk, score=1.0 - float(dist), embedding=np.asarray(emb, dtype=float)))
        return hits

    def delete_source(self, source: str) -> None:
        self.col.delete(where={"source": source})

    def reset(self) -> None:
        import chromadb

        client = chromadb.PersistentClient(path=self._path)
        try:
            client.delete_collection(self._collection_name)
        except Exception:
            pass
        self._col = None

    def stats(self, role_ids: list[str]) -> dict:
        per_role = {r: len(self.col.get(where={f"role_{r}": True}, include=[])["ids"]) for r in role_ids}
        return {"total_chunks": self.col.count(), "roles": per_role}
