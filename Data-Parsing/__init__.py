"""
Data-Parsing module for The Interview Agent.

Provides data ingestion, validation, analysis, and context formatting
for candidate evaluation and interview preparation.

Core exports:
- load_candidates(): Load and validate candidate data
- load_curriculum(): Load and validate curriculum structure
- calculate_candidate_progress(): Analyze mission completion
- calculate_evaluation_metrics(): Compute performance scores
- analyze_candidate(): Generate comprehensive candidate analysis
- format_candidate_context(): Format data for LLM prompts
"""

from data_logic import (
    analyze_candidate,
    calculate_candidate_progress,
    calculate_evaluation_metrics,
    format_candidate_context,
    format_candidate_context_json,
    get_candidate,
    get_candidate_curriculum_coverage,
    load_candidates,
    load_curriculum,
    map_mission_to_curriculum,
)
from validators import (
    CandidateModel,
    CandidatesPayloadModel,
    CurriculumDayRangeModel,
    CurriculumModel,
    CurriculumModuleModel,
    CurriculumPayloadModel,
    MissionModel,
)

__all__ = [
    # Data loading
    "load_candidates",
    "load_curriculum",
    "get_candidate",
    # Progress and metrics
    "calculate_candidate_progress",
    "calculate_evaluation_metrics",
    "get_candidate_curriculum_coverage",
    # Analysis
    "analyze_candidate",
    "map_mission_to_curriculum",
    # Formatting
    "format_candidate_context",
    "format_candidate_context_json",
    # Validators
    "CandidateModel",
    "MissionModel",
    "CurriculumModel",
    "CurriculumModuleModel",
    "CurriculumDayRangeModel",
    "CandidatesPayloadModel",
    "CurriculumPayloadModel",
]

__version__ = "1.0.0"
