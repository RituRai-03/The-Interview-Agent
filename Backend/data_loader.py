import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent


def load_json(path: str) -> dict[str, Any]:
    file_path = BASE_DIR / path
    if not file_path.exists():
        raise FileNotFoundError(f"JSON data file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_candidates() -> list[dict[str, Any]]:
    payload = load_json("candidates.json")
    candidates = payload.get("candidates", [])
    return candidates


def get_curriculum() -> dict[str, Any]:
    payload = load_json("curriculum.json")
    return payload.get("curriculum", {})


def get_candidate_by_id(candidate_id: str) -> dict[str, Any] | None:
    for candidate in get_candidates():
        if candidate.get("id") == candidate_id:
            return candidate
    return None


def get_candidate_metrics(candidate_id: str) -> dict[str, Any] | None:
    candidate = get_candidate_by_id(candidate_id)
    if candidate is None:
        return None
    return candidate.get("metrics", {})


def get_curriculum_requirements() -> dict[str, Any]:
    curriculum = get_curriculum()
    return curriculum.get("requirements", {})


def parse_bootstrap_payload() -> dict[str, Any]:
    return {
        "candidates": get_candidates(),
        "curriculum": get_curriculum(),
        "requirements": get_curriculum_requirements(),
    }
