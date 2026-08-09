import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from data_loader import get_candidate_by_id, get_curriculum, get_curriculum_requirements, parse_bootstrap_payload
from database import create_session, get_report, get_session, init_db, insert_report, insert_turn, list_sessions, session_exists, update_session

BASE_DIR = Path(__file__).resolve().parent
SESSION_STORE_PATH = BASE_DIR / "sessions.json"

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(title="The Interview Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, dict[str, Any]] = {}


def load_sessions_from_disk() -> dict[str, dict[str, Any]]:
    if not SESSION_STORE_PATH.exists():
        SESSION_STORE_PATH.write_text("{}", encoding="utf-8")

    try:
        with SESSION_STORE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}

    if not isinstance(data, dict):
        return {}

    return data


def persist_sessions_to_disk() -> None:
    with SESSION_STORE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(sessions, handle, indent=2)


init_db()
sessions = load_sessions_from_disk()

try:
    from google import genai

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    if api_key:
        gemini_client = genai.Client(api_key=api_key)
    else:
        gemini_client = None
except Exception:
    gemini_client = None


class InterviewRequest(BaseModel):
    candidate_id: str = Field(..., description="Candidate identifier")
    interview_type: str = Field("technical", description="Interview mode")
    conversation: list[dict[str, Any]] | None = Field(default_factory=list)


class InterviewAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, description="Candidate response to the current question")
    transcript_turn: str | None = Field(default=None, description="Optional label for question/answer turn")


class InterviewResponse(BaseModel):
    session_id: str
    candidate_id: str
    candidate: dict[str, Any]
    curriculum: dict[str, Any]
    status: str
    current_question: str | None = None
    reply: str | None = None
    done: bool = False
    created_at: str


class InterviewAnswerResponse(BaseModel):
    session_id: str
    status: str
    current_question: str | None = None
    reply: str | None = None
    done: bool = False
    evaluation: dict[str, Any]
    conversation_count: int


class InterviewSessionState(BaseModel):
    session_id: str
    candidate_id: str
    candidate: dict[str, Any]
    curriculum: dict[str, Any]
    requirements: dict[str, Any]
    interview_type: str
    conversation: list[dict[str, Any]]
    created_at: str
    status: str
    current_question: str | None = None


class InterviewReportResponse(BaseModel):
    session_id: str
    candidate_id: str
    candidate_name: str
    interview_type: str
    candidate_score: float
    curriculum_progress: float
    required_module_coverage: list[str]
    recommended_next_focus: str
    question_count: int
    answer_count: int
    conversation_summary: str


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/interview")
def list_interview_sessions() -> dict[str, Any]:
    session_items = list_sessions()

    return {
        "count": len(session_items),
        "sessions": session_items,
    }


@app.get("/api/interview/{session_id}", response_model=InterviewSessionState)
def get_interview_session(session_id: str) -> InterviewSessionState:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return InterviewSessionState(**session)


