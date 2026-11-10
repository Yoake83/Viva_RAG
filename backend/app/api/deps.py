from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.services.interview_service import InterviewService
from app.services.knowledge.embeddings import SentenceTransformerEmbedder
from app.services.knowledge.retriever import Retriever
from app.services.knowledge.store import ChromaStore
from app.services.llm import GroqLLM


@lru_cache
def get_llm():
    s = get_settings()
    return GroqLLM(s.groq_api_key, s.groq_model, s.llm_timeout_s, s.llm_max_retries, s.groq_reasoning_effort)


@lru_cache
def get_retriever() -> Retriever:
    s = get_settings()
    return Retriever(
        ChromaStore(s.chroma_dir, s.chroma_collection),
        SentenceTransformerEmbedder(s.embedding_model, s.embedding_query_prefix),
        s,
    )


def get_service(db: Session = Depends(get_db), llm=Depends(get_llm), retriever=Depends(get_retriever)) -> InterviewService:
    return InterviewService(db, llm, retriever, get_settings())
