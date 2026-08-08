"""
Data & Logic layer for candidate analysis and evaluation.

This module provides core functions for:
- Loading and validating candidates and curriculum data
- Calculating candidate progress metrics
- Analyzing candidate strengths and weaknesses
- Evaluating performance against curriculum
- Formatting candidate context for LLM integration

Note: This module loads data from Backend/candidates.json and Backend/curriculum.json
"""

import json
from pathlib import Path
from typing import Any, Optional

from validators import CandidateModel, CurriculumModel, CurriculumPayloadModel, CandidatesPayloadModel


# Get path to Backend folder (where JSON data files are stored)
DATA_PARSING_DIR = Path(__file__).resolve().parent
BACKEND_DIR = DATA_PARSING_DIR.parent / "Backend"

# ============================================================================
# DATA LOADING & VALIDATION
# ============================================================================


def load_candidates(filepath: Optional[str] = None) -> list[CandidateModel]:
    """
    Load and validate candidates from JSON file.

    Args:
        filepath: Path to candidates.json (defaults to Backend/candidates.json)

    Returns:
        List of validated CandidateModel instances

    Raises:
        FileNotFoundError: If candidates.json not found
        json.JSONDecodeError: If JSON is malformed
        ValueError: If data doesn't match CandidateModel schema
    """
    file_path = Path(filepath) if filepath else BACKEND_DIR / "candidates.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Candidates file not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Malformed JSON in {file_path}: {e.msg}", e.doc, e.pos
        ) from e

    try:
        payload = CandidatesPayloadModel(**data)
        return payload.candidates
    except Exception as e:
        raise ValueError(
            f"Invalid candidate data structure: {str(e)}"
        ) from e


def load_curriculum(filepath: Optional[str] = None) -> CurriculumModel:
    """
    Load and validate curriculum from JSON file.

    Args:
        filepath: Path to curriculum.json (defaults to Backend/curriculum.json)

    Returns:
        Validated CurriculumModel instance

    Raises:
        FileNotFoundError: If curriculum.json not found
        json.JSONDecodeError: If JSON is malformed
        ValueError: If data doesn't match CurriculumModel schema
    """
    file_path = Path(filepath) if filepath else BACKEND_DIR / "curriculum.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Curriculum file not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Malformed JSON in {file_path}: {e.msg}", e.doc, e.pos
        ) from e

    try:
        payload = CurriculumPayloadModel(**data)
        return payload.curriculum
    except Exception as e:
        raise ValueError(
            f"Invalid curriculum data structure: {str(e)}"
        ) from e


# ============================================================================
# CANDIDATE LOOKUP
# ============================================================================


def get_candidate(candidate_id: str) -> Optional[CandidateModel]:
    """
    Retrieve a single candidate by ID.

    Args:
        candidate_id: Unique candidate identifier

    Returns:
        CandidateModel if found, None otherwise
    """
    try:
        candidates = load_candidates()
        return next((c for c in candidates if c.id == candidate_id), None)
    except Exception:
        return None


# ============================================================================
# PROGRESS CALCULATION
# ============================================================================


