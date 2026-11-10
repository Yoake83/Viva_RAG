RESUME = ("Asha Verma. B.Tech Computer Science student. Built a sentiment classifier with PyTorch and BERT. "
          "Skills: Python, NLP, scikit-learn, SQL. Projects: Sentiment bot using transformers for review analysis. ") * 3


def _create(client, mode="interview"):
    return client.post("/api/sessions", data={"role": "ai_ml_engineer", "mode": mode, "resume_text": RESUME,
                                              "total_questions": "3"})


def test_full_interview_flow(client, llm):
    r = _create(client)
    assert r.status_code == 201, r.text
    s = r.json()
    sid = s["id"]
    assert s["total_questions"] == 3 and s["profile"]["seniority"] == "student" and s["questions"] == []

    for i in range(3):
        q = client.post(f"/api/sessions/{sid}/questions/next").json()
        assert q["sources"] and q["rubric"] is None  # rubric hidden in interview mode
        again = client.post(f"/api/sessions/{sid}/questions/next").json()
        assert again["id"] == q["id"]  # idempotent while unanswered
        a = client.post(f"/api/sessions/{sid}/answers",
                        json={"question_id": q["id"], "answer": "Overfitting is when a model memorises noise, fixed by regularization.",
                              "time_taken_sec": 30})
        assert a.status_code == 200, a.text
        assert a.json()["answer"]["evaluation"] is None  # hidden in interview mode
        assert a.json()["finished"] == (i == 2)

    assert client.post(f"/api/sessions/{sid}/questions/next").status_code == 409
    report = client.post(f"/api/sessions/{sid}/complete").json()
    assert report["overall_score"] == 75.0 and report["band"] == "Strong"
    assert report["stats"]["answered"] == 3 and report["topic_scores"]
    full = client.get(f"/api/sessions/{sid}").json()
    assert full["status"] == "completed" and full["questions"][0]["rubric"]
    assert full["questions"][0]["answer"]["evaluation"]["score"] == 7.5
    assert client.get(f"/api/sessions/{sid}/report").json()["overall_score"] == 75.0


def test_double_answer_and_validation_errors(client):
    sid = _create(client).json()["id"]
    q = client.post(f"/api/sessions/{sid}/questions/next").json()
    ok = client.post(f"/api/sessions/{sid}/answers", json={"question_id": q["id"], "answer": "A real answer with words."})
    assert ok.status_code == 200
    dup = client.post(f"/api/sessions/{sid}/answers", json={"question_id": q["id"], "answer": "Again."})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "already_answered"
    assert client.post("/api/sessions/nope/questions/next").json()["error"]["code"] == "session_not_found"
    assert client.post("/api/sessions", data={"role": "ai_ml_engineer"}).json()["error"]["code"] == "resume_required"
    assert client.post("/api/sessions", data={"role": "chef", "resume_text": RESUME}).json()["error"]["code"] == "unknown_role"
    assert client.get(f"/api/sessions/{sid}/report").status_code == 409


def test_weak_answer_triggers_follow_up_and_lowers_difficulty(client, llm):
    llm.score = 2.0
    sid = _create(client).json()["id"]
    q1 = client.post(f"/api/sessions/{sid}/questions/next").json()
    client.post(f"/api/sessions/{sid}/answers", json={"question_id": q1["id"], "answer": "I am not completely sure what this means."})
    q2 = client.post(f"/api/sessions/{sid}/questions/next").json()
    assert q2["is_follow_up"] and q2["difficulty"] < q1["difficulty"] and q2["topic"] == q1["topic"]


def test_practice_mode_reveals_feedback(client):
    sid = _create(client, "practice").json()["id"]
    q = client.post(f"/api/sessions/{sid}/questions/next").json()
    a = client.post(f"/api/sessions/{sid}/answers", json={"question_id": q["id"], "answer": "Some reasonable answer here."}).json()
    assert a["answer"]["evaluation"]["feedback"] == "Good start."


def test_text_resume_upload_and_short_resume_rejected(client):
    r = client.post("/api/sessions", data={"role": "ai_ml_engineer", "resume_text": "too short"})
    assert r.json()["error"]["code"] == "resume_too_short"
    files = {"resume": ("cv.txt", RESUME.encode(), "text/plain")}
    assert client.post("/api/sessions", data={"role": "data_scientist"}, files=files).status_code == 201
    bad = {"resume": ("cv.exe", b"x" * 500, "application/octet-stream")}
    assert client.post("/api/sessions", data={"role": "data_scientist"}, files=bad).json()["error"]["code"] == "unsupported_file_type"
