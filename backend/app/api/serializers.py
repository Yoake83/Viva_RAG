from __future__ import annotations

from app.models import Answer, InterviewSession, Question
from app.roles import ROLES
from app.schemas import AnswerOut, QuestionOut, RetrievalOut, SessionOut, SourceOut
from app.services.difficulty import LABELS
from app.services.evaluator import Evaluation
from app.services.planner import TopicPlan
from app.services.resume_parser import ResumeProfile

EXCERPT_CHARS = 360


def _excerpt(text: str) -> str:
    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "..."


def serialize_answer(a: Answer, reveal: bool) -> AnswerOut:
    evaluation = None
    if reveal and a.eval_status == "done" and a.score is not None:
        evaluation = Evaluation(
            score=a.score, depth=a.depth or "adequate", covered_points=a.covered_points or [],
            missed_points=a.missed_points or [], strengths=a.strengths or [], gaps=a.gaps or [],
            feedback=a.feedback or "",
        )
    return AnswerOut(
        text=a.text, time_taken_sec=a.time_taken_sec, submitted_at=a.created_at,
        eval_status=a.eval_status, evaluation=evaluation,
    )


def serialize_question(q: Question, reveal: bool) -> QuestionOut:
    return QuestionOut(
        id=q.id, order=q.order_idx, topic=q.topic, qtype=q.qtype, difficulty=q.difficulty,
        difficulty_label=LABELS[q.difficulty], text=q.text, rationale=q.rationale, is_follow_up=q.is_follow_up,
        resume_signals=q.resume_signals or [], retrieval=RetrievalOut(**(q.retrieval or {})),
        sources=[SourceOut(**{**s, "excerpt": _excerpt(s["text"])}) for s in q.sources],
        rubric=list(q.rubric) if reveal else None,
        answer=serialize_answer(q.answer, reveal) if q.answer else None,
    )


def serialize_session(s: InterviewSession) -> SessionOut:
    reveal = s.mode == "practice" or s.status == "completed"
    role = ROLES.get(s.role)
    return SessionOut(
        id=s.id, role=s.role, role_label=role.label if role else s.role, mode=s.mode, status=s.status,
        candidate_name=s.candidate_name, profile=ResumeProfile.model_validate(s.resume_profile),
        plan=[TopicPlan.model_validate(t) for t in s.plan], total_questions=s.total_questions,
        answered=sum(1 for q in s.questions if q.answer is not None), current_difficulty=s.current_difficulty,
        difficulty_label=LABELS[s.current_difficulty], created_at=s.created_at, completed_at=s.completed_at,
        questions=[serialize_question(q, reveal) for q in s.questions],
    )