def calculate_candidate_progress(candidate: CandidateModel) -> dict[str, Any]:
    """
    Calculate comprehensive progress metrics for a candidate.

    Analyzes mission completion, attempts, pass rates, and commit activity.

    Args:
        candidate: CandidateModel instance

    Returns:
        Dictionary containing:
            - total_missions: Total missions assigned
            - completed_missions: Successfully passed missions
            - passed_missions: Missions with passed=True
            - failed_missions: Missions with passed=False (not skipped)
            - skipped_missions: Missions with skipped=True
            - attempted_missions: Missions that were not skipped
            - completion_rate: % of non-skipped missions completed
            - pass_rate: % of attempted missions passed (of non-skipped)
            - first_try_rate: % of passed missions completed on first attempt
            - average_attempts: Average attempts for attempted missions
            - total_attempts: Sum of all attempts
            - total_commit_days: Sum of distinct commit days
            - current_day: Highest day reached
            - progress_percentage: Overall progress (0-100)
    """
    missions = candidate.missions or []

    if not missions:
        return {
            "total_missions": 0,
            "completed_missions": 0,
            "passed_missions": 0,
            "failed_missions": 0,
            "skipped_missions": 0,
            "attempted_missions": 0,
            "completion_rate": 0.0,
            "pass_rate": 0.0,
            "first_try_rate": 0.0,
            "average_attempts": 0.0,
            "total_attempts": 0,
            "total_commit_days": 0,
            "current_day": 0,
            "progress_percentage": 0.0,
        }

    total_missions = len(missions)
    skipped_missions = sum(1 for m in missions if m.skipped)
    attempted_missions = total_missions - skipped_missions

    # Passed: mission with passed=True AND not skipped
    passed_missions = sum(1 for m in missions if m.passed and not m.skipped)

    # Failed: mission with passed=False AND not skipped
    failed_missions = sum(1 for m in missions if not m.passed and not m.skipped)

    # Completed = Passed (only count successful completions)
    completed_missions = passed_missions

    # First-try: passed missions with attempts=1
    first_try = sum(1 for m in missions if m.passed and m.attempts == 1)

    # Metrics
    completion_rate = (passed_missions / attempted_missions * 100) if attempted_missions > 0 else 0.0
    pass_rate = (passed_missions / attempted_missions * 100) if attempted_missions > 0 else 0.0
    first_try_rate = (first_try / passed_missions * 100) if passed_missions > 0 else 0.0
    average_attempts = (
        sum(m.attempts for m in missions if not m.skipped) / attempted_missions
        if attempted_missions > 0
        else 0.0
    )

    total_attempts = sum(m.attempts for m in missions if not m.skipped)
    total_commit_days = sum(m.commit_days for m in missions if not m.skipped)
    current_day = max((m.day for m in missions), default=0)

    # Overall progress: combination of completion and current day
    progress_percentage = (current_day / 31 * 100) + (completion_rate * 0.5) if current_day > 0 else 0.0
    progress_percentage = min(100.0, progress_percentage)

    return {
        "total_missions": total_missions,
        "completed_missions": completed_missions,
        "passed_missions": passed_missions,
        "failed_missions": failed_missions,
        "skipped_missions": skipped_missions,
        "attempted_missions": attempted_missions,
        "completion_rate": round(completion_rate, 2),
        "pass_rate": round(pass_rate, 2),
        "first_try_rate": round(first_try_rate, 2),
        "average_attempts": round(average_attempts, 2),
        "total_attempts": total_attempts,
        "total_commit_days": total_commit_days,
        "current_day": current_day,
        "progress_percentage": round(progress_percentage, 2),
    }


# ============================================================================
# CURRICULUM MAPPING
# ============================================================================


def map_mission_to_curriculum(
    mission_title: str, curriculum: Optional[CurriculumModel] = None
) -> Optional[dict[str, Any]]:
    """
    Map a mission title to its corresponding curriculum module and details.

    Searches by day or title match.

    Args:
        mission_title: Title of mission to map
        curriculum: CurriculumModel (loads if not provided)

    Returns:
        Dictionary with module info or None if not found:
            - module_id: Module identifier
            - module_name: Name of module
            - day_start: Start day of module
            - day_end: End day of module
            - topics: Topics in module
            - key_skills: Key skills for module
    """
    if curriculum is None:
        try:
            curriculum = load_curriculum()
        except Exception:
            return None

    # Normalize mission title for matching
    mission_lower = mission_title.lower()

    # Try exact/fuzzy match on topics or module names
    for module in curriculum.modules:
        module_topics_str = " ".join(module.topics).lower()
        if mission_lower in module_topics_str or any(
            word in mission_lower for word in module.topics if word
        ):
            return {
                "module_id": module.module_id,
                "module_name": module.module_name,
                "day_start": module.days.start,
                "day_end": module.days.end,
                "topics": module.topics,
                "key_skills": module.key_skills,
            }

    # Fallback: try matching by key words
    for module in curriculum.modules:
        if any(
            keyword in mission_lower
            for keyword in module.module_name.lower().split()
        ):
            return {
                "module_id": module.module_id,
                "module_name": module.module_name,
                "day_start": module.days.start,
                "day_end": module.days.end,
                "topics": module.topics,
                "key_skills": module.key_skills,
            }

    return None


