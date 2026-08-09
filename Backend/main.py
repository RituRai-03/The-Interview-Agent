import json
import os
import re
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
# AUTHORITATIVE CANDIDATE LOOKUP & VERIFICATION
# ============================================================================

def find_authoritative_candidate(candidate_id_or_query: str) -> dict[str, Any] | None:
    if not candidate_id_or_query or not str(candidate_id_or_query).strip():
        return None

    bootstrap = parse_bootstrap_payload()
    candidates = bootstrap.get("candidates", [])
    q = str(candidate_id_or_query).strip().lower()

    q_num = re.sub(r'[^0-9]', '', q)

    for c in candidates:
        cid = str(c.get("id", "")).strip().lower()
        cid_num = re.sub(r'[^0-9]', '', cid)

        if cid == q:
            return c
        if q_num and cid_num and q_num.zfill(3) == cid_num.zfill(3):
            return c
        if f"candidate-{q_num.zfill(3)}" == cid or f"cand-{q_num.zfill(3)}" == cid:
            return c

    return None


# ============================================================================
# ANSWER QUALITY CLASSIFICATION
# ============================================================================

ANSWER_QUALITY_PUNCTUATION = "punctuation_only"
ANSWER_QUALITY_UNCERTAINTY = "uncertainty"
ANSWER_QUALITY_VERY_SHORT = "very_short"
ANSWER_QUALITY_MEANINGFUL = "meaningful"

UNCERTAINTY_PHRASES = [
    "don't know", "dont know", "not sure", "no idea", "no answer",
    "not familiar", "dunno", "can't answer", "cant answer", "have no idea",
    "i don't understand", "i dont understand", "uncertain"
]


def evaluate_answer_quality(answer_text: str) -> str:
    if not answer_text or not answer_text.strip():
        return ANSWER_QUALITY_PUNCTUATION

    cleaned = answer_text.strip()
    lowered = cleaned.lower()

    alphanumeric_chars = re.sub(r'[^a-zA-Z0-9]', '', cleaned)
    if len(alphanumeric_chars) == 0:
        return ANSWER_QUALITY_PUNCTUATION

    if any(phrase in lowered for phrase in UNCERTAINTY_PHRASES):
        words = lowered.split()
        if len(words) < 12:
            return ANSWER_QUALITY_UNCERTAINTY

    words = cleaned.split()
    if len(words) <= 2:
        return ANSWER_QUALITY_VERY_SHORT

    return ANSWER_QUALITY_MEANINGFUL


# ============================================================================
# PYDANTIC MODELS
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
    candidate_id: Optional[str] = Field(default=None, alias="candidateId")
    candidateId: Optional[str] = None
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


