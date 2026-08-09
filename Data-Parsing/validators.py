"""
Data validation and Pydantic models for candidates and curriculum.

This module provides type-safe validation for:
- Candidate profiles with mission tracking
- Curriculum modules and structure
- Mission completion data
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MissionModel(BaseModel):
    """Represents a single mission/assignment in the curriculum."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Python Fundamentals - Part 1",
                "day": 2,
                "passed": True,
                "skipped": False,
                "attempts": 1,
                "commit_days": 1,
            }
        }
    )

    title: str = Field(..., description="Mission title")
    day: int = Field(..., ge=1, le=31, description="Curriculum day (1-31)")
    passed: bool = Field(default=False, description="Whether mission was passed")
    skipped: bool = Field(default=False, description="Whether mission was skipped")
    attempts: int = Field(default=1, ge=1, description="Number of attempts")
    commit_days: int = Field(default=0, ge=0, description="Number of distinct commit days")

    @field_validator("passed", "skipped")
    @classmethod
    def validate_mission_status(cls, v: bool) -> bool:
        """Validate that mission status is boolean."""
        return v


class CandidateModel(BaseModel):
    """Represents a candidate profile with metrics and progress."""

    id: str = Field(..., description="Unique candidate identifier")
    name: str = Field(..., description="Candidate name")
    role: str = Field(..., description="Job role/title")
    experience: int = Field(..., ge=0, description="Years of experience")
    education: Optional[str] = Field(default=None, description="Education level")
    metrics: dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    skills: list[str] = Field(default_factory=list, description="Technical skills")
    growth_areas: list[str] = Field(default_factory=list, description="Areas for improvement")
    missions: list[MissionModel] = Field(default_factory=list, description="Mission completion data")

    @field_validator("missions", mode="before")
    @classmethod
    def validate_missions(cls, v: Any) -> list[MissionModel]:
        """Convert mission dicts to MissionModel if needed."""
        if not isinstance(v, list):
            return []
        return [MissionModel(**m) if isinstance(m, dict) else m for m in v]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "candidate-001",
                "name": "Aarav Sharma",
                "role": "Full-stack Engineer",
                "experience": 2,
                "education": "B.S. Computer Science",
                "metrics": {
                    "technical_score": 78,
                    "communication_score": 88,
                    "problem_solving_score": 70,
                    "project_completion": 85,
                },
                "skills": ["Python", "FastAPI", "JavaScript"],
                "growth_areas": ["system design", "testing"],
                "missions": [
                    {
                        "title": "Python Fundamentals",
                        "day": 1,
                        "passed": True,
                        "skipped": False,
                        "attempts": 1,
                        "commit_days": 1,
                    }
                ],
            }
        }
    )


class CurriculumDayRangeModel(BaseModel):
    """Represents day range for a curriculum module."""

    start: int = Field(..., ge=1, le=31, description="Start day (1-31)")
    end: int = Field(..., ge=1, le=31, description="End day (1-31)")

    @field_validator("end")
    @classmethod
    def validate_end_day(cls, v: int, info) -> int:
        """Ensure end day is not before start day."""
        if "start" in info.data and v < info.data["start"]:
            raise ValueError("end day must be >= start day")
        return v


class CurriculumModuleModel(BaseModel):
    """Represents a module in the 31-day curriculum."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "module_id": "m1",
                "module_name": "Environment & Tooling",
                "days": {"start": 1, "end": 2},
                "topics": ["Command line", "Git", "Python environment"],
                "key_skills": ["development environment", "git workflow"],
            }
        }
    )

    module_id: str = Field(..., description="Unique module identifier")
    module_name: str = Field(..., description="Module name")
    days: CurriculumDayRangeModel = Field(..., description="Day range for module")
    topics: list[str] = Field(default_factory=list, description="Topics covered")
    key_skills: list[str] = Field(default_factory=list, description="Key skills developed")


class CurriculumModel(BaseModel):
    """Represents the complete 31-day curriculum."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "31-Day AI Engineering Bootcamp",
                "total_days": 31,
                "modules": [
                    {
                        "module_id": "m1",
                        "module_name": "Environment & Tooling",
                        "days": {"start": 1, "end": 2},
                        "topics": ["Command line", "Git"],
                        "key_skills": ["development environment"],
                    }
                ],
                "focus_areas": ["Python", "APIs", "AI"],
                "requirements": {"minimum_progress": 75},
            }
        }
    )

    title: str = Field(..., description="Curriculum title")
    subtitle: Optional[str] = Field(default=None, description="Curriculum subtitle")
    total_days: int = Field(default=31, description="Total number of days")
    modules: list[CurriculumModuleModel] = Field(
        default_factory=list, description="Curriculum modules"
    )
    focus_areas: list[str] = Field(default_factory=list, description="Focus areas")
    requirements: dict[str, Any] = Field(default_factory=dict, description="Curriculum requirements")

    @field_validator("modules", mode="before")
    @classmethod
    def validate_modules(cls, v: Any) -> list[CurriculumModuleModel]:
        """Convert module dicts to CurriculumModuleModel if needed."""
        if not isinstance(v, list):
            return []
        return [CurriculumModuleModel(**m) if isinstance(m, dict) else m for m in v]


class CandidatesPayloadModel(BaseModel):
    """Represents the candidates.json payload structure."""

    candidates: list[CandidateModel] = Field(default_factory=list, description="List of candidates")


class CurriculumPayloadModel(BaseModel):
    """Represents the curriculum.json payload structure."""

    curriculum: CurriculumModel = Field(..., description="Curriculum data")
