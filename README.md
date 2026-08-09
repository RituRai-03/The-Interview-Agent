# The Interview Agent

An adaptive, multi-turn AI Interview Agent built for evaluating candidates through personalized, context-aware technical interviews based on their **31-Day AI Engineering Bootcamp** progress. The system asks dynamic follow-up questions, probes growth areas/failed missions, and generates structured actionable feedback.

---

## 🚀 Live Production URLs

- **Frontend Application**: [https://the-interview-agent-eta.vercel.app](https://the-interview-agent-eta.vercel.app)
- **Backend API Base**: `https://the-interview-agent-eta.vercel.app/api`
- **API Health Check**: [https://the-interview-agent-eta.vercel.app/api/health](https://the-interview-agent-eta.vercel.app/api/health)
- **Public GitHub Repository**: [https://github.com/RituRai-03/The-Interview-Agent](https://github.com/RituRai-03/The-Interview-Agent)
- **AI Prompts & Usage Log**: [PROMPTS.md](https://github.com/RituRai-03/The-Interview-Agent/blob/main/PROMPTS.md)

---

## 🏗️ Production Architecture

```
USER BROWSER
    ↓
Vercel React + Vite Frontend (https://the-interview-agent-eta.vercel.app)
    ↓  (same-domain relative route /api/interview)
Vercel Serverless Function (api/index.py)
    ↓
FastAPI Backend (Backend/main.py)
    ↓
Data-Parsing Module + candidates.json + curriculum.json + SQLite / Session Persistence
    ↓
Personalized Adaptive Response + Structured Feedback
```

---

## ⚡ Key Features

1. **Compliant Public API Contract (`technical-spec.md`)**:
   - `POST /api/interview` supports initialization (`{sessionId, candidate}`) and multi-turn responses (`{sessionId, message}`).
   - Returns structured final feedback (`summary`, `strengths`, `gaps`, `next`).
2. **Candidate Personalization**:
   - Dynamic questioning tailored for candidate profiles (Aarav Sharma - Full-stack, Mia Johnson - Data Engineer, James Chen - Backend Engineer).
3. **31-Day Bootcamp Curriculum Integration**:
   - Driven by `curriculum.json` and candidate mission history (`candidates.json`).
4. **Adaptive Multi-Turn Flow**:
   - Evaluates answer quality, targets failed missions/growth areas, and finishes naturally after 3-4 turns.
5. **Deterministic Fallback Mode**:
   - Works 100% reliably even if no LLM API key (`GEMINI_API_KEY`) is configured.

---

## 💻 Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+

### 2. Backend Setup
```bash
# From repository root
cd Backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Backend will run at `http://localhost:8000`.

### 3. Frontend Setup
```bash
# From repository root
cd frontend
npm install
npm run dev -- --port 5174
```
Frontend will run at `http://localhost:5174`.

### 4. Running Tests
```bash
# Run pytest unit and integration tests
.\.venv\Scripts\python.exe -m pytest -v Data-Parsing/ Backend/

# Run Data-Parsing validation script
$env:PYTHONIOENCODING="utf-8"; .\.venv\Scripts\python.exe Data-Parsing/validate_linking.py

# Run frontend build
cd frontend && npm run build
```

---

## 🔑 Environment Variables

### Backend (`Backend/.env`)
- `GEMINI_API_KEY`: *(Optional)* API key for Google Gemini model generation. If not set, system operates in deterministic fallback mode.

### Frontend (`frontend/.env`)
- `VITE_API_URL`: *(Optional)* Base URL for backend. Defaults to `http://localhost:8000` in dev mode, and relative `/api` in production on Vercel.
