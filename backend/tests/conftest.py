import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["GROQ_API_KEY"] = "test-key"

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import get_llm, get_retriever  # noqa: E402
from app.main import app  # noqa: E402
from app.services.knowledge.chunking import Chunk  # noqa: E402
from app.services.knowledge.retriever import RetrievalResult, RetrievedChunk  # noqa: E402


class FakeLLM:
    def __init__(self):
        self.calls = []
        self.n = 0
        self.score = 7.5

    def complete_json(self, *, task, system, user, schema, temperature=0.4, max_tokens=1400):
        self.calls.append(task)
        if task == "resume_parse":
            data = {"candidate_name": "Asha", "headline": "ML student", "seniority": "student",
                    "ml_exposure": "moderate", "skills": ["NLP"], "technologies": ["PyTorch", "Python"],
                    "domains": [], "projects": [{"name": "Sentiment bot", "summary": "BERT classifier",
                                                 "technologies": ["PyTorch"]}], "education": ["B.Tech"]}
        elif task == "plan":
            data = {"topics": [{"topic": f"Topic {i}", "origin": "resume" if i % 2 == 0 else "resume_gap",
                                "rationale": "r", "resume_signals": ["PyTorch"], "queries": [f"query {i}"],
                                "question_type": "conceptual"} for i in range(8)]}
        elif task == "question":
            self.n += 1
            data = {"question": f"Distinct question number {self.n} about alpha{self.n} beta{self.n} gamma{self.n} delta",
                    "expected_points": ["point a", "point b", "point c"], "rationale": "because",
                    "used_chunks": ["C1"]}
        elif task == "evaluate":
            data = {"score": self.score, "depth": "adequate", "covered_points": ["point a"],
                    "missed_points": ["point c"], "strengths": ["clear"], "gaps": ["edge cases"],
                    "feedback": "Good start."}
        else:
            data = {"summary": "Solid.", "strengths": ["a"], "gaps": ["b"], "next_steps": ["c"]}
        return schema.model_validate(data)


class FakeRetriever:
    def __init__(self):
        self.calls = 0

    def retrieve(self, queries, *, role, k, exclude_ids=()):
        self.calls += 1
        chunks = [
            RetrievedChunk(Chunk(id=f"book:{i}", text=f"Passage {i} about learning. " * 20, source="Test Book",
                                 section=f"Section {i}", page_start=10 + i, page_end=11 + i, roles=[role]), 0.8 - i * 0.1)
            for i in range(3) if f"book:{i}" not in set(exclude_ids)
        ]
        return RetrievalResult(chunks, {"queries": queries, "quality": "high", "candidates": 3, "threshold": 0.35})

    class store:
        @staticmethod
        def stats(role_ids):
            return {"total_chunks": 3, "roles": {r: 3 for r in role_ids}}


@pytest.fixture()
def llm():
    return FakeLLM()


@pytest.fixture()
def client(llm):
    with TestClient(app) as c:
        app.dependency_overrides[get_llm] = lambda: llm
        app.dependency_overrides[get_retriever] = lambda: FakeRetriever()
        yield c
    app.dependency_overrides.clear()
