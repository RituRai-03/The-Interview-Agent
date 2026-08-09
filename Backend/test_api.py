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

    # Start
    start_resp = client.post("/api/interview", json={
        "sessionId": session_id,
        "candidate": candidate
    })
    assert start_resp.status_code == 200
    assert start_resp.json()["done"] is False

    # Turn 1
    t1_resp = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "I would structure the FastAPI backend with Pydantic schemas, dependency injection, and async handlers."
    })
    assert t1_resp.status_code == 200
    assert t1_resp.json()["done"] is False
    assert len(t1_resp.json()["reply"]) > 0

    # Turn 2
    t2_resp = client.post("/api/interview", json={
        "sessionId": session_id,
        "message": "To optimize database performance, I create indexes on key columns, monitor query execution plans, and use connection pooling."
    })
    assert t2_resp.status_code == 200
    assert t2_resp.json()["done"] is False

    # Turn 3 (Final turn -> completion)
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
    assert len(feedback["strengths"]) > 0
    assert len(feedback["gaps"]) > 0
    assert len(feedback["next"]) > 0


def test_candidate_personalization_across_candidates():
    # Aarav Sharma (Full-stack)
    aarav = get_candidate_by_id("candidate-001")
    res1 = client.post("/api/interview", json={"sessionId": "p-001", "candidate": aarav})
    assert res1.status_code == 200
    reply1 = res1.json()["reply"]
    assert "Aarav" in reply1 or "Full-stack" in reply1 or "FastAPI" in reply1

    # Mia Johnson (Data Engineer)
    mia = get_candidate_by_id("candidate-002")
    res2 = client.post("/api/interview", json={"sessionId": "p-002", "candidate": mia})
    assert res2.status_code == 200
    reply2 = res2.json()["reply"]
    assert "Mia" in reply2 or "Data Engineer" in reply2 or "ETL" in reply2

    # James Chen (Backend Engineer)
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
