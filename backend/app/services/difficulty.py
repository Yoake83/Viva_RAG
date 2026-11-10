"""Adaptive difficulty on a 1-5 scale, seeded from the resume and adjusted after every scored answer."""
from __future__ import annotations

from app.services.resume_parser import ResumeProfile

LABELS = {1: "Foundational", 2: "Core", 3: "Applied", 4: "Advanced", 5: "Expert"}
DESCRIPTIONS = {
    1: "Definitions and intuition. A student who read the chapter once should manage.",
    2: "Explain the mechanism and why it works, with a simple example.",
    3: "Apply the concept to a concrete situation and discuss trade-offs.",
    4: "Reason about failure modes, edge cases and interactions between concepts.",
    5: "Open-ended design or diagnosis that needs synthesis and justified decisions.",
}


def initial_difficulty(profile: ResumeProfile) -> int:
    base = {"student": 2, "junior": 2, "mid": 3, "senior": 4}[profile.seniority]
    adjust = {"none": -1, "basic": 0, "moderate": 0, "strong": 1}[profile.ml_exposure]
    return max(1, min(5, base + adjust))


def next_difficulty(current: int, score: float | None) -> int:
    if score is None:
        return current
    if score >= 8:
        return min(5, current + 1)
    if score <= 4:
        return max(1, current - 1)
    return current
