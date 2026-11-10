"""Grounded question generation: the model sees only the retrieved passages, the plan and the candidate."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.services.difficulty import DESCRIPTIONS, LABELS
from app.services.knowledge.retriever import RetrievedChunk
from app.services.llm import LLM
from app.services.resume_parser import ResumeProfile

QTYPE_HELP = {
    "conceptual": "asks the candidate to explain a concept and why it works",
    "applied_scenario": "puts the candidate in a realistic situation and asks what they would do and why",
    "project_deep_dive": "anchors on a specific project from the resume and probes a concept through it",
    "tradeoff": "asks the candidate to compare two approaches and justify a choice",
    "debugging": "describes a symptom (for example a train/validation gap) and asks for a diagnosis",
}


class GeneratedQuestion(BaseModel):
    question: str = Field(min_length=15)
    expected_points: list[str] = Field(min_length=2)
    rationale: str = ""
    used_chunks: list[str] = Field(default_factory=list)


@dataclass
class FollowUp:
    previous_question: str
    previous_answer: str
    gaps: list[str]


_SYSTEM = """You are a senior interviewer writing ONE question for a candidate.
Ground the question ONLY in the numbered reference passages. Never mention "the passages", "the textbook" or "the excerpt" to the candidate.
Requirements:
- Match the requested difficulty and question type exactly.
- Use the candidate's background where it fits naturally (name their project or technology), but do not force it.
- Not a yes/no question, not a definition lookup unless difficulty is 1, and not copied sentence-for-sentence from the passages.
- Answerable in roughly 3-6 sentences.
- "expected_points": 3-5 specific points a strong answer would contain, drawn from the passages (hidden from the candidate; used for grading).
- "rationale": 1-2 sentences, addressed to a reviewer, explaining why this question suits this candidate.
- "used_chunks": labels of the passages you actually relied on, e.g. ["C1","C3"].
Return JSON: {"question": str, "expected_points": [str], "rationale": str, "used_chunks": [str]}"""


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _too_similar(question: str, history: list[str], threshold: float = 0.6) -> bool:
    a = _tokens(question)
    for prev in history:
        b = _tokens(prev)
        if a and b and len(a & b) / len(a | b) >= threshold:
            return True
    return False


def format_passages(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, rc in enumerate(chunks, start=1):
        c = rc.chunk
        blocks.append(f'[C{i}] ({c.source}, "{c.section}", pp. {c.page_start}-{c.page_end})\n{c.text}')
    return "\n\n".join(blocks)


def generate_question(
    *,
    role_label: str,
    profile: ResumeProfile,
    topic: str,
    qtype: str,
    difficulty: int,
    chunks: list[RetrievedChunk],
    history: list[str],
    follow_up: FollowUp | None,
    llm: LLM,
) -> GeneratedQuestion:
    candidate = {
        "headline": profile.headline,
        "seniority": profile.seniority,
        "skills": profile.skills[:10],
        "technologies": profile.technologies[:12],
        "projects": [p.model_dump() for p in profile.projects[:4]],
    }
    parts = [
        f"Role: {role_label}",
        f"Topic: {topic}",
        f"Difficulty {difficulty}/5 ({LABELS[difficulty]}): {DESCRIPTIONS[difficulty]}",
        f"Question type: {qtype}, which {QTYPE_HELP.get(qtype, QTYPE_HELP['conceptual'])}",
        f"Candidate: {json.dumps(candidate, ensure_ascii=False)}",
    ]
    if follow_up:
        parts.append(
            "This is a FOLLOW-UP. The candidate struggled with the previous question.\n"
            f"Previous question: {follow_up.previous_question}\n"
            f"Previous answer: {follow_up.previous_answer[:800]}\n"
            f"Gaps noticed: {'; '.join(follow_up.gaps) or 'unclear understanding'}\n"
            "Ask a more focused, simpler question that targets the gap directly."
        )
    if history:
        parts.append("Already asked (do not repeat or paraphrase):\n- " + "\n- ".join(h[:200] for h in history))
    parts.append("Reference passages:\n" + format_passages(chunks))
    user = "\n\n".join(parts)

    result = llm.complete_json(
        task="question", system=_SYSTEM, user=user, schema=GeneratedQuestion, temperature=0.6, max_tokens=900
    )
    if _too_similar(result.question, history):
        result = llm.complete_json(
            task="question",
            system=_SYSTEM,
            user=user + "\n\nYour previous attempt was too similar to an earlier question. Take a clearly different angle.",
            schema=GeneratedQuestion,
            temperature=0.9,
            max_tokens=900,
        )
    return result