def get_candidate_curriculum_coverage(
    candidate: CandidateModel, curriculum: Optional[CurriculumModel] = None
) -> dict[str, Any]:
    """
    Analyze which curriculum modules a candidate has covered via missions.

    Args:
        candidate: CandidateModel instance
        curriculum: CurriculumModel (loads if not provided)

    Returns:
        Dictionary with coverage info:
            - total_modules: Total modules in curriculum
            - covered_modules: Number of modules with completed missions
            - partial_modules: Modules with any mission attempted
            - covered_module_names: List of covered module names
            - uncovered_module_names: List of uncovered module names
            - coverage_percentage: % of modules covered
    """
    if curriculum is None:
        try:
            curriculum = load_curriculum()
        except Exception:
            return {
                "total_modules": 0,
                "covered_modules": 0,
                "partial_modules": 0,
                "covered_module_names": [],
                "uncovered_module_names": [],
                "coverage_percentage": 0.0,
            }

    covered_modules = set()
    partial_modules = set()

    for mission in candidate.missions or []:
        mapping = map_mission_to_curriculum(mission.title, curriculum)
        if mapping:
            if mission.passed:
                covered_modules.add(mapping["module_name"])
            else:
                partial_modules.add(mapping["module_name"])

    all_module_names = {m.module_name for m in curriculum.modules}
    uncovered_modules = all_module_names - covered_modules - partial_modules

    total_modules = len(all_module_names)
    coverage_pct = (len(covered_modules) / total_modules * 100) if total_modules > 0 else 0.0

    return {
        "total_modules": total_modules,
        "covered_modules": len(covered_modules),
        "partial_modules": len(partial_modules),
        "covered_module_names": sorted(list(covered_modules)),
        "uncovered_module_names": sorted(list(uncovered_modules)),
        "coverage_percentage": round(coverage_pct, 2),
    }


# ============================================================================
# EVALUATION METRICS
# ============================================================================


def calculate_evaluation_metrics(candidate: CandidateModel) -> dict[str, Any]:
    """
    Calculate standardized evaluation metrics for a candidate.

    Combines progress metrics with curriculum mapping for comprehensive evaluation.

    Args:
        candidate: CandidateModel instance

    Returns:
        Dictionary with evaluation scores:
            - mission_completion_rate: % missions passed
            - first_try_rate: % first attempts successful
            - pass_rate: % attempted missions passed
            - skipped_mission_count: Number of skipped missions
            - failed_mission_count: Number of failed missions
            - average_attempts: Average attempts per mission
            - commit_activity_score: Based on commit days (0-100)
            - curriculum_coverage_score: Based on modules covered (0-100)
            - overall_performance_score: Weighted combination (0-100)
    """
    progress = calculate_candidate_progress(candidate)
    curriculum = load_curriculum()
    coverage = get_candidate_curriculum_coverage(candidate, curriculum)

    # Commit activity: normalize to 0-100
    max_possible_commits = progress["attempted_missions"] or 1
    commit_score = min(
        100.0, (progress["total_commit_days"] / max(max_possible_commits, 1)) * 100
    )

    # Coverage score
    coverage_score = coverage["coverage_percentage"]

    # Combine metrics: 40% completion + 30% commit activity + 30% coverage
    overall_score = (
        progress["pass_rate"] * 0.4 +
        commit_score * 0.3 +
        coverage_score * 0.3
    )

    return {
        "mission_completion_rate": progress["pass_rate"],
        "first_try_rate": progress["first_try_rate"],
        "pass_rate": progress["pass_rate"],
        "skipped_mission_count": progress["skipped_missions"],
        "failed_mission_count": progress["failed_missions"],
        "average_attempts": progress["average_attempts"],
        "commit_activity_score": round(commit_score, 2),
        "curriculum_coverage_score": coverage_score,
        "overall_performance_score": round(overall_score, 2),
    }


# ============================================================================
# CANDIDATE ANALYSIS
# ============================================================================


