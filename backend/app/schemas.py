"""API response/request models."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.services.evaluator import Evaluation
from app.services.planner import TopicPlan
from app.services.resume_parser import ResumeProfile


class SourceOut(BaseModel):
    chunk_id: str
    source: str
    section: str
    page_start: int
    page_end: int
    score: float
    excerpt: str
    used: bool


class RetrievalOut(BaseModel):
    queries: list[str] = []
    quality: str = "low"
    candidates: int = 0
    threshold: float = 0.0


class AnswerOut(BaseModel):
    text: str
    time_taken_sec: int | None
    submitted_at: datetime
    eval_status: str
    evaluation: Evaluation | None = None  # hidden in interview mode until the report


class QuestionOut(BaseModel):
    id: str
    order: int
    topic: str
    qtype: str
    difficulty: int
    difficulty_label: str
    text: str
    rationale: str
    is_follow_up: bool
    resume_signals: list[str]
    retrieval: RetrievalOut
    sources: list[SourceOut]
    rubric: list[str] | None = None
    answer: AnswerOut | None = None


class SessionOut(BaseModel):
    id: str
    role: str
    role_label: str
    mode: str
    status: str
    candidate_name: str | None
    profile: ResumeProfile
    plan: list[TopicPlan]
    total_questions: int
    answered: int
    current_difficulty: int
    difficulty_label: str
    created_at: datetime
    completed_at: datetime | None
    questions: list[QuestionOut]


class AnswerIn(BaseModel):
    question_id: str
    answer: str = Field(min_length=1)
    time_taken_sec: int | None = Field(default=None, ge=0, le=86400)


class AnswerSubmitOut(BaseModel):
    question_id: str
    answer: AnswerOut
    answered_count: int
    total_questions: int
    finished: bool


class RoleOut(BaseModel):
    id: str
    label: str
    tagline: str
    description: str


class KnowledgeStatus(BaseModel):
    ready: bool
    total_chunks: int
    roles: dict[str, int]


ReportOut = dict[str, Any]
