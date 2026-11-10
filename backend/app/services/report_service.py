"""Final report: deterministic statistics first, model-written narrative second (with a fallback)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.core.errors import AppError
from app.models import InterviewSession, Question
from app.services.llm import LLM

BANDS = [
    (75, "Strong", "Advance to the next round."),
    (55, "Promising", "Advance, with a focused follow-up on the weaker topics."),
    (35, "Developing", "Hold. Revisit the fundamentals below, then re-screen."),
    (0, "Early", "Not ready for this role yet. Recommend structured study first."),
]


class Narrative(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


_SYSTEM = """You write the closing assessment of a technical screening interview for a hiring reviewer.
Be specific, fair and concise. Base every statement on the supplied scores and per-question notes; do not invent evidence.
Return JSON: {"summary": 3-4 sentences, "strengths": [up to 3 short statements], "gaps": [up to 3 short statements], "next_steps": [up to 3 concrete study or interview follow-ups]}"""


def _band(score: float) -> tuple[str, str]:
    for floor, name, rec in BANDS:
        if score >= floor:
            return name, rec
    return BANDS[-1][1], BANDS[-1][2]


def _fallback_narrative(overall: float, topic_scores: list[dict]) -> Narrative:
    ranked = sorted(topic_scores, key=lambda t: t["score"], reverse=True)
    best, worst = ranked[:2], ranked[-2:] if len(ranked) > 2 else []
    return Narrative(
        summary=f"The candidate scored {overall:.0f}/100 across {len(topic_scores)} topics. "
        "This summary was generated from scores only because the language model was unavailable.",
        strengths=[f"{t['topic']} ({t['score']:.0f}/100)" for t in best],
        gaps=[f"{t['topic']} ({t['score']:.0f}/100)" for t in worst],
        next_steps=[f"Review: {t['topic']}" for t in worst],
    )


def build_report(session: InterviewSession, llm: LLM) -> dict:
    asked: list[Question] = list(session.questions)
    answered = [q for q in asked if q.answer is not None]
    scored = [q for q in answered if q.answer.score is not None]

    weight_sum = sum(q.difficulty for q in scored) or 1
    overall = round(sum(q.answer.score * q.difficulty for q in scored) / weight_sum * 10, 1) if scored else 0.0
    band, recommendation = _band(overall)

    by_topic: dict[str, list[float]] = {}
    for q in scored:
        by_topic.setdefault(q.topic, []).append(q.answer.score)
    topic_scores = [
        {"topic": t, "score": round(sum(v) / len(v) * 10, 1), "questions": len(v)} for t, v in by_topic.items()
    ]

    trajectory = [{"order": q.order_idx + 1, "difficulty": q.difficulty, "score": q.answer.score} for q in scored]

    study_map, seen = [], set()
    for q in scored:
        if q.answer.score >= 6.5:
            continue
        used = [s for s in q.sources if s.get("used")] or q.sources[:1]
        if not used:
            continue
        s = used[0]
        key = (s["source"], s["section"])
        if key not in seen:
            seen.add(key)
            study_map.append(
                {"topic": q.topic, "source": s["source"], "section": s["section"],
                 "page_start": s["page_start"], "page_end": s["page_end"]}
            )

    chunk_ids = {s["chunk_id"] for q in asked for s in q.sources if s.get("used")}
    sections = {(s["source"], s["section"]) for q in asked for s in q.sources if s.get("used")}
    times = [q.answer.time_taken_sec for q in answered if q.answer.time_taken_sec is not None]
    grounding = {"high": 0, "medium": 0, "low": 0}
    for q in asked:
        grounding[q.retrieval.get("quality", "low")] = grounding.get(q.retrieval.get("quality", "low"), 0) + 1

    stats = {
        "questions_asked": len(asked),
        "answered": len(answered),
        "avg_time_sec": round(sum(times) / len(times)) if times else None,
        "chunks_used": len(chunk_ids),
        "sections_covered": len(sections),
        "grounding": grounding,
        "resume_anchored": sum(1 for q in asked if q.origin == "resume"),
        "gap_probes": sum(1 for q in asked if q.origin == "resume_gap"),
        "follow_ups": sum(1 for q in asked if q.is_follow_up),
        "ended_early": len(answered) < session.total_questions,
    }

    notes = [
        {"topic": q.topic, "difficulty": q.difficulty, "score": q.answer.score, "gaps": q.answer.gaps[:2],
         "strengths": q.answer.strengths[:2]}
        for q in scored
    ]
    try:
        narrative = llm.complete_json(
            task="report",
            system=_SYSTEM,
            user=f"Role: {session.role}\nOverall score: {overall}/100 ({band})\n"
                 f"Per-question notes: {json.dumps(notes, ensure_ascii=False)}",
            schema=Narrative,
            temperature=0.3,
            max_tokens=900,
        )
    except AppError:
        narrative = _fallback_narrative(overall, topic_scores)

    return {
        "overall_score": overall,
        "band": band,
        "recommendation": recommendation,
        "summary": narrative.summary,
        "strengths": narrative.strengths[:3],
        "gaps": narrative.gaps[:3],
        "next_steps": narrative.next_steps[:3],
        "topic_scores": topic_scores,
        "trajectory": trajectory,
        "study_map": study_map,
        "stats": stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