@app.get("/api/candidates/{candidate_id}")
def verify_candidate_endpoint(candidate_id: str) -> dict[str, Any]:
    candidate = find_authoritative_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return {
        "verified": True,
        "candidate": candidate
    }


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
    requirements = session.get("requirements", {}) or {}
    curriculum = session.get("curriculum", {}) or {}
    required_modules = requirements.get("required_modules", []) or []
    conversation = session.get("conversation", []) or []

    analysis = analyze_interview_transcript(conversation)
    answers = [item for item in conversation if isinstance(item, dict) and item.get("answer")]

    if not analysis["has_meaningful_evidence"]:
        candidate_score = 15.0
        curriculum_progress = 10.0
    else:
        base_score = min(100.0, (analysis["meaningful_count"] / max(1, MAX_INTERVIEW_TURNS)) * 85 + len(analysis["demonstrated_concepts"]) * 5)
        candidate_score = round(base_score, 2)
        curriculum_progress = round(min(100.0, candidate_score + 10), 2)

    coverage = []
    for module in required_modules:
        module_lower = module.lower()
        if any(module_lower in str(item.get("answer", "")).lower() for item in conversation if isinstance(item, dict)):
            coverage.append(module)

    report = InterviewReportResponse(
        session_id=session_id,
        candidate_id=session.get("candidate_id", ""),
        candidate_name=candidate.get("name", "Unknown Candidate"),
        interview_type=session.get("interview_type", "technical"),
        candidate_score=candidate_score,
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
    req_session_id = payload.sessionId or payload.session_id
    req_message = payload.message or payload.answer

    req_candidate_id = payload.candidate_id or payload.candidateId
    if not req_candidate_id and payload.candidate and isinstance(payload.candidate, dict):
        req_candidate_id = payload.candidate.get("id")

    if req_session_id and req_message is not None:
        session = get_session(req_session_id) or sessions.get(req_session_id)
        if session:
            bound_cid = session.get("candidate_id")
            if req_candidate_id and bound_cid:
                cand_req = find_authoritative_candidate(req_candidate_id)
                cand_bound = find_authoritative_candidate(bound_cid)
                if cand_req and cand_bound and cand_req.get("id") != cand_bound.get("id"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot change candidate during an active interview session."
                    )
        return process_interview_turn(req_session_id, req_message)

    if req_session_id and not payload.candidate and not req_candidate_id:
        if session_exists(req_session_id) or req_session_id in sessions:
            if req_message is not None:
                return process_interview_turn(req_session_id, req_message)
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is required for ongoing interview turn.")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if not req_candidate_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Valid candidate ID is required to initialize an interview session."
        )

    authoritative_candidate = find_authoritative_candidate(req_candidate_id)
    if authoritative_candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    session_id = req_session_id or str(uuid.uuid4())
    return start_new_interview_session(session_id, authoritative_candidate, payload.interview_type)


