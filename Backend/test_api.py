import json

import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"


def test_health_endpoint():
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("status") == "ok"


def test_create_session_endpoint_accepts_seed_candidate():
    payload = {
        "candidate_id": "candidate-001",
        "interview_type": "technical",
        "conversation": [],
    }

    response = requests.post(f"{BASE_URL}/api/interview", json=payload, timeout=5)
    assert response.status_code == 200

    body = response.json()
    assert body.get("candidate_id") == "candidate-001"
    assert body.get("session_id")
    assert body.get("status") == "active"


def test_answer_and_report_roundtrip():
    payload = {
        "candidate_id": "candidate-001",
        "interview_type": "technical",
        "conversation": [],
    }

    create_response = requests.post(f"{BASE_URL}/api/interview", json=payload, timeout=5)
    assert create_response.status_code == 200

    session_id = create_response.json()["session_id"]

    answer_response = requests.post(
        f"{BASE_URL}/api/interview/{session_id}/answer",
        json={
            "answer": "I would design a small API using FastAPI, validate inputs, and explain trade-offs.",
            "transcript_turn": "Q1",
        },
        timeout=5,
    )
    assert answer_response.status_code == 200

    answer_body = answer_response.json()
    assert answer_body.get("session_id") == session_id
    assert answer_body.get("status") == "active"
    assert answer_body.get("conversation_count") >= 1

    report_response = requests.get(f"{BASE_URL}/api/interview/{session_id}/report", timeout=5)
    assert report_response.status_code == 200

    report_body = report_response.json()
    assert report_body.get("session_id") == session_id
    assert report_body.get("candidate_id") == "candidate-001"
    assert report_body.get("candidate_score") > 0


def test_create_session_rejects_unknown_candidate():
    payload = {
        "candidate_id": "ghost-candidate",
        "interview_type": "technical",
        "conversation": [],
    }

    response = requests.post(f"{BASE_URL}/api/interview", json=payload, timeout=5)
    assert response.status_code == 404

    detail = response.json().get("detail")
    assert detail == "Candidate not found"


def test_get_unknown_session_returns_404():
    response = requests.get(f"{BASE_URL}/api/interview/does-not-exist-session", timeout=5)
    assert response.status_code == 404


def test_answer_unknown_session_returns_404():
    response = requests.post(
        f"{BASE_URL}/api/interview/does-not-exist-session/answer",
        json={
            "answer": "This is a valid answer but the session is not available.",
            "transcript_turn": "Q1",
        },
        timeout=5,
    )
    assert response.status_code == 404


def test_report_unknown_session_returns_404():
    response = requests.get(f"{BASE_URL}/api/interview/does-not-exist-session/report", timeout=5)
    assert response.status_code == 404


def test_answer_endpoint_requires_answer_text():
    payload = {
        "candidate_id": "candidate-001",
        "interview_type": "technical",
        "conversation": [],
    }

    create_response = requests.post(f"{BASE_URL}/api/interview", json=payload, timeout=5)
    assert create_response.status_code == 200

    session_id = create_response.json()["session_id"]

    response = requests.post(
        f"{BASE_URL}/api/interview/{session_id}/answer",
        json={
            "transcript_turn": "Q1",
        },
        timeout=5,
    )
    assert response.status_code == 422


def test_rejects_malformed_json_payload():
    response = requests.post(
        f"{BASE_URL}/api/interview",
        data="{not-json}",
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    assert response.status_code in {400, 422}


def test_rejects_unsupported_get_on_answer_route():
    response = requests.get(f"{BASE_URL}/api/interview/unused-session/answer", timeout=5)
    assert response.status_code == 405


def test_rejects_unsupported_delete_on_collection_route():
    response = requests.delete(f"{BASE_URL}/api/interview", timeout=5)
    assert response.status_code == 405
