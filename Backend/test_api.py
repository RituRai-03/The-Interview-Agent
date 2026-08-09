import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Put Backend directory in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import app
from data_loader import get_candidate_by_id

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"


def test_candidate_verification_endpoint_success():
    resp = client.get("/api/candidates/candidate-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["candidate"]["name"] == "Aarav Sharma"


def test_candidate_verification_endpoint_invalid_id():
    resp = client.get("/api/candidates/candidate-999")
    assert resp.status_code == 404


def test_server_side_authoritative_candidate_overrides_fake_data():
    payload = {
        "sessionId": "auth-test-001",
        "candidate": {
            "id": "candidate-001",
            "name": "Fake Malicious Name",
            "role": "Fake Job Role"
        }
    }
    resp = client.post("/api/interview", json=payload)
    assert resp.status_code == 200

    sess_resp = client.get("/api/interview/auth-test-001")
    assert sess_resp.status_code == 200
    cand = sess_resp.json()["candidate"]
    assert cand["name"] == "Aarav Sharma"
    assert cand["role"] == "Full-stack Engineer"


def test_cannot_switch_candidate_mid_session():
    start_resp = client.post("/api/interview", json={
        "sessionId": "switch-test-001",
        "candidate_id": "candidate-001"
    })
    assert start_resp.status_code == 200

    switch_resp = client.post("/api/interview", json={
        "sessionId": "switch-test-001",
        "candidate_id": "candidate-002",
        "message": "Attempting candidate switch"
    })
    assert switch_resp.status_code == 400
    assert "Cannot change candidate" in switch_resp.json()["detail"]


def test_answer_quality_punctuation_only_no_praise_no_advancement():
    start_resp = client.post("/api/interview", json={
        "sessionId": "punct-test-001",
        "candidate_id": "candidate-001"
    })
    assert start_resp.status_code == 200

    punct_resp = client.post("/api/interview", json={
        "sessionId": "punct-test-001",
        "message": "."
    })
    assert punct_resp.status_code == 200
    reply = punct_resp.json()["reply"]
    assert "Excellent insights" not in reply
    assert "Great answer" not in reply
    assert punct_resp.json()["done"] is False
    assert "come through" in reply or "approach" in reply


def test_answer_quality_uncertainty_no_praise():
    start_resp = client.post("/api/interview", json={
        "sessionId": "uncert-test-001",
        "candidate_id": "candidate-001"
    })
    assert start_resp.status_code == 200

    uncert_resp = client.post("/api/interview", json={
        "sessionId": "uncert-test-001",
        "message": "I don't know"
    })
    assert uncert_resp.status_code == 200
    reply = uncert_resp.json()["reply"]
    assert "Excellent insights" not in reply
    assert "Great answer" not in reply
    assert uncert_resp.json()["done"] is False
    assert "simpler angle" in reply or "fine" in reply or "principles" in reply


def test_answer_quality_very_short_clarification():
    start_resp = client.post("/api/interview", json={
        "sessionId": "short-test-001",
        "candidate_id": "candidate-001"
    })
    assert start_resp.status_code == 200

    short_resp = client.post("/api/interview", json={
        "sessionId": "short-test-001",
        "message": "Python"
    })
    assert short_resp.status_code == 200
    reply = short_resp.json()["reply"]
    assert "Excellent insights" not in reply
    assert "Python" in reply
    assert "advantage" in reply or "suitable" in reply


def test_meaningful_answer_references_concepts_and_advances():
    start_resp = client.post("/api/interview", json={
        "sessionId": "strong-test-001",
        "candidate_id": "candidate-001"
    })
    assert start_resp.status_code == 200

    strong_resp = client.post("/api/interview", json={
        "sessionId": "strong-test-001",
        "message": "I would use PostgreSQL with indexes on high-cardinality columns and connection pooling for scaling."
    })
    assert strong_resp.status_code == 200
    reply = strong_resp.json()["reply"]
    assert "index" in reply.lower() or "database" in reply.lower() or "growth" in reply.lower()


def test_start_interview_technical_spec():
    candidate = get_candidate_by_id("candidate-001")
    assert candidate is not None

    payload = {
        "sessionId": "test-spec-session-001",
        "candidate": candidate,
    }

    response = client.post("/api/interview", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert "reply" in body
    assert body.get("done") is False
    assert body.get("sessionId") == "test-spec-session-001" or body.get("session_id") == "test-spec-session-001"


def test_interview_multi_turn_flow_and_completion():
    candidate = get_candidate_by_id("candidate-001")
    session_id = "test-multi-turn-001"

    start_resp = client.post("/api/interview", json={
        "sessionId": session_id,
        "candidate": candidate
    })
    assert start_resp.status_code == 200
    assert start_resp.json()["done"] is False

    t1_resp = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "I would structure the FastAPI backend with Pydantic schemas, dependency injection, and async handlers."
    })
    assert t1_resp.status_code == 200
    assert t1_resp.json()["done"] is False

    t2_resp = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "To optimize database performance, I create indexes on key columns, monitor query execution plans, and use connection pooling."
    })
    assert t2_resp.status_code == 200
    assert t2_resp.json()["done"] is False

    t3_resp = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "For vector search and RAG architecture, I integrate FAISS embeddings index with fallback caching and batch inference."
    })
    assert t3_resp.status_code == 200
    body3 = t3_resp.json()
    assert body3["done"] is True
    assert "feedback" in body3

    feedback = body3["feedback"]
    assert isinstance(feedback.get("summary"), str)
    assert isinstance(feedback.get("strengths"), list)
    assert isinstance(feedback.get("gaps"), list)
    assert isinstance(feedback.get("next"), list)


