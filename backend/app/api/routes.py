from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_retriever, get_service
from app.api.serializers import serialize_question, serialize_session
from app.config import get_settings
from app.core.errors import Conflict, ValidationFailed
from app.database import get_db
from app.roles import ROLES
from app.schemas import AnswerIn, AnswerSubmitOut, KnowledgeStatus, QuestionOut, ReportOut, RoleOut, SessionOut
from app.api.serializers import serialize_answer
from app.services.interview_service import InterviewService
from app.services.resume_parser import extract_text, normalise_resume_text

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "llm_configured": bool(settings.groq_api_key)}


@router.get("/roles", response_model=list[RoleOut])
def list_roles():
    return [RoleOut(id=r.id, label=r.label, tagline=r.tagline, description=r.description) for r in ROLES.values()]


@router.get("/knowledge/status", response_model=KnowledgeStatus)
def knowledge_status(retriever=Depends(get_retriever)):
    try:
        stats = retriever.store.stats(list(ROLES))
    except Exception as exc:  # vector store not initialised yet
        log.warning("knowledge status unavailable: %s", exc)
        stats = {"total_chunks": 0, "roles": {r: 0 for r in ROLES}}
    return KnowledgeStatus(ready=stats["total_chunks"] > 0, **stats)


@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(
    role: str = Form(...),
    mode: str = Form("interview"),
    candidate_name: str | None = Form(None),
    resume_text: str | None = Form(None),
    total_questions: int | None = Form(None),
    resume: UploadFile | None = File(None),
    service: InterviewService = Depends(get_service),
):
    settings = get_settings()
    filename = None
    if resume is not None and resume.filename:
        limit = settings.max_resume_mb * 1024 * 1024
        data = resume.file.read(limit + 1)
        if len(data) > limit:
            raise ValidationFailed(f"Resume is larger than {settings.max_resume_mb} MB.", code="file_too_large")
        text_content = extract_text(resume.filename, data)
        filename = resume.filename
    elif resume_text and resume_text.strip():
        text_content = normalise_resume_text(resume_text)
    else:
        raise ValidationFailed("Upload a resume or paste its text.", code="resume_required")

    name = (candidate_name or "").strip()[:80] or None
    session = service.create_session(
        role_id=role, mode=mode, resume_text=text_content, resume_filename=filename,
        candidate_name=name, total_questions=total_questions,
    )
    return serialize_session(session)


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: str, service: InterviewService = Depends(get_service)):
    return serialize_session(service.get_session(session_id))


@router.post("/sessions/{session_id}/questions/next", response_model=QuestionOut)
def next_question(session_id: str, service: InterviewService = Depends(get_service)):
    question = service.next_question(session_id)
    session = service.get_session(session_id)
    return serialize_question(question, reveal=session.mode == "practice")


@router.post("/sessions/{session_id}/answers", response_model=AnswerSubmitOut)
def submit_answer(session_id: str, body: AnswerIn, service: InterviewService = Depends(get_service)):
    answer, answered, total = service.submit_answer(session_id, body.question_id, body.answer, body.time_taken_sec)
    session = service.get_session(session_id)
    return AnswerSubmitOut(
        question_id=body.question_id,
        answer=serialize_answer(answer, reveal=session.mode == "practice"),
        answered_count=answered,
        total_questions=total,
        finished=answered >= total,
    )


@router.post("/sessions/{session_id}/complete", response_model=ReportOut)
def complete_session(session_id: str, service: InterviewService = Depends(get_service)):
    return service.complete(session_id)


@router.get("/sessions/{session_id}/report", response_model=ReportOut)
def get_report(session_id: str, service: InterviewService = Depends(get_service)):
    session = service.get_session(session_id)
    if session.status != "completed" or not session.report:
        raise Conflict("The report is not ready. Complete the interview first.", code="report_not_ready")
    return session.report
