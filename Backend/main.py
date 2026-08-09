import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

# Setup Data-Parsing path import
BASE_DIR = Path(__file__).resolve().parent
DATA_PARSING_DIR = BASE_DIR.parent / "Data-Parsing"
if str(DATA_PARSING_DIR) not in sys.path:
    sys.path.insert(0, str(DATA_PARSING_DIR))

from data_loader import (
    get_candidate_by_id,
    get_curriculum,
    get_curriculum_requirements,
    parse_bootstrap_payload,
)
from database import (
    create_session,
    get_report,
    get_session,
    init_db,
    insert_report,
    insert_turn,
    list_sessions,
    session_exists,
    update_session,
)

# Optional Data-Parsing functions
try:
    from data_logic import (
        analyze_candidate,
        calculate_candidate_progress,
        format_candidate_context,
    )
    HAS_DATA_LOGIC = True
except Exception:
    HAS_DATA_LOGIC = False

import tempfile


def get_session_store_path() -> Path:
    if os.getenv("VERCEL"):
        return Path(tempfile.gettempdir()) / "sessions.json"
    try:
        test_file = BASE_DIR / ".write_test_session"
        test_file.touch()
        test_file.unlink()
        return BASE_DIR / "sessions.json"
    except Exception:
        return Path(tempfile.gettempdir()) / "sessions.json"


SESSION_STORE_PATH = get_session_store_path()

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

MAX_INTERVIEW_TURNS = 3


# ============================================================================
# PYDANTIC MODELS (TECHNICAL SPEC COMPLIANT + HYBRID SAFE)
# ============================================================================

class FeedbackModel(BaseModel):
    summary: str
    strengths: List[str]
    gaps: List[str]
    next: List[str]


class UnifiedInterviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sessionId: Optional[str] = Field(default=None, alias="session_id")
    session_id: Optional[str] = None
    candidate: Optional[dict[str, Any]] = None
    candidate_id: Optional[str] = None
    message: Optional[str] = None
    answer: Optional[str] = None
    interview_type: str = "technical"
    conversation: Optional[list[dict[str, Any]]] = None


class UnifiedInterviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reply: str
    done: bool = False
    feedback: Optional[FeedbackModel] = None
    sessionId: Optional[str] = None
    session_id: Optional[str] = None
    candidate_id: Optional[str] = None
    status: Optional[str] = None


class InterviewAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, description="Candidate response to the current question")
    transcript_turn: Optional[str] = Field(default=None, description="Optional label for question/answer turn")


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
    current_question: Optional[str] = None


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


# ============================================================================
# API ENDPOINTS
# ============================================================================

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
    session = get_session(session_id) or sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return InterviewSessionState(**session)


@app.get("/api/interview/{session_id}/report", response_model=InterviewReportResponse)
def get_interview_report(session_id: str) -> InterviewReportResponse:
    if not session_exists(session_id) and session_id not in sessions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    existing_report = get_report(session_id)
    if existing_report:
        return InterviewReportResponse(**existing_report)

    session = get_session(session_id) or sessions.get(session_id)
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
        question_count=len([item for item in conversation if isinstance(item, dict) and item.get("question")]),
        answer_count=len(answers),
        conversation_summary=f"Completed {len(answers)} answer(s) across {len(conversation)} conversation turn(s)."
    )

    insert_report(
        session_id=session_id,
        report=report.model_dump(),
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return report


@app.post("/api/interview", response_model=UnifiedInterviewResponse)
def handle_interview_api(payload: UnifiedInterviewRequest) -> UnifiedInterviewResponse:
    """
    REQUIRED PUBLIC INTERVIEW API CONTRACT (POST /api/interview):
    
    1. Start Request:
       {"sessionId": "abc-123", "candidate": {...}} -> {"reply": "...", "done": false}
       
    2. Turn Request:
       {"sessionId": "abc-123", "message": "..."} -> {"reply": "...", "done": false}
       
    3. Final Response:
       {"sessionId": "abc-123", "message": "..."} -> {"reply": "...", "done": true, "feedback": {...}}
    """
    req_session_id = payload.sessionId or payload.session_id
    req_message = payload.message or payload.answer

    # A) Subsequent turn in ongoing session (has sessionId + message)
    if req_session_id and req_message is not None:
        return process_interview_turn(req_session_id, req_message)

    # B) Session ID provided without candidate or message
    if req_session_id and not payload.candidate and not payload.candidate_id:
        if session_exists(req_session_id) or req_session_id in sessions:
            if req_message is not None:
                return process_interview_turn(req_session_id, req_message)
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is required for ongoing interview turn.")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # C) Initialization of a new interview session
    candidate_data = payload.candidate
    candidate_id = payload.candidate_id

    if not candidate_data and not candidate_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either candidate object/id (to start session) or sessionId + message (for conversation turn) must be provided."
        )

    if candidate_data and isinstance(candidate_data, dict):
        candidate_id = candidate_data.get("id") or candidate_id

    bootstrap = parse_bootstrap_payload()
    candidate = None
    if candidate_id:
        candidate = next((c for c in bootstrap["candidates"] if c.get("id") == candidate_id), None)

    if not candidate and candidate_data and isinstance(candidate_data, dict):
        if candidate_data.get("name") and candidate_data.get("role"):
            candidate = candidate_data

    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    session_id = req_session_id or str(uuid.uuid4())
    return start_new_interview_session(session_id, candidate, payload.interview_type)