@app.get("/api/interview/{session_id}/report", response_model=InterviewReportResponse)
def get_interview_report(session_id: str) -> InterviewReportResponse:
    if not session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    existing_report = get_report(session_id)
    if existing_report:
        return InterviewReportResponse(**existing_report)

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    candidate = session.get("candidate", {}) or {}
    candidate_metrics = candidate.get("metrics", {}) or {}
    requirements = session.get("requirements", {}) or {}
    curriculum = session.get("curriculum", {}) or {}

    required_modules = requirements.get("required_modules", []) or []
    conversation = session.get("conversation", []) or []
    answers = [item for item in conversation if isinstance(item, dict) and item.get("answer")]

    technical_score = candidate_metrics.get("technical_score", 0)
    communication_score = candidate_metrics.get("communication_score", 0)
    problem_solving_score = candidate_metrics.get("problem_solving_score", 0)
    project_completion = candidate_metrics.get("project_completion", 0)

    normalized_scores = [technical_score, communication_score, problem_solving_score, project_completion]
    average_score = sum(normalized_scores) / len(normalized_scores) if normalized_scores else 0

    coverage = []
    for module in required_modules:
        module_lower = module.lower()
        if any(module_lower in str(item).lower() for item in conversation):
            coverage.append(module)

    coverage_ratio = (len(coverage) / len(required_modules)) if required_modules else 0
    curriculum_progress = round(min(100.0, coverage_ratio * 100 + (average_score / 100) * 50), 2)

    report = InterviewReportResponse(
        session_id=session_id,
        candidate_id=session.get("candidate_id", ""),
        candidate_name=candidate.get("name", "Unknown Candidate"),
        interview_type=session.get("interview_type", "technical"),
        candidate_score=round(average_score, 2),
        curriculum_progress=curriculum_progress,
        required_module_coverage=coverage,
        recommended_next_focus=requirements.get("suggested_next_topic") or curriculum.get("title") or "technical depth",
        question_count=len([item for item in conversation if item.get("question")]),
        answer_count=len(answers),
        conversation_summary=f"Completed {len(answers)} answer(s) across {len(conversation)} conversation turn(s)."
    )

    insert_report(
        session_id=session_id,
        report=report.model_dump(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return report


@app.post("/api/interview", response_model=InterviewResponse)
def create_interview_session(payload: InterviewRequest) -> InterviewResponse:
    bootstrap = parse_bootstrap_payload()
    candidate = next((item for item in bootstrap["candidates"] if item.get("id") == payload.candidate_id), None)

    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    session_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    curriculum = bootstrap.get("curriculum", {})
    requirements = bootstrap.get("requirements", {})

    current_question = None
    try:
        current_question = generate_interview_question(candidate, curriculum, requirements)
    except Exception:
        current_question = "Can you walk me through a problem you solved recently and explain the trade-offs you considered?"

    session_payload = {
        "session_id": session_id,
        "candidate_id": payload.candidate_id,
        "candidate": candidate,
        "curriculum": curriculum,
        "requirements": requirements,
        "interview_type": payload.interview_type,
        "conversation": payload.conversation or [],
        "created_at": created_at,
        "status": "active",
        "current_question": current_question,
    }

    sessions[session_id] = session_payload
    persist_sessions_to_disk()
    create_session(session_id, payload.candidate_id, payload.interview_type, session_payload, created_at)

    return InterviewResponse(
        session_id=session_id,
        candidate_id=payload.candidate_id,
        candidate=candidate,
        curriculum=curriculum,
        status="active",
        current_question=current_question,
        reply=current_question,
        done=False,
        created_at=created_at,
    )


@app.post("/api/interview/{session_id}/answer", response_model=InterviewAnswerResponse)
def answer_interview_question(session_id: str, payload: InterviewAnswerRequest) -> InterviewAnswerResponse:
    if not session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    conversation = session.get("conversation", []) or []
    question = session.get("current_question")

    turn = {
        "type": "candidate_answer",
        "question": question,
        "answer": payload.answer,
        "transcript_turn": payload.transcript_turn or "candidate_answer",
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }
    conversation.append(turn)

    candidate = session.get("candidate", {})
    metrics = candidate.get("metrics", {}) or {}
    skills = candidate.get("skills", []) or []

    answer_text = payload.answer.strip()
    response_quality = 0.5
    if len(answer_text) > 60:
        response_quality = min(0.95, response_quality + 0.2)
    if any(keyword in answer_text.lower() for keyword in ["design", "architecture", "scale", "api", "database", "testing"]):
        response_quality = min(1.0, response_quality + 0.2)

    evaluation = {
        "response_length": len(answer_text),
        "quality_score": round(max(0.0, min(1.0, response_quality)), 2),
        "candidate_metrics": metrics,
        "skills_seen": [skill for skill in skills if skill and skill.lower() in answer_text.lower()],
        "recommended_next_focus": "system design" if "design" in answer_text.lower() else "technical depth",
    }

    new_question = generate_interview_question(candidate, session.get("curriculum", {}), session.get("requirements", {}))

    session["conversation"] = conversation
    session["status"] = "active"
    session["current_question"] = new_question
    update_session(session_id, session)
    persist_sessions_to_disk()

    insert_turn(
        session_id=session_id,
        question=question,
        answer=payload.answer,
        transcript_turn=payload.transcript_turn or "candidate_answer",
        answered_at=datetime.now(timezone.utc).isoformat(),
    )

    return InterviewAnswerResponse(
        session_id=session_id,
        status="active",
        current_question=new_question,
        reply=new_question,
        done=False,
        evaluation=evaluation,
        conversation_count=len(conversation),
    )


def generate_interview_question(candidate: dict[str, Any], curriculum: dict[str, Any], requirements: dict[str, Any]) -> str:
    if gemini_client is None:
        return build_static_question(candidate, curriculum, requirements)

    model_name = os.getenv("OPENAI_MODEL") or "gemini-2.0-flash"

    prompt = (
        "You are a technical interviewer. Generate one concise interview question for a candidate. "
        f"Candidate profile: {candidate.get('name')}, role: {candidate.get('role')}, skills: {candidate.get('skills')}, "
        f"growth areas: {candidate.get('growth_areas')}, metrics: {candidate.get('metrics')}. "
        f"Curriculum title: {curriculum.get('title')}, focus areas: {curriculum.get('focus_areas')}, "
        f"requirements: {requirements}. "
        "Return only the interview question as plain text."
    )

    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        if hasattr(response, "text") and response.text:
            return str(response.text).strip()
        if hasattr(response, "candidates") and response.candidates:
            first = response.candidates[0]
            if hasattr(first, "content"):
                returned = getattr(first.content, "parts", None)
                if returned:
                    return str(returned[0]).strip()
        return build_static_question(candidate, curriculum, requirements)
    except Exception:
        return build_static_question(candidate, curriculum, requirements)


def build_static_question(candidate: dict[str, Any], curriculum: dict[str, Any], requirements: dict[str, Any]) -> str:
    role = candidate.get("role") or "candidate"
    focus = ", ".join(curriculum.get("focus_areas", [])) or "technical capability"
    return (
        f"For a {role} interview aligned to {focus}, explain how you would design a small production-ready solution "
        f"using the candidate's current strengths: {candidate.get('skills', [])}."
    )
