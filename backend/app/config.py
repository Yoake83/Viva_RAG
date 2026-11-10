"""All runtime configuration comes from environment variables (or backend/.env)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite:///./viva.db"

    # LLM
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_reasoning_effort: str = "low"
    llm_timeout_s: float = 45.0
    llm_max_retries: int = 2

    # RAG: ingestion
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_query_prefix: str = "Represent this sentence for searching relevant passages: "
    chroma_dir: str = str(BASE_DIR / "storage" / "chroma")
    chroma_collection: str = "ml_knowledge"
    knowledge_dir: str = str(BASE_DIR / "data" / "books")
    knowledge_manifest: str = str(BASE_DIR / "data" / "manifest.json")
    chunk_target_words: int = 220
    chunk_overlap_words: int = 40
    chunk_min_words: int = 60

    # RAG: retrieval
    retrieval_top_k: int = 4
    retrieval_fetch_k: int = 24
    retrieval_mmr_lambda: float = 0.7
    retrieval_min_score: float = 0.35

    # Interview behaviour
    questions_per_interview: int = 6
    max_follow_ups: int = 2
    follow_up_below_score: float = 4.0
    max_resume_mb: int = 5
    max_answer_chars: int = 6000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