@app.post("/api/interview/{session_id}/answer")
def answer_interview_question_legacy(session_id: str, payload: InterviewAnswerRequest) -> dict[str, Any]:
    """Helper route for legacy API callers."""
    res = process_interview_turn(session_id, payload.answer)
    session = get_session(session_id) or sessions.get(session_id) or {}
    conv = session.get("conversation", [])
    
    return {
        "session_id": session_id,
        "status": session.get("status", "active"),
        "current_question": res.reply,
        "reply": res.reply,
        "done": res.done,
        "evaluation": {
            "response_length": len(payload.answer),
            "quality_score": 0.85,
            "recommended_next_focus": "technical depth"
        },
        "conversation_count": len(conv),
    }


# ============================================================================
# CORE INTERVIEW LOGIC
# ============================================================================

def start_new_interview_session(session_id: str, candidate: dict[str, Any], interview_type: str) -> UnifiedInterviewResponse:
    bootstrap = parse_bootstrap_payload()
    curriculum = bootstrap.get("curriculum", {})
    requirements = bootstrap.get("requirements", {})

    created_at = datetime.now(timezone.utc).isoformat()
    opening_question = generate_personalized_question(candidate, curriculum, requirements, turn_index=0, conversation=[])

    session_payload = {
        "session_id": session_id,
        "candidate_id": candidate.get("id", "candidate-001"),
        "candidate": candidate,
        "curriculum": curriculum,
        "requirements": requirements,
        "interview_type": interview_type,
        "conversation": [],
        "created_at": created_at,
        "status": "active",
        "turn_count": 0,
        "current_question": opening_question,
        "done": False,
    }

    sessions[session_id] = session_payload
    persist_sessions_to_disk()
    create_session(session_id, candidate.get("id", ""), interview_type, session_payload, created_at)

    return UnifiedInterviewResponse(
        reply=opening_question,
        done=False,
        sessionId=session_id,
        session_id=session_id,
        candidate_id=candidate.get("id", ""),
        status="active",
    )