@app.post("/api/interview/{session_id}/answer")
def answer_interview_question_legacy(session_id: str, payload: InterviewAnswerRequest) -> dict[str, Any]:
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
    opening_question = generate_personalized_question(
        candidate=candidate,
        curriculum=curriculum,
        requirements=requirements,
        turn_index=0,
        conversation=[],
        latest_quality=None,
        latest_answer=None
    )

    session_payload = {
        "session_id": session_id,
        "candidate_id": candidate.get("id"),
        "candidate": candidate,
        "curriculum": curriculum,
        "requirements": requirements,
        "interview_type": interview_type,
        "conversation": [],
        "created_at": created_at,
        "status": "active",
        "turn_count": 0,
        "meaningful_turn_count": 0,
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
        candidate_id=candidate.get("id"),
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

    quality = evaluate_answer_quality(message_text)

    turn_entry = {
        "role": "user",
        "question": current_question,
        "answer": message_text,
        "quality": quality,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }
    conversation.append(turn_entry)

    candidate = session.get("candidate", {})
    curriculum = session.get("curriculum", {})
    requirements = session.get("requirements", {})

    meaningful_count = session.get("meaningful_turn_count", 0)
    if quality == ANSWER_QUALITY_MEANINGFUL:
        meaningful_count += 1
        session["meaningful_turn_count"] = meaningful_count

    total_attempts = len(conversation)

    if meaningful_count >= MAX_INTERVIEW_TURNS or total_attempts >= 8:
        feedback_dict = generate_personalized_feedback(candidate, curriculum, conversation)
        feedback_obj = FeedbackModel(**feedback_dict)

        session["conversation"] = conversation
        session["status"] = "completed"
        session["done"] = True
        session["turn_count"] = total_attempts
        session["feedback"] = feedback_dict
        session["current_question"] = None

        sessions[session_id] = session
        persist_sessions_to_disk()
        update_session(session_id, session)

        insert_report(
            session_id=session_id,
            report=feedback_dict,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return UnifiedInterviewResponse(
            reply="Interview completed. Thank you for walking through your technical background and curriculum progress!",
            done=True,
            feedback=feedback_obj,
            sessionId=session_id,
            session_id=session_id,
            candidate_id=session.get("candidate_id"),
            status="completed",
        )

    next_question = generate_personalized_question(
        candidate=candidate,
        curriculum=curriculum,
        requirements=requirements,
        turn_index=meaningful_count,
        conversation=conversation,
        latest_quality=quality,
        latest_answer=message_text,
    )

    session["conversation"] = conversation
    session["status"] = "active"
    session["done"] = False
    session["turn_count"] = total_attempts
    session["current_question"] = next_question

    sessions[session_id] = session
    persist_sessions_to_disk()
    update_session(session_id, session)

    insert_turn(
        session_id=session_id,
        question=current_question,
        answer=message_text,
        transcript_turn=f"Q{total_attempts}",
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
# PERSONALIZED QUESTION & EVIDENCE-BASED FEEDBACK GENERATION
# ============================================================================

def generate_personalized_question(
    candidate: dict[str, Any],
    curriculum: dict[str, Any],
    requirements: dict[str, Any],
    turn_index: int,
    conversation: list[dict[str, Any]],
    latest_quality: Optional[str] = None,
    latest_answer: Optional[str] = None,
) -> str:
    if latest_quality == ANSWER_QUALITY_PUNCTUATION:
        return (
            "It looks like your response may not have come through clearly. "
            "Could you please share your technical approach to the question?"
        )

    if latest_quality == ANSWER_QUALITY_UNCERTAINTY:
        role = candidate.get("role", "software engineer")
        return (
            f"That's completely fine! Let's approach it from a simpler angle: for a {role}, "
            "what initial steps or core principles would you consider when starting to address this problem?"
        )

    if latest_quality == ANSWER_QUALITY_VERY_SHORT and latest_answer:
        short_text = latest_answer.strip()
        return (
            f"What makes '{short_text}' a suitable choice for this problem? "
            "Could you explain one key advantage and one trade-off of that choice?"
        )

    if gemini_client is not None:
        try:
            model_name = os.getenv("OPENAI_MODEL") or "gemini-2.0-flash"
            history_text = "\n".join(
                f"Q: {t.get('question')}\nA: {t.get('answer')}" for t in conversation if isinstance(t, dict)
            )

            prompt = (
                f"You are a technical interviewer evaluating candidate {candidate.get('name')} ({candidate.get('role')}).\n"
                f"Candidate skills: {candidate.get('skills')}\n"
                f"Growth areas: {candidate.get('growth_areas')}\n"
                f"Latest Answer: '{latest_answer}' (Quality Classification: {latest_quality})\n"
                f"Previous Turns:\n{history_text}\n\n"
                f"STRICT INSTRUCTIONS:\n"
                f"- Evaluate the latest candidate answer before responding.\n"
                f"- NEVER output positive praise phrases like 'Excellent insights' or 'Great explanation' unless the answer contains meaningful technical substance.\n"
                f"- Reference specific technical concepts from their latest answer if meaningful.\n"
                f"- Generate turn #{turn_index+1} question focusing on deep technical details, trade-offs, or system design.\n"
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

    return build_deterministic_question(candidate, curriculum, turn_index, latest_answer)


def build_deterministic_question(candidate: dict[str, Any], curriculum: dict[str, Any], turn_index: int, latest_answer: Optional[str] = None) -> str:
    name = candidate.get("name", "Candidate")
    role = candidate.get("role", "Software Engineer")
    skills = candidate.get("skills", ["Python", "APIs"])
    growth_areas = candidate.get("growth_areas", ["system design", "testing"])
    missions = candidate.get("missions", [])

    failed_missions = [m.get("title") for m in missions if not m.get("passed") and not m.get("skipped")]
    passed_missions = [m.get("title") for m in missions if m.get("passed")]

    if latest_answer and len(latest_answer.strip()) > 10:
        ans_lower = latest_answer.lower()
        if "postgres" in ans_lower or "sql" in ans_lower or "index" in ans_lower or "database" in ans_lower:
            return (
                "You highlighted database indexing and structural design concerns. "
                "How do you determine which specific columns to index, and what write-performance trade-offs do excessive indexes introduce?"
            )
        elif "redis" in ans_lower or "cache" in ans_lower or "caching" in ans_lower:
            return (
                "You mentioned caching for performance optimization. "
                "How do you manage cache invalidation and TTL policies when multiple service instances process real-time updates?"
            )
        elif "fastapi" in ans_lower or "pydantic" in ans_lower or "async" in ans_lower or "api" in ans_lower:
            return (
                "Your approach covers clean API endpoints and validation. "
                "How do you handle background tasks, async rate limiting, and graceful degradation during traffic spikes?"
            )

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
            f"Thank you for walking through that. Moving to your learning journey: one of your growth areas is '{target_growth}' "
            f"(and in the bootcamp, you revisited '{target_failed}'). "
            f"How would you approach solving bottlenecks and query trade-offs when scaling '{target_growth}' in a production environment?"
        )

    else:
        return (
            f"For our final technical topic, let's explore system design and AI integration: "
            f"If you were tasked with incorporating Vector Search or an LLM RAG pipeline into your application architecture, "
            f"how would you ensure low latency, fault tolerance, and proper evaluation of the output?"
        )


def analyze_interview_transcript(conversation: list[dict[str, Any]]) -> dict[str, Any]:
    meaningful_turns = []
    uncertain_turns = []
    punctuation_turns = []
    short_turns = []

    demonstrated_concepts = set()

    for turn in conversation:
        if not isinstance(turn, dict):
            continue
        ans = turn.get("answer", "")
        q_type = turn.get("quality") or evaluate_answer_quality(ans)

        if q_type == ANSWER_QUALITY_MEANINGFUL:
            meaningful_turns.append(turn)
            ans_lower = ans.lower()
            if "postgres" in ans_lower or "sql" in ans_lower or "database" in ans_lower:
                demonstrated_concepts.add("relational database architecture & query optimization")
            if "index" in ans_lower or "indexing" in ans_lower:
                demonstrated_concepts.add("database indexing trade-offs")
            if "connection pool" in ans_lower or "pooling" in ans_lower:
                demonstrated_concepts.add("connection pooling and resource management")
            if "fastapi" in ans_lower or "pydantic" in ans_lower or "api" in ans_lower:
                demonstrated_concepts.add("production API architecture & Pydantic validation")
            if "async" in ans_lower or "handler" in ans_lower:
                demonstrated_concepts.add("asynchronous request handling")
            if "redis" in ans_lower or "cache" in ans_lower or "caching" in ans_lower:
                demonstrated_concepts.add("Redis caching & invalidation strategies")
            if "faiss" in ans_lower or "vector" in ans_lower or "rag" in ans_lower or "embedding" in ans_lower:
                demonstrated_concepts.add("Vector search & RAG pipeline integration")
            if "etl" in ans_lower or "pipeline" in ans_lower or "spark" in ans_lower:
                demonstrated_concepts.add("ETL pipeline construction & transformation logic")

        elif q_type == ANSWER_QUALITY_UNCERTAINTY:
            uncertain_turns.append(turn)
        elif q_type == ANSWER_QUALITY_PUNCTUATION:
            punctuation_turns.append(turn)
        elif q_type == ANSWER_QUALITY_VERY_SHORT:
            short_turns.append(turn)

    return {
        "meaningful_count": len(meaningful_turns),
        "uncertain_count": len(uncertain_turns),
        "punctuation_count": len(punctuation_turns),
        "short_count": len(short_turns),
        "total_turns": len(conversation),
        "demonstrated_concepts": list(demonstrated_concepts),
        "has_meaningful_evidence": len(meaningful_turns) > 0,
    }


def generate_personalized_feedback(
    candidate: dict[str, Any],
    curriculum: dict[str, Any],
    conversation: list[dict[str, Any]],
) -> dict[str, Any]:
    analysis = analyze_interview_transcript(conversation)

    if gemini_client is not None:
        try:
            model_name = os.getenv("OPENAI_MODEL") or "gemini-2.0-flash"
            conv_text = "\n".join(
                f"Q: {t.get('question')}\nA: {t.get('answer')} [Quality: {t.get('quality', 'unknown')}]"
                for t in conversation if isinstance(t, dict)
            )

            prompt = (
                f"You are an objective technical interviewer evaluating candidate {candidate.get('name')} ({candidate.get('role')}).\n"
                f"CANDIDATE PROFILE CONTEXT (FOR BACKGROUND ONLY — DO NOT USE AS INTERVIEW EVIDENCE):\n"
                f"- Candidate skills: {candidate.get('skills')}\n"
                f"- Growth areas: {candidate.get('growth_areas')}\n"
                f"- Past Bootcamp Missions: {len(candidate.get('missions', []))} missions\n\n"
                f"ACTUAL INTERVIEW TRANSCRIPT (SOLE EVIDENCE SOURCE FOR EVALUATION):\n{conv_text}\n\n"
                f"STRICT INSTRUCTIONS:\n"
                f"1. Evaluate ONLY performance demonstrated in the interview transcript.\n"
                f"2. Candidate profile, skills, experience, and past missions are CONTEXT ONLY. DO NOT claim the candidate demonstrated a skill unless the transcript contains actual evidence of that skill!\n"
                f"3. DO NOT praise unanswered, punctuation-only ('.'), or uncertain ('not sure') responses. NEVER say 'solid domain knowledge' or 'clear communication' if candidate gave no meaningful technical answers!\n"
                f"4. If there is insufficient evidence to assess a skill or topic, explicitly state that evidence was insufficient.\n"
                f"5. Every strength MUST be traceable to an actual candidate answer in the transcript.\n"
                f"6. Return a JSON object with EXACTLY four fields: summary, strengths, gaps, next.\n"
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

    return build_fallback_feedback(candidate, conversation)


def build_fallback_feedback(candidate: dict[str, Any], conversation: list[dict[str, Any]]) -> dict[str, Any]:
    name = candidate.get("name", "The candidate")
    role = candidate.get("role", "Software Engineer")
    analysis = analyze_interview_transcript(conversation)

    meaningful_count = analysis["meaningful_count"]
    uncertain_count = analysis["uncertain_count"]
    punctuation_count = analysis["punctuation_count"]
    concepts = analysis["demonstrated_concepts"]

    # SCENARIO A: Weak / Invalid / Unanswered / Punctuation-Heavy Interview
    if not analysis["has_meaningful_evidence"]:
        summary = (
            f"The interview provided limited evidence of {name}'s technical abilities as a {role} "
            "because the candidate gave unanswered, punctuation-only, or uncertain responses throughout the session."
        )
        strengths = [
            "No substantial technical strengths could be reliably assessed from this interview session."
        ]
        gaps = [
            f"Targeted technical competencies for {role} could not be evaluated due to incomplete or unanswered responses.",
            "Demonstrated technical reasoning and communication were insufficient during the interview."
        ]
        next_steps = [
            "Practice explaining technical approaches and trade-offs aloud.",
            f"Review core fundamentals and system design concepts relevant to {role}.",
            "Reattempt the technical interview with detailed, structured responses."
        ]
        return {
            "summary": summary,
            "strengths": strengths,
            "gaps": gaps,
            "next": next_steps,
        }

    # SCENARIO B: Strong / Evidence-Based Interview
    concept_str = ", ".join(concepts) if concepts else "core software engineering principles"
    summary = (
        f"During the interview, {name} demonstrated practical technical understanding in {concept_str}. "
        "Their responses provided evidence of engineering trade-off awareness and technical problem-solving."
    )

    strengths = []
    for concept in concepts[:3]:
        strengths.append(f"Demonstrated practical knowledge of {concept} in candidate responses.")
    if not strengths:
        strengths.append(f"Provided structured technical answers relevant to {role} questions.")

    gaps = [
        f"Could expand technical depth when addressing complex distributed edge cases in {role}.",
    ]
    if uncertain_count > 0 or punctuation_count > 0:
        gaps.append("Some topics required simplified follow-ups or additional clarification before technical details were provided.")

    next_steps = [
        f"Further refine production failure handling and concurrency patterns in {role}.",
        "Review vector database indexing, RAG evaluation frameworks, and production MLOps.",
        "Continue completing 31-Day AI Engineering Bootcamp capstone missions."
    ]

    return {
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "next": next_steps,
    }