def test_feedback_very_bad_interview_gives_no_false_praise():
    session_id = "fb-bad-001"
    start_resp = client.post("/api/interview", json={"sessionId": session_id, "candidate_id": "candidate-001"})
    assert start_resp.status_code == 200

    bad_messages = [".", "not sure", "I don't know", ".", "not sure", ".", "I don't know", "."]
    last_resp = None
    for msg in bad_messages:
        last_resp = client.post("/api/interview", json={"sessionId": session_id, "message": msg})

    assert last_resp.status_code == 200
    body = last_resp.json()
    assert body["done"] is True
    fb = body["feedback"]

    summary = fb["summary"]
    strengths = fb["strengths"]

    assert "solid domain knowledge" not in summary.lower()
    assert "effectively discussed" not in summary.lower()
    assert "clear communication" not in str(strengths).lower()
    assert "No substantial technical strengths" in strengths[0] or "insufficient" in str(strengths).lower()


def test_feedback_strong_interview_gives_evidence_based_strengths():
    session_id = "fb-strong-001"
    start_resp = client.post("/api/interview", json={"sessionId": session_id, "candidate_id": "candidate-001"})
    assert start_resp.status_code == 200

    t1 = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "I build FastAPI microservices using Pydantic schemas and dependency injection."
    })
    t2 = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "I optimize PostgreSQL queries using B-Tree indexes on high-cardinality columns and connection pooling."
    })
    t3 = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "For caching, I use Redis with TTL expiration and active cache invalidation patterns."
    })

    assert t3.status_code == 200
    body = t3.json()
    assert body["done"] is True
    fb = body["feedback"]

    summary = fb["summary"]
    strengths = fb["strengths"]

    assert "database" in summary.lower() or "caching" in summary.lower() or "api" in summary.lower() or "practical" in summary.lower()
    assert any("database" in s.lower() or "caching" in s.lower() or "api" in s.lower() or "pydantic" in s.lower() for s in strengths)


def test_two_sessions_produce_distinct_evidence_based_feedback():
    s_bad = client.post("/api/interview", json={"sessionId": "fb-compare-bad", "candidate_id": "candidate-001"})
    for msg in [".", "not sure", "I don't know", ".", "not sure", ".", "I don't know", "."]:
        bad_end = client.post("/api/interview", json={"sessionId": "fb-compare-bad", "message": msg})
    fb_bad = bad_end.json()["feedback"]

    s_good = client.post("/api/interview", json={"sessionId": "fb-compare-good", "candidate_id": "candidate-001"})
    client.post("/api/interview", json={"sessionId": "fb-compare-good", "message": "I use FastAPI with Pydantic validation."})
    client.post("/api/interview", json={"sessionId": "fb-compare-good", "message": "I use PostgreSQL with connection pooling."})
    good_end = client.post("/api/interview", json={"sessionId": "fb-compare-good", "message": "I use Redis for distributed caching."})
    fb_good = good_end.json()["message"] if "message" in good_end.json() else good_end.json()["feedback"]

    assert fb_bad["summary"] != fb_good["summary"]
    assert fb_bad["strengths"] != fb_good["strengths"]
    assert "No substantial technical strengths" in fb_bad["strengths"][0]
    assert "No substantial technical strengths" not in fb_good["strengths"][0]


def test_candidate_personalization_across_candidates():
    aarav = get_candidate_by_id("candidate-001")
    res1 = client.post("/api/interview", json={"sessionId": "p-001", "candidate": aarav})
    assert res1.status_code == 200
    reply1 = res1.json()["reply"]
    assert "Aarav" in reply1 or "Full-stack" in reply1 or "FastAPI" in reply1

    mia = get_candidate_by_id("candidate-002")
    res2 = client.post("/api/interview", json={"sessionId": "p-002", "candidate": mia})
    assert res2.status_code == 200
    reply2 = res2.json()["reply"]
    assert "Mia" in reply2 or "Data Engineer" in reply2 or "ETL" in reply2

    james = get_candidate_by_id("candidate-003")
    res3 = client.post("/api/interview", json={"sessionId": "p-003", "candidate": james})
    assert res3.status_code == 200
    reply3 = res3.json()["reply"]
    assert "James" in reply3 or "Backend" in reply3 or "microservices" in reply3 or "Go" in reply3


def test_rejects_unknown_candidate():
    payload = {
        "sessionId": "ghost-session",
        "candidate": {"id": "ghost-candidate"}
    }

    response = client.post("/api/interview", json=payload)
    assert response.status_code == 404
    assert response.json().get("detail") == "Candidate not found"


def test_unknown_session_turn_returns_404():
    response = client.post(
        "/api/interview",
        json={
            "sessionId": "non-existent-session-xyz",
            "message": "Hello?"
        }
    )
    assert response.status_code == 404


def test_legacy_answer_endpoint_roundtrip():
    candidate = get_candidate_by_id("candidate-001")
    start_resp = client.post("/api/interview", json={"sessionId": "legacy-001", "candidate": candidate})
    assert start_resp.status_code == 200

    ans_resp = client.post("/api/interview/legacy-001/answer", json={
        "answer": "Legacy test answer for roundtrip."
    })
    assert ans_resp.status_code == 200
    assert ans_resp.json()["session_id"] == "legacy-001"