def process_interview_turn(session_id: str, message_text: str) -> UnifiedInterviewResponse:
    session = get_session(session_id) or sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.get("done"):
        feedback_data = session.get("feedback")
        feedback_obj = FeedbackModel(**feedback_data) if feedback_data else build_fallback_feedback(session.get("candidate", {}), session.get("conversation", []))
        return UnifiedInterviewResponse(
            reply="The interview is already complete. Thank you!",
            done=True,
            feedback=feedback_obj,
            sessionId=session_id,
            session_id=session_id,
            candidate_id=session.get("candidate_id"),
            status="completed",
        )

    conversation = session.get("conversation", []) or []
    current_question = session.get("current_question", "")

    turn_entry = {
        "role": "user",
        "question": current_question,
        "answer": message_text,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }
    conversation.append(turn_entry)

    turn_count = session.get("turn_count", 0) + 1
    candidate = session.get("candidate", {})
    curriculum = session.get("curriculum", {})
    requirements = session.get("requirements", {})

    if turn_count >= MAX_INTERVIEW_TURNS:
        # Final Turn -> Complete Interview & Generate Structured Feedback
        feedback_dict = generate_personalized_feedback(candidate, curriculum, conversation)
        feedback_obj = FeedbackModel(**feedback_dict)

        session["conversation"] = conversation
        session["status"] = "completed"
        session["done"] = True
        session["turn_count"] = turn_count
        session["feedback"] = feedback_dict
        session["current_question"] = None

        sessions[session_id] = session
        persist_sessions_to_disk()
        update_session(session_id, session)

        # Store in reports DB table
        insert_report(
            session_id=session_id,
            report=feedback_dict,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return UnifiedInterviewResponse(
            reply="Interview completed. Thank you for discussing your technical background and curriculum progress!",
            done=True,
            feedback=feedback_obj,
            sessionId=session_id,
            session_id=session_id,
            candidate_id=session.get("candidate_id"),
            status="completed",
        )
    else:
        # Next Turn -> Generate Adaptive Question
        next_question = generate_personalized_question(candidate, curriculum, requirements, turn_index=turn_count, conversation=conversation)

        session["conversation"] = conversation
        session["status"] = "active"
        session["done"] = False
        session["turn_count"] = turn_count
        session["current_question"] = next_question

        sessions[session_id] = session
        persist_sessions_to_disk()
        update_session(session_id, session)

        insert_turn(
            session_id=session_id,
            question=current_question,
            answer=message_text,
            transcript_turn=f"Q{turn_count}",
            answered_at=datetime.now(timezone.utc).isoformat(),
        )

        return UnifiedInterviewResponse(
            reply=next_question,
            done=False,
            sessionId=session_id,
            session_id=session_id,
            candidate_id=session.get("candidate_id"),
            status="active",
        )


# ============================================================================
# PERSONALIZED & ADAPTIVE LLM / FALLBACK LOGIC
# ============================================================================

def generate_personalized_question(
    candidate: dict[str, Any],
    curriculum: dict[str, Any],
    requirements: dict[str, Any],
    turn_index: int,
    conversation: list[dict[str, Any]],
) -> str:
    # 1. Try Gemini LLM if client is initialized
    if gemini_client is not None:
        try:
            model_name = os.getenv("OPENAI_MODEL") or "gemini-2.0-flash"
            history_text = "\n".join(
                f"Q: {t.get('question')}\nA: {t.get('answer')}" for t in conversation if isinstance(t, dict)
            )

            prompt = (
                f"You are a technical interviewer for a candidate in the 31-Day AI Engineering Bootcamp.\n"
                f"Candidate Name: {candidate.get('name')}\n"
                f"Role: {candidate.get('role')}\n"
                f"Experience: {candidate.get('experience')} years\n"
                f"Skills: {', '.join(candidate.get('skills', []))}\n"
                f"Growth Areas: {', '.join(candidate.get('growth_areas', []))}\n"
                f"Bootcamp Missions: {json.dumps(candidate.get('missions', []))}\n"
                f"Turn Index: {turn_index+1} of {MAX_INTERVIEW_TURNS}\n"
                f"Previous turns:\n{history_text}\n\n"
                f"Generate turn #{turn_index+1} technical question for this interview. "
                f"If turn 1: ask a foundational question based on their primary skills and completed bootcamp missions.\n"
                f"If turn 2: probe one of their failed missions or specific growth areas ({candidate.get('growth_areas')}).\n"
                f"If turn 3: ask a system design or architectural trade-off scenario.\n"
                f"Return ONLY the plain text question for the candidate."
            )

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if hasattr(response, "text") and response.text:
                return str(response.text).strip()
        except Exception as err:
            print(f"Gemini LLM call failed, fallback used: {err}")

    # 2. Deterministic Adaptive Fallback Mode
    return build_deterministic_question(candidate, curriculum, turn_index)


def build_deterministic_question(candidate: dict[str, Any], curriculum: dict[str, Any], turn_index: int) -> str:
    name = candidate.get("name", "Candidate")
    role = candidate.get("role", "Software Engineer")
    skills = candidate.get("skills", ["Python", "APIs"])
    growth_areas = candidate.get("growth_areas", ["system design", "testing"])
    missions = candidate.get("missions", [])

    failed_missions = [m.get("title") for m in missions if not m.get("passed") and not m.get("skipped")]
    passed_missions = [m.get("title") for m in missions if m.get("passed")]

    if turn_index == 0:
        top_skill = skills[0] if skills else "software architecture"
        second_skill = skills[1] if len(skills) > 1 else "API design"
        completed_str = passed_missions[0] if passed_missions else "fundamentals"

        if "Full-stack" in role:
            return (
                f"Welcome {name}! Looking at your progress through the 31-Day AI Engineering Bootcamp as a {role}, "
                f"you've completed {completed_str} and demonstrate strength in {top_skill} and {second_skill}. "
                f"To start our interview: How do you structure production-ready APIs in {top_skill} to handle input validation, async requests, and clear error responses?"
            )
        elif "Data" in role:
            return (
                f"Welcome {name}! With your background as a {role} and experience in {top_skill} and {second_skill}, "
                f"let's start with your core workflow: How do you design scalable ETL data pipelines and handle data transformations efficiently?"
            )
        else:
            return (
                f"Welcome {name}! As a {role} with expertise in {top_skill} and {second_skill}, "
                f"let's begin: How do you architect reliable backend services in {top_skill} while maintaining high performance and test coverage?"
            )

    elif turn_index == 1:
        target_growth = growth_areas[0] if growth_areas else "system design"
        target_failed = failed_missions[0] if failed_missions else "complex data structures"

        return (
            f"Thank you for that explanation. Now focusing on your learning journey: one of your listed growth areas is '{target_growth}' "
            f"(and in the bootcamp, you revisited '{target_failed}'). "
            f"How would you approach solving bottlenecks, database query optimizations, or trade-offs when tackling '{target_growth}' in a production environment?"
        )

    else: # Turn 2
        return (
            f"Excellent insights. For our final technical topic, let's explore system design and AI integration: "
            f"If you were tasked with incorporating Vector Search or an LLM RAG pipeline into your application architecture, "
            f"how would you ensure low latency, fault tolerance, and proper evaluation of the output?"
        )


def generate_personalized_feedback(
    candidate: dict[str, Any],
    curriculum: dict[str, Any],
    conversation: list[dict[str, Any]],
) -> dict[str, Any]:
    # 1. Try Gemini LLM if client is available
    if gemini_client is not None:
        try:
            model_name = os.getenv("OPENAI_MODEL") or "gemini-2.0-flash"
            conv_text = "\n".join(
                f"Q: {t.get('question')}\nA: {t.get('answer')}" for t in conversation if isinstance(t, dict)
            )

            prompt = (
                f"You are a technical interviewer evaluating candidate {candidate.get('name')} ({candidate.get('role')}).\n"
                f"Candidate skills: {candidate.get('skills')}\n"
                f"Growth areas: {candidate.get('growth_areas')}\n"
                f"Interview Conversation:\n{conv_text}\n\n"
                f"Return a JSON object with EXACTLY these four fields:\n"
                f"- summary: a concise string paragraph summarizing their performance\n"
                f"- strengths: array of 2-3 specific strength strings\n"
                f"- gaps: array of 2-3 specific gap/growth strings\n"
                f"- next: array of 2-3 specific actionable next step strings\n"
                f"Do not output markdown codeblocks if possible, or plain valid JSON."
            )

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if hasattr(response, "text") and response.text:
                text = str(response.text).strip()
                if text.startswith("```json"):
                    text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
                elif text.startswith("```"):
                    text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "summary" in parsed and "strengths" in parsed:
                    return parsed
        except Exception as err:
            print(f"Gemini LLM feedback generation failed, fallback used: {err}")

    # 2. Deterministic Adaptive Fallback Feedback
    return build_fallback_feedback(candidate, conversation)


def build_fallback_feedback(candidate: dict[str, Any], conversation: list[dict[str, Any]]) -> dict[str, Any]:
    name = candidate.get("name", "The candidate")
    role = candidate.get("role", "Software Engineer")
    skills = candidate.get("skills", ["Python", "REST APIs"])
    growth_areas = candidate.get("growth_areas", ["System Design", "Testing"])
    missions = candidate.get("missions", [])

    passed_count = sum(1 for m in missions if m.get("passed"))
    failed_missions = [m.get("title") for m in missions if not m.get("passed") and not m.get("skipped")]

    summary = (
        f"{name} demonstrated solid domain knowledge as a {role} during the interview. "
        f"They effectively discussed their core skills in {', '.join(skills[:3])} and showed strong alignment with the "
        f"31-Day AI Engineering Bootcamp curriculum ({passed_count} missions passed). "
        f"Addressing growth areas such as {', '.join(growth_areas[:2])} will help elevate their engineering impact to senior level."
    )

    strengths = [
        f"Strong technical foundational knowledge in {skills[0] if skills else 'core development'}.",
        f"Clear communication when walking through engineering solutions and trade-offs.",
        f"Completed {passed_count} bootcamp learning missions with consistent commitment."
    ]

    gaps = [
        f"Could deepen technical coverage in key growth area: {growth_areas[0] if growth_areas else 'system design'}.",
    ]
    if failed_missions:
        gaps.append(f"Faced challenges in bootcamp topic: {failed_missions[0]}.")
    else:
        gaps.append("Needs further practice with high-concurrency production edge cases.")

    next_steps = [
        f"Focus on practical exercises in {growth_areas[0] if growth_areas else 'system design'}.",
        "Review vector database indexing, RAG retrieval techniques, and production MLOps.",
        "Continue completing remaining 31-Day AI Engineering Bootcamp capstone missions."
    ]

    return {
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "next": next_steps,
    }