def analyze_candidate(candidate: CandidateModel, curriculum: Optional[CurriculumModel] = None) -> dict[str, Any]:
    """
    Generate comprehensive structured analysis for a candidate.

    Combines profile, progress, strengths, gaps, and technical topics.

    Args:
        candidate: CandidateModel instance
        curriculum: CurriculumModel (loads if not provided)

    Returns:
        Dictionary with analysis:
            - profile: Name, role, experience, education
            - progress: Completion metrics
            - metrics: Evaluation scores
            - strengths: Skills and achieved areas
            - gaps: Areas needing improvement
            - technical_topics: Relevant curriculum topics
            - interview_focus: Recommended interview areas
    """
    if curriculum is None:
        try:
            curriculum = load_curriculum()
        except Exception:
            curriculum = None

    progress = calculate_candidate_progress(candidate)
    metrics = calculate_evaluation_metrics(candidate)
    coverage = get_candidate_curriculum_coverage(candidate, curriculum) if curriculum else {}

    # Identify strengths: high-scoring areas from metrics
    strengths = []
    if metrics["pass_rate"] >= 75:
        strengths.append("Strong mission completion rate")
    if metrics["first_try_rate"] >= 70:
        strengths.append("Excellent first-attempt success")
    if metrics["commit_activity_score"] >= 80:
        strengths.append("Consistent daily commitment")
    strengths.extend(candidate.skills[:3])  # Top 3 technical skills

    # Identify gaps: areas not covered or with failures
    gaps = []
    if progress["failed_missions"] > 0:
        failed_titles = [m.title for m in candidate.missions if not m.passed and not m.skipped]
        gaps.append(f"Struggled with: {', '.join(failed_titles[:2])}")
    if progress["completion_rate"] < 75:
        gaps.append("Needs to improve overall completion rate")
    gaps.extend(candidate.growth_areas[:2])  # Top 2 growth areas

    # Technical topics: covered + next recommended
    covered_topics = []
    if curriculum:
        for module in curriculum.modules:
            if module.module_name in coverage.get("covered_module_names", []):
                covered_topics.extend(module.topics[:2])
    covered_topics = list(set(covered_topics))[:5]  # Unique, top 5

    uncovered_topics = []
    if curriculum:
        for module in curriculum.modules:
            if module.module_name in coverage.get("uncovered_module_names", []):
                uncovered_topics.extend(module.topics[:2])
    uncovered_topics = list(set(uncovered_topics))[:3]  # Unique, top 3

    # Interview focus: based on strengths and gaps
    interview_focus = []
    if metrics["pass_rate"] < 80:
        interview_focus.append("Problem-solving approach and debugging strategies")
    if "system design" in " ".join(candidate.growth_areas).lower():
        interview_focus.append("System design and scalability")
    if progress["average_attempts"] > 1.5:
        interview_focus.append("First-attempt solution design")
    if not interview_focus:
        interview_focus.append("Advanced technical depth in core areas")

    return {
        "profile": {
            "id": candidate.id,
            "name": candidate.name,
            "role": candidate.role,
            "experience_years": candidate.experience,
            "education": candidate.education or "Not specified",
        },
        "progress": progress,
        "metrics": metrics,
        "strengths": strengths,
        "gaps": gaps,
        "technical_topics": {
            "covered": covered_topics,
            "next_focus": uncovered_topics,
        },
        "curriculum_coverage": coverage,
        "interview_focus": interview_focus,
        "learning_signals": {
            "engagement": "High" if progress["total_commit_days"] >= progress["attempted_missions"] else "Moderate",
            "consistency": "Strong" if metrics["commit_activity_score"] >= 75 else "Needs improvement",
            "problem_solving": "Strong" if metrics["first_try_rate"] >= 70 else "Needs practice",
        },
    }


# ============================================================================
# PROMPT CONTEXT FORMATTING
# ============================================================================


def format_candidate_context(candidate: CandidateModel) -> str:
    """
    Format candidate analysis into concise structured text for LLM prompts.

    Args:
        candidate: CandidateModel instance

    Returns:
        Formatted string suitable for inclusion in LLM prompts
    """
    analysis = analyze_candidate(candidate)
    profile = analysis["profile"]
    progress = analysis["progress"]
    metrics = analysis["metrics"]
    strengths = analysis["strengths"]
    gaps = analysis["gaps"]
    topics = analysis["technical_topics"]
    focus = analysis["interview_focus"]

    context = f"""CANDIDATE PROFILE:
Name: {profile['name']}
Role: {profile['role']}
Experience: {profile['experience_years']} years
Education: {profile['education']}

PROGRESS:
- Completed: {progress['passed_missions']}/{progress['attempted_missions']} missions ({metrics['mission_completion_rate']:.1f}%)
- First-try success: {metrics['first_try_rate']:.1f}%
- Average attempts: {metrics['average_attempts']:.1f}
- Commit activity: {progress['total_commit_days']} distinct days
- Overall progress: Day {progress['current_day']}/31 ({progress['progress_percentage']:.1f}%)

STRENGTHS:
{chr(10).join(f"- {s}" for s in strengths)}

GROWTH AREAS:
{chr(10).join(f"- {g}" for g in gaps)}

TECHNICAL TOPICS COVERED:
{chr(10).join(f"- {t}" for t in topics['covered'])}

RECOMMENDED INTERVIEW FOCUS:
{chr(10).join(f"- {f}" for f in focus)}

OVERALL SCORE: {metrics['overall_performance_score']:.1f}/100
"""
    return context.strip()


def format_candidate_context_json(candidate: CandidateModel) -> dict[str, Any]:
    """
    Format candidate analysis as structured JSON for API responses.

    Args:
        candidate: CandidateModel instance

    Returns:
        Dictionary suitable for JSON serialization
    """
    return analyze_candidate(candidate)
