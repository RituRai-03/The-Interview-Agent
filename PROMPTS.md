# AI Coding Prompts & Development Log - The Interview Agent

This log documents the AI prompts, engineering decisions, and workflows used in developing **The Interview Agent** hackathon project.

---

## Overview & Architecture Goals

**Project Name**: The Interview Agent  
**Goal**: Build an AI-driven, multi-turn technical interviewer that personalizes interviews based on candidate profiles, learning history, and progress in the **31-Day AI Engineering Bootcamp**.

### Tech Stack
- **Frontend**: React + Vite, Vanilla CSS glassmorphism UI.
- **Backend**: FastAPI (Python), Uvicorn, Pydantic V2, SQLite persistence.
- **Data & Parsing Layer**: Data-Logic analyzer, Pydantic data validators, 31-day curriculum mapper.
- **AI / LLM Integration**: Gemini API integration with automatic deterministic offline fallback mode.

---

## 1. Data Layer & Validation Engineering

### Prompt Context & Objective
Set up rigid data schemas for `candidates.json` and `curriculum.json` to ensure clean parsing, progress metrics, and curriculum mapping.

### Key AI Prompt Sequence
> *"Create a data parsing module with Pydantic validators (`validators.py`) and data logic (`data_logic.py`) that loads candidate profiles and 31-day curriculum missions. Calculate completion rates, pass rates, first-try rates, failed/skipped mission lists, and format context for LLM interview prompts."*

### Key Implementation Details
- Created `CandidateModel`, `MissionModel`, `CurriculumModel`, `CandidatesPayloadModel`, and `CurriculumPayloadModel`.
- Built analysis functions: `calculate_candidate_progress()`, `analyze_candidate()`, and `format_candidate_context()`.
- Implemented 40+ unit tests in `Data-Parsing/test_data_logic.py`.

---

## 2. API Contract & Technical Specification Alignment

### Prompt Context & Objective
Align backend API endpoints with `technical-spec.md` for a single unified public endpoint: `POST /api/interview`.

### Key AI Prompt Sequence
> *"Refactor Backend/main.py to unify the public interview API under `POST /api/interview`. Handle initialization requests (`{sessionId, candidate}`) and turn requests (`{sessionId, message}`). Maintain session state via `sessionId` across multi-turn interactions and return structured feedback (`summary`, `strengths`, `gaps`, `next`) upon completion."*

### Key Implementation Details
- Built `UnifiedInterviewRequest` and `UnifiedInterviewResponse` using Pydantic `ConfigDict(populate_by_name=True)`.
- Maintained backward compatibility for helper endpoints (`GET /health`, `GET /api/interview/{id}`, `GET /api/interview/{id}/report`).
- Handled candidate lookup, session store persistence (`sessions.json` and SQLite `interview_agent.db`), and safe `/tmp` fallback resolution for serverless environments (Vercel).

---

## 3. Candidate Personalization & Adaptive Interview Flow

### Prompt Context & Objective
Ensure the AI interviewer dynamically adapts questions to each candidate's background rather than asking generic questions.

### Candidate Specific Flows
1. **Aarav Sharma (Full-stack Engineer)**:
   - *Skills*: Python, FastAPI, JavaScript, REST APIs.
   - *Target Areas*: Database query optimization (growth area), Data Structures & Algorithms (failed Day 4 mission), Vector Search & RAG (Day 8 Embeddings).
2. **Mia Johnson (Data Engineer)**:
   - *Skills*: SQL, Python, ETL, PySpark, Pandas.
   - *Target Areas*: Scalable ETL pipelines, REST API design (failed Day 6 mission), data warehouse modeling.
3. **James Chen (Backend Engineer)**:
   - *Skills*: Python, Go, Kubernetes, Microservices, gRPC.
   - *Target Areas*: Low-latency microservices, prompt engineering & fine-tuning (Day 11-12 missions), production MLOps.

---

## 4. Fallback Mode & Reliability

### Prompt Context & Objective
Guarantee that the hackathon application functions 100% reliably even if no external LLM API key (`GEMINI_API_KEY`) is configured.

### Key AI Prompt Sequence
> *"Implement a deterministic adaptive interview fallback generator in Backend/main.py. If the Gemini LLM API key is missing or fails, generate personalized questions and structured feedback based on candidate metrics, failed missions, and growth areas."*

---

## 5. Deployment & Monorepo Setup

### Prompt Context & Objective
Deploy Frontend (React + Vite) and Backend (FastAPI) under **ONE single Vercel domain** (`https://<project>.vercel.app`).

### Key AI Prompt Sequence
> *"Configure `vercel.json` and `api/index.py` for monorepo deployment on Vercel. Serve the React frontend on `/` and route all `/api/*` requests to the FastAPI backend. Ensure production frontend API calls use same-origin `/api/interview` path."*

---

## Verification & Test Log

- **Pytest Backend & Data Tests**: 35/35 tests passed.
- **Frontend Build**: Vite build completed cleanly (`dist/assets`).
- **Data Validation Script**: `validate_linking.py` executed successfully.
- **E2E Live API Tests**: Multi-turn roundtrip verified for Aarav, Mia, and James.
