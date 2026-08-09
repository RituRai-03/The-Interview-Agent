import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent


def get_db_path() -> Path:
    if os.getenv("VERCEL"):
        return Path(tempfile.gettempdir()) / "interview_agent.db"
    try:
        test_file = BASE_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
        return BASE_DIR / "interview_agent.db"
    except Exception:
        return Path(tempfile.gettempdir()) / "interview_agent.db"


DB_PATH = get_db_path()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                interview_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS interview_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question TEXT,
                answer TEXT NOT NULL,
                transcript_turn TEXT,
                answered_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS interview_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                report TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        connection.commit()


def create_session(session_id: str, candidate_id: str, interview_type: str, payload: dict[str, Any], created_at: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO sessions (session_id, candidate_id, interview_type, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [session_id, candidate_id, interview_type, json.dumps(payload), created_at],
        )
        connection.commit()


def update_session(session_id: str, payload: dict[str, Any]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE sessions
            SET payload = ?
            WHERE session_id = ?
            """,
            [json.dumps(payload), session_id],
        )
        connection.commit()


def insert_turn(session_id: str, question: str | None, answer: str, transcript_turn: str, answered_at: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO interview_turns (session_id, question, answer, transcript_turn, answered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [session_id, question, answer, transcript_turn, answered_at],
        )
        connection.commit()


def insert_report(session_id: str, report: dict[str, Any], created_at: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO interview_reports (session_id, report, created_at)
            VALUES (?, ?, ?)
            """,
            [session_id, json.dumps(report), created_at],
        )
        connection.commit()


def get_report(session_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT report FROM interview_reports WHERE session_id = ?",
            [session_id],
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["report"])


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT payload FROM sessions WHERE session_id = ?",
            [session_id],
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload"])


def list_sessions() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT session_id, candidate_id, interview_type, payload, created_at FROM sessions"
        ).fetchall()

        items = []
        for row in rows:
            payload = json.loads(row["payload"])
            items.append({
                "session_id": row["session_id"],
                "candidate_id": row["candidate_id"],
                "status": payload.get("status"),
                "created_at": row["created_at"],
            })
        return items


def session_exists(session_id: str) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?",
            [session_id],
        ).fetchone()
        return row is not None
