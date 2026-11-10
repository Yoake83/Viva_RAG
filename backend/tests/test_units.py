import numpy as np

from app.services.difficulty import initial_difficulty, next_difficulty
from app.services.knowledge.chunking import PageText, build_chunks, clean_text, make_section_lookup
from app.services.knowledge.retriever import mmr_select
from app.services.resume_parser import ResumeProfile, fallback_profile
from app.services.planner import fallback_plan
from app.roles import get_role

SENT = "Overfitting happens when a model memorises training noise instead of the signal. "


def test_clean_text_joins_hyphenation_and_drops_page_numbers():
    out = clean_text("A learn-\ning model\n42\n\nNext paragraph here.")
    assert "learning model" in out and "42" not in out.split()


def test_chunks_respect_sections_and_overlap():
    pages = [PageText(1, "1 Intro to Learning\n" + SENT * 40), PageText(2, "2 Regularization Basics\n" + SENT * 40)]
    lookup = make_section_lookup([], pages)
    chunks = build_chunks(pages, source="Book", lookup=lookup, target_words=100, overlap_words=20, min_words=40)
    assert chunks, "expected chunks"
    assert {c.section for c in chunks} == {"1 Intro to Learning", "2 Regularization Basics"}
    assert all(c.page_start <= c.page_end for c in chunks)
    assert len({c.id for c in chunks}) == len(chunks)


def test_toc_lookup_wins():
    pages = [PageText(1, "x"), PageText(5, "y")]
    lookup = make_section_lookup([[1, "Chapter A", 1], [1, "Chapter B", 4]], pages)
    assert lookup(2) == "Chapter A" and lookup(5) == "Chapter B"


def test_mmr_prefers_diverse_second_pick():
    embs = np.array([[1, 0], [0.99, 0.14], [0, 1]], dtype=float)
    embs /= np.linalg.norm(embs, axis=1, keepdims=True)
    rel = np.array([0.9, 0.89, 0.7])
    assert mmr_select(embs, rel, 2, 0.5) == [0, 2]
    assert mmr_select(embs, rel, 2, 1.0) == [0, 1]


def test_difficulty_adapts_and_clamps():
    assert next_difficulty(3, 9) == 4 and next_difficulty(5, 9) == 5
    assert next_difficulty(3, 2) == 2 and next_difficulty(1, 2) == 1
    assert next_difficulty(3, 6) == 3 and next_difficulty(3, None) == 3
    p = ResumeProfile(seniority="senior", ml_exposure="strong")
    assert initial_difficulty(p) == 5
    assert initial_difficulty(ResumeProfile(seniority="student", ml_exposure="none")) == 1


def test_fallback_profile_and_plan_use_resume_evidence():
    text = "B.Tech student. Built models with PyTorch and scikit-learn, deep learning projects. " * 5
    profile = fallback_profile(text)
    assert "pytorch" in profile.technologies
    plan = fallback_plan(get_role("ai_ml_engineer"), profile, 6)
    assert len(plan) == 6 and len({t.topic for t in plan}) == 6
    assert any(t.origin == "resume" for t in plan) and any(t.origin == "resume_gap" for t in plan)
