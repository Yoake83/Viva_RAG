"""Orchestrates the interview lifecycle: create -> question -> answer -> ... -> complete.

Pipeline per question (stored on the Question row so every step is traceable):
  plan topic + resume signals -> retrieval queries -> retrieved passages (flagged used / unused)
  -> generated question + hidden rubric -> candidate answer -> evaluation -> adapted difficulty
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.core.errors import AppError, Conflict, NotFound, ServiceUnavailable, ValidationFailed
from app.models import Answer, InterviewSession, Question
from app.roles import get_role
from app.services.difficulty import initial_difficulty, next_difficulty
from app.services.evaluator import Evaluation, evaluate_answer
from app.services.knowledge.retriever import Retriever
from app.services.llm import LLM
from app.services.planner import TopicPlan, build_plan
from app.services.question_generator import FollowUp, generate_question
from app.services.report_service import build_report
from app.services.resume_parser import ResumeProfile, parse_resume

log = logging.getLogger(__name__)
EXCERPT_CHARS = 360


class InterviewService:
    def __init__(self, db: Session, llm: LLM, retriever: Retriever, settings: Settings):
        self.db, self.llm, self.retriever, self.s = db, llm, retriever, settings

    # ---- queries -------------------------------------------------------------------------------
    def get_session(self, session_id: str) -> InterviewSession:
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .options(selectinload(InterviewSession.questions).selectinload(Question.answer))
        )
        session = self.db.execute(stmt).scalar_one_or_none()
        if not session:
            raise NotFound("Interview session not found.", code="session_not_found")
        return session

    # ---- lifecycle -----------------------------------------------------------------------------
    def create_session(
        self, *, role_id: str, mode: str, resume_text: str, resume_filename: str | None,
        candidate_name: str | None, total_questions: int | None = None,
    ) -> InterviewSession:
        role = get_role(role_id)
        if mode not in {"interview", "practice"}:
            raise ValidationFailed("mode must be 'interview' or 'practice'.", code="invalid_mode")
        n = max(3, min(10, total_questions or self.s.questions_per_interview))

        profile = parse_resume(resume_text, self.llm)
        if candidate_name:
            profile.candidate_name = candidate_name
        plan = build_plan(role, profile, n, self.llm)

        session = InterviewSession(
            role=role.id, mode=mode, status="created", candidate_name=profile.candidate_name,
            resume_filename=resume_filename, resume_text=resume_text,
            resume_profile=profile.model_dump(), plan=[t.model_dump() for t in plan],
            total_questions=len(plan), current_difficulty=initial_difficulty(profile),
        )
        self.db.add(session)
        self.db.commit()
        return self.get_session(session.id)

    def next_question(self, session_id: str) -> Question:
        session = self.get_session(session_id)
        if session.status == "completed":
            raise Conflict("This interview is already complete.", code="session_completed")
        pending = next((q for q in session.questions if q.answer is None), None)
        if pending:  # idempotent: a refresh or double click returns the same question
            return pending
        if len(session.questions) >= session.total_questions:
            raise Conflict("All questions are answered. Complete the interview to see the report.",
                           code="interview_finished")

        role = get_role(session.role)
        profile = ResumeProfile.model_validate(session.resume_profile)
        plan = [TopicPlan.model_validate(t) for t in session.plan]
        asked = list(session.questions)

        last = asked[-1] if asked else None
        follow_up_ctx: FollowUp | None = None
        is_follow_up = False
        if (
            last and last.answer and last.answer.score is not None
            and last.answer.score <= self.s.follow_up_below_score
            and not last.is_follow_up
            and sum(q.is_follow_up for q in asked) < self.s.max_follow_ups
        ):
            is_follow_up = True
            plan_index = last.plan_index
            follow_up_ctx = FollowUp(last.text, last.answer.text, list(last.answer.gaps or last.answer.missed_points))
        else:
            plan_index = min(sum(1 for q in asked if not q.is_follow_up), len(plan) - 1)
        target = plan[plan_index]

        queries = list(target.queries)
        if follow_up_ctx:
            queries += [f"{target.topic} {g}" for g in follow_up_ctx.gaps[:2]]
        used_ids = {s["chunk_id"] for q in asked for s in q.sources if s.get("used")}

        result = self.retriever.retrieve(
            queries, role=role.id, k=self.s.retrieval_top_k, exclude_ids=set() if is_follow_up else used_ids
        )
        if not result.chunks and used_ids:
            result = self.retriever.retrieve(queries, role=role.id, k=self.s.retrieval_top_k)
        if not result.chunks:
            raise ServiceUnavailable(
                "The knowledge base has no content for this role yet. Run `python -m app.cli ingest` in the backend.",
                code="knowledge_base_empty",
            )

        difficulty = session.current_difficulty
        qtype = "conceptual" if is_follow_up else target.question_type
        gq = generate_question(
            role_label=role.label, profile=profile, topic=target.topic, qtype=qtype, difficulty=difficulty,
            chunks=result.chunks, history=[q.text for q in asked], follow_up=follow_up_ctx, llm=self.llm,
        )

        labels = {f"C{i}": i - 1 for i in range(1, len(result.chunks) + 1)}
        used_idx = {labels[l] for l in gq.used_chunks if l in labels} or {0, 1} & set(range(len(result.chunks)))
        sources = [
            {
                "chunk_id": rc.chunk.id, "source": rc.chunk.source, "section": rc.chunk.section,
                "page_start": rc.chunk.page_start, "page_end": rc.chunk.page_end,
                "score": round(rc.score, 3), "text": rc.chunk.text, "used": i in used_idx,
            }
            for i, rc in enumerate(result.chunks)
        ]
        signals = list(target.resume_signals)
        if follow_up_ctx and follow_up_ctx.gaps:
            signals = [f"Gap in previous answer: {follow_up_ctx.gaps[0]}"]

        question = Question(
            session_id=session.id, order_idx=len(asked), plan_index=plan_index, origin=target.origin,
            topic=target.topic, qtype=qtype, difficulty=difficulty, is_follow_up=is_follow_up,
            text=gq.question.strip(), rubric=gq.expected_points, rationale=gq.rationale,
            resume_signals=signals, retrieval=result.meta, sources=sources,
        )
        session.status = "in_progress"
        self.db.add(question)
        try:
            self.db.commit()
        except IntegrityError:  # two concurrent requests raced; hand back the winner
            self.db.rollback()
            session = self.get_session(session_id)
            pending = next((q for q in session.questions if q.answer is None), None)
            if pending:
                return pending
            raise
        return question

    def submit_answer(self, session_id: str, question_id: str, text: str, time_taken_sec: int | None):
        session = self.get_session(session_id)
        if session.status == "completed":
            raise Conflict("This interview is already complete.", code="session_completed")
        question = next((q for q in session.questions if q.id == question_id), None)
        if not question:
            raise NotFound("That question does not belong to this interview.", code="question_not_found")
        if question.answer is not None:
            raise Conflict("This question has already been answered.", code="already_answered")
        text = text.strip()
        if not text:
            raise ValidationFailed("Write an answer before submitting.", code="empty_answer")
        if len(text) > self.s.max_answer_chars:
            raise ValidationFailed(f"Answers are limited to {self.s.max_answer_chars} characters.", code="answer_too_long")

        answer = Answer(question_id=question.id, text=text, time_taken_sec=time_taken_sec, eval_status="pending")
        self.db.add(answer)
        self.db.commit()  # persist the response first so an LLM outage never loses it

        self._evaluate(question, answer)
        session.current_difficulty = next_difficulty(session.current_difficulty, answer.score)
        self.db.commit()

        answered = sum(1 for q in session.questions if q.answer is not None or q.id == question.id)
        return answer, answered, session.total_questions

    def complete(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if session.report and session.status == "completed":
            return session.report
        answered = [q for q in session.questions if q.answer is not None]
        if not answered:
            raise Conflict("Answer at least one question before finishing.", code="no_answers")
        for q in answered:
            if q.answer.eval_status != "done":
                self._evaluate(q, q.answer)
        session.report = build_report(session, self.llm)
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        return session.report

    # ---- internals -----------------------------------------------------------------------------
    def _evaluate(self, question: Question, answer: Answer) -> None:
        passages = [s["text"] for s in question.sources if s.get("used")] or [s["text"] for s in question.sources[:2]]
        try:
            ev: Evaluation = evaluate_answer(
                question=question.text, rubric=list(question.rubric), passages=passages,
                answer=answer.text, difficulty=question.difficulty, llm=self.llm,
            )
        except AppError as exc:
            log.warning("evaluation deferred for question %s: %s", question.id, exc.code)
            answer.eval_status = "pending"
            return
        answer.score, answer.depth, answer.eval_status = ev.score, ev.depth, "done"
        answer.covered_points, answer.missed_points = ev.covered_points, ev.missed_points
        answer.strengths, answer.gaps, answer.feedback = ev.strengths, ev.gaps, ev.feedback
