# The Interview Agent Backend

This folder contains the FastAPI backend for The Interview Agent.

## Stack

- FastAPI
- Uvicorn
- Pydantic
- SQLite
- JSON bootstrap data

## Runtime setup

Install dependencies:

```powershell
python -m pip install -r Backend/requirements.txt
```

Start the API locally:

```powershell
.venv\Scripts\python.exe -m uvicorn Backend.main:app --host 127.0.0.1 --port 8000 --reload
```

## Environment

The API reads candidate and curriculum seed data from the JSON files in this folder.
The API can optionally use Gemini environment variables such as `OPENAI_API_KEY` or `GEMINI_API_KEY`.

## Endpoints

### Health

- GET `/health`

### Session lifecycle

- GET `/api/interview`
- POST `/api/interview`
- GET `/api/interview/{session_id}`
- POST `/api/interview/{session_id}/answer`
- GET `/api/interview/{session_id}/report`

Example payload for session creation:

```json
{
  "candidate_id": "candidate-001",
  "interview_type": "technical",
  "conversation": []
}
```

Example answer payload:

```json
{
  "answer": "I would design a small API using FastAPI, validate inputs, and explain trade-offs.",
  "transcript_turn": "Q1"
}
```
