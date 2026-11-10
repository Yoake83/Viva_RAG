from __future__ import annotations

from typing import Protocol

import numpy as np


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """Local embedding model (no API cost, deterministic). Vectors are L2-normalised so dot product == cosine."""

    def __init__(self, model_name: str, query_prefix: str = ""):
        self._model_name = model_name
        self._query_prefix = query_prefix
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self._load().encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=len(texts) > 200)
        )

    def embed_query(self, text: str) -> np.ndarray:
        return np.asarray(self._load().encode([self._query_prefix + text], normalize_embeddings=True)[0])
