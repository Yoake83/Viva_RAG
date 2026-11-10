"""Context construction: turn (role + resume) into an ordered interview plan with retrieval queries."""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.errors import AppError
from app.roles import Role
from app.services.llm import LLM
from app.services.resume_parser import ResumeProfile

QTYPES = ("conceptual", "applied_scenario", "project_deep_dive", "tradeoff", "debugging")
Origin = Literal["resume", "resume_gap", "role_core"]


class TopicPlan(BaseModel):
    topic: str
    origin: Origin = "role_core"
    rationale: str = ""
    resume_signals: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    question_type: str = "conceptual"

    @field_validator("origin", mode="before")
    @classmethod
    def _origin(cls, v):
        return v if v in {"resume", "resume_gap", "role_core"} else "role_core"

    @field_validator("question_type", mode="before")
    @classmethod
    def _qtype(cls, v):
        return v if v in QTYPES else "conceptual"


class PlanOut(BaseModel):
    topics: list[TopicPlan]


_SYSTEM = """You design a technical interview plan for a candidate applying to a machine-learning role.
Rules:
- Every topic must be a machine-learning concept that a standard ML textbook covers, so the question can be grounded in the book.
- Anchor about 60% of topics in the candidate's real resume (technologies, projects, domains).
- Include at least one topic from the role's core syllabus that the resume gives no evidence for (origin "resume_gap").
- Order the topics: start approachable and tied to the resume, escalate, finish with an integrative topic.
- No duplicate topics.
- "queries": 2-3 retrieval queries per topic, written like textbook passage descriptions or concept keywords (not interview questions).
- "resume_signals": the specific resume facts that motivated the topic (empty list for pure role_core topics).
- "question_type": one of conceptual, applied_scenario, project_deep_dive, tradeoff, debugging. Use project_deep_dive only if the resume lists a project.
Return JSON: {"topics":[{"topic": str, "origin": "resume"|"resume_gap"|"role_core", "rationale": str, "resume_signals": [str], "queries": [str], "question_type": str}]}"""


def fallback_plan(role: Role, profile: ResumeProfile, n: int) -> list[TopicPlan]:
    blob = profile.keyword_blob()
    scored = []
    for i, area in enumerate(role.focus_areas()):
        hits = [k for k in area.keywords if k in blob]
        scored.append((len(hits), i, area, hits))
    evidenced = [t for t in sorted(scored, key=lambda t: (-t[0], t[1])) if t[0] > 0]
    others = [t for t in scored if t[0] == 0]
    chosen: list[tuple] = [(t, "resume") for t in evidenced[: max(1, round(n * 0.6))]] if evidenced else []
    gap_used = False
    for t in others:
        if len(chosen) >= n:
            break
        chosen.append((t, "role_core" if gap_used else "resume_gap"))
        gap_used = True
    for t in evidenced[len(chosen):]:
        if len(chosen) >= n:
            break
        chosen.append((t, "resume"))
    plans = []
    for (_, _, area, hits), origin in chosen[:n]:
        plans.append(
            TopicPlan(
                topic=area.topic,
                origin=origin,
                rationale="Matches evidence in the resume." if origin == "resume" else "Core syllabus area for this role.",
                resume_signals=hits[:3],
                queries=list(area.queries),
                question_type="conceptual",
            )
        )
    return plans


def build_plan(role: Role, profile: ResumeProfile, n: int, llm: LLM) -> list[TopicPlan]:
    user = (
        f"Role: {role.label}\nInterview length: {n} topics\n"
        f"Role syllabus (core areas): {', '.join(a.topic for a in role.focus_areas())}\n"
        f"Candidate profile JSON:\n{json.dumps(profile.model_dump(), ensure_ascii=False)[:6000]}"
    )
    try:
        topics = llm.complete_json(
            task="plan", system=_SYSTEM, user=user, schema=PlanOut, temperature=0.3, max_tokens=2200
        ).topics
    except AppError as exc:
        if exc.code == "llm_not_configured":
            raise
        topics = []

    plan: list[TopicPlan] = []
    seen: set[str] = set()
    for t in topics:
        key = t.topic.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        t.queries = [q.strip() for q in t.queries if q.strip()][:3] or [t.topic]
        if t.question_type == "project_deep_dive" and not profile.projects:
            t.question_type = "applied_scenario"
        plan.append(t)
    for t in fallback_plan(role, profile, n):  # pad if the model returned too few
        if len(plan) >= n:
            break
        if t.topic.strip().lower() not in seen:
            seen.add(t.topic.strip().lower())
            plan.append(t)
    return plan[:n]
