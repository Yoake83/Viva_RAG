"""Persistence layer: sessions, questions (with full retrieval trace) and answers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    role: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16), default="interview")  # interview | practice
    status: Mapped[str] = mapped_column(String(16), default="created")  # created | in_progress | completed
    candidate_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resume_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_text: Mapped[str] = mapped_column(Text)
    resume_profile: Mapped[dict] = mapped_column(JSON)
    plan: Mapped[list] = mapped_column(JSON)
    total_questions: Mapped[int] = mapped_column(Integer)
    current_difficulty: Mapped[int] = mapped_column(Integer, default=2)
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="session", order_by="Question.order_idx", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("session_id", "order_idx", name="uq_question_order"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True)
    order_idx: Mapped[int] = mapped_column(Integer)
    plan_index: Mapped[int] = mapped_column(Integer, default=0)
    origin: Mapped[str] = mapped_column(String(16), default="role_core")  # resume | resume_gap | role_core
    topic: Mapped[str] = mapped_column(String(200))
    qtype: Mapped[str] = mapped_column(String(32))
    difficulty: Mapped[int] = mapped_column(Integer)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(Text)
    rubric: Mapped[list] = mapped_column(JSON)  # expected points, hidden until the report
    rationale: Mapped[str] = mapped_column(Text, default="")
    resume_signals: Mapped[list] = mapped_column(JSON, default=list)
    retrieval: Mapped[dict] = mapped_column(JSON)  # queries, quality, candidates, threshold
    sources: Mapped[list] = mapped_column(JSON)  # every retrieved chunk, flagged used / not used
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[InterviewSession] = relationship(back_populates="questions")
    answer: Mapped["Answer | None"] = relationship(back_populates="question", uselist=False, cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    time_taken_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eval_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | done
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth: Mapped[str | None] = mapped_column(String(16), nullable=True)
    covered_points: Mapped[list] = mapped_column(JSON, default=list)
    missed_points: Mapped[list] = mapped_column(JSON, default=list)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    question: Mapped[Question] = relationship(back_populates="answer")
