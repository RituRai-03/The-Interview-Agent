"""
Comprehensive tests for data_logic module.

Tests cover:
- JSON loading and validation
- Progress calculation (pass/fail/skip scenarios)
- Curriculum mapping
- Evaluation metrics
- Candidate analysis
- Context formatting
- Error handling
"""

import json
import tempfile
from pathlib import Path

import pytest

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
from validators import CandidateModel, CurriculumModel, MissionModel


class TestJSONLoading:
    """Test JSON loading with valid and invalid data."""

    def test_load_candidates_success(self):
        """Test loading valid candidates.json."""
        candidates = load_candidates()
        assert isinstance(candidates, list)
        assert len(candidates) >= 2
        assert all(isinstance(c, CandidateModel) for c in candidates)
        assert candidates[0].id == "candidate-001"

    def test_load_curriculum_success(self):
        """Test loading valid curriculum.json."""
        curriculum = load_curriculum()
        assert isinstance(curriculum, CurriculumModel)
        assert curriculum.title
        assert len(curriculum.modules) == 8
        assert curriculum.total_days == 31

    def test_load_candidates_missing_file(self):
        """Test loading from non-existent path."""
        with pytest.raises(FileNotFoundError):
            load_candidates("/nonexistent/path/candidates.json")

    def test_load_curriculum_missing_file(self):
        """Test loading from non-existent path."""
        with pytest.raises(FileNotFoundError):
            load_curriculum("/nonexistent/path/curriculum.json")

    def test_load_candidates_malformed_json(self):
        """Test handling malformed JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                load_candidates(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_candidates_invalid_schema(self):
        """Test handling data that doesn't match schema."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"candidates": [{"id": "test"}]}, f)  # Missing required fields
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError):
                load_candidates(temp_path)
        finally:
            Path(temp_path).unlink()


class TestCandidateLookup:
    """Test candidate lookup functionality."""

    def test_get_candidate_found(self):
        """Test retrieving existing candidate."""
        candidate = get_candidate("candidate-001")
        assert candidate is not None
        assert candidate.id == "candidate-001"
        assert candidate.name == "Aarav Sharma"

    def test_get_candidate_not_found(self):
        """Test retrieving non-existent candidate."""
        candidate = get_candidate("nonexistent-id")
        assert candidate is None

    def test_get_candidate_multiple_exists(self):
        """Test that all seed candidates can be retrieved."""
        candidate_ids = ["candidate-001", "candidate-002", "candidate-003"]
        for cid in candidate_ids:
            candidate = get_candidate(cid)
            assert candidate is not None
            assert candidate.id == cid


class TestProgressCalculation:
    """Test progress calculation with various mission scenarios."""

    def test_progress_all_passed(self):
        """Test progress when all missions are passed."""
        missions = [
            MissionModel(title="Mission 1", day=1, passed=True, attempts=1),
            MissionModel(title="Mission 2", day=2, passed=True, attempts=1),
            MissionModel(title="Mission 3", day=3, passed=True, attempts=1),
        ]
        candidate = CandidateModel(id="test", name="Test", role="Engineer", experience=1, missions=missions)
        
        progress = calculate_candidate_progress(candidate)
        assert progress["total_missions"] == 3
        assert progress["passed_missions"] == 3
        assert progress["completion_rate"] == 100.0
        assert progress["pass_rate"] == 100.0
        assert progress["first_try_rate"] == 100.0
        assert progress["failed_missions"] == 0
        assert progress["skipped_missions"] == 0

    def test_progress_with_failures(self):
        """Test progress when some missions fail."""
        missions = [
            MissionModel(title="Mission 1", day=1, passed=True, attempts=1),
            MissionModel(title="Mission 2", day=2, passed=False, attempts=2),
            MissionModel(title="Mission 3", day=3, passed=True, attempts=1),
        ]
        candidate = CandidateModel(id="test", name="Test", role="Engineer", experience=1, missions=missions)
        
        progress = calculate_candidate_progress(candidate)
        assert progress["total_missions"] == 3
        assert progress["passed_missions"] == 2
        assert progress["failed_missions"] == 1
        assert progress["completion_rate"] == 66.67
        assert progress["pass_rate"] == 66.67

    def test_progress_with_skipped(self):
        """Test progress with skipped missions (not counted)."""
        missions = [
            MissionModel(title="Mission 1", day=1, passed=True, attempts=1),
            MissionModel(title="Mission 2", day=2, passed=True, skipped=True, attempts=1),
            MissionModel(title="Mission 3", day=3, passed=True, attempts=1),
        ]
        candidate = CandidateModel(id="test", name="Test", role="Engineer", experience=1, missions=missions)
        
        progress = calculate_candidate_progress(candidate)
        assert progress["total_missions"] == 3
        assert progress["skipped_missions"] == 1
        assert progress["attempted_missions"] == 2
        # Completion should only count non-skipped attempts
        assert progress["completion_rate"] == 100.0

    def test_progress_mixed_scenario(self):
        """Test complex scenario with passed, failed, and skipped."""
        missions = [
            MissionModel(title="Mission 1", day=1, passed=True, attempts=1, commit_days=1),
            MissionModel(title="Mission 2", day=2, passed=False, attempts=3, commit_days=2),
            MissionModel(title="Mission 3", day=3, passed=False, skipped=True, attempts=1, commit_days=0),
            MissionModel(title="Mission 4", day=4, passed=True, attempts=2, commit_days=2),
        ]
        candidate = CandidateModel(id="test", name="Test", role="Engineer", experience=1, missions=missions)
        
        progress = calculate_candidate_progress(candidate)
        assert progress["total_missions"] == 4
        assert progress["attempted_missions"] == 3
        assert progress["passed_missions"] == 2
        assert progress["failed_missions"] == 1
        assert progress["skipped_missions"] == 1
        assert progress["total_attempts"] == 6  # 1 + 3 + 1 + 2
        assert progress["total_commit_days"] == 5  # 1 + 2 + 0 + 2
        assert progress["average_attempts"] == 2.0  # (1+3+2)/3
        assert progress["first_try_rate"] == 50.0  # Only 1st mission was first-try

    def test_progress_empty_missions(self):
        """Test progress with no missions."""
        candidate = CandidateModel(id="test", name="Test", role="Engineer", experience=1, missions=[])
        
        progress = calculate_candidate_progress(candidate)
        assert progress["total_missions"] == 0
        assert progress["completion_rate"] == 0.0
        assert progress["pass_rate"] == 0.0
        assert progress["progress_percentage"] == 0.0


class TestCurriculumMapping:
    """Test curriculum mapping and module coverage."""

    def test_map_mission_to_module_by_topic(self):
        """Test mapping mission to curriculum module by topic."""
        mapping = map_mission_to_curriculum("Python Fundamentals - Part 1")
        assert mapping is not None
        assert "module_name" in mapping
        assert "Python" in mapping["module_name"] or "Data Foundations" in mapping["module_name"]

    def test_map_mission_not_found(self):
        """Test unmappable mission title."""
        mapping = map_mission_to_curriculum("Nonexistent Mission Topic")
        assert mapping is None or "module_name" in mapping  # Either None or best guess

    def test_curriculum_coverage_all_covered(self):
        """Test coverage when all modules have passed missions."""
        curriculum = load_curriculum()
        candidates = load_candidates()
        candidate = candidates[0]  # Use real candidate
        
        coverage = get_candidate_curriculum_coverage(candidate, curriculum)
        assert "total_modules" in coverage
        assert coverage["total_modules"] == 8
        assert coverage["covered_modules"] >= 0
        assert coverage["coverage_percentage"] >= 0

    def test_curriculum_coverage_empty_candidate(self):
        """Test coverage for candidate with no missions."""
        curriculum = load_curriculum()
        candidate = CandidateModel(id="empty", name="Empty", role="Role", experience=0, missions=[])
        
        coverage = get_candidate_curriculum_coverage(candidate, curriculum)
        assert coverage["covered_modules"] == 0
        assert coverage["coverage_percentage"] == 0.0


class TestEvaluationMetrics:
    """Test evaluation metric calculations."""

    def test_metrics_basic(self):
        """Test basic metric calculation."""
        missions = [
            MissionModel(title="M1", day=1, passed=True, attempts=1, commit_days=1),
            MissionModel(title="M2", day=2, passed=True, attempts=2, commit_days=2),
            MissionModel(title="M3", day=3, passed=False, attempts=3, commit_days=1),
        ]
        candidate = CandidateModel(id="test", name="Test", role="Engineer", experience=1, missions=missions)
        
        metrics = calculate_evaluation_metrics(candidate)
        assert "mission_completion_rate" in metrics
        assert "first_try_rate" in metrics
        assert "commit_activity_score" in metrics
        assert "overall_performance_score" in metrics
        assert 0 <= metrics["overall_performance_score"] <= 100

    def test_metrics_with_real_candidate(self):
        """Test metrics with actual seed candidate."""
        candidate = get_candidate("candidate-001")
        assert candidate is not None
        
        metrics = calculate_evaluation_metrics(candidate)
        assert isinstance(metrics, dict)
        assert all(isinstance(v, (int, float)) for v in metrics.values())


class TestCandidateAnalysis:
    """Test comprehensive candidate analysis."""

    def test_analysis_structure(self):
        """Test that analysis produces correct structure."""
        candidate = get_candidate("candidate-001")
        assert candidate is not None
        
        analysis = analyze_candidate(candidate)
        assert "profile" in analysis
        assert "progress" in analysis
        assert "metrics" in analysis
        assert "strengths" in analysis
        assert "gaps" in analysis
        assert "technical_topics" in analysis
        assert "interview_focus" in analysis
        assert "learning_signals" in analysis

    def test_analysis_profile(self):
        """Test analysis profile section."""
        candidate = get_candidate("candidate-002")
        assert candidate is not None
        
        analysis = analyze_candidate(candidate)
        profile = analysis["profile"]
        assert profile["id"] == "candidate-002"
        assert profile["name"] == "Mia Johnson"
        assert profile["role"] == "Data Engineer"
        assert profile["experience_years"] == 3

    def test_analysis_strengths_gaps(self):
        """Test that strengths and gaps are populated."""
        candidate = get_candidate("candidate-001")
        assert candidate is not None
        
        analysis = analyze_candidate(candidate)
        assert len(analysis["strengths"]) > 0
        assert len(analysis["gaps"]) > 0
        assert len(analysis["technical_topics"]["covered"]) >= 0
        assert len(analysis["interview_focus"]) > 0


class TestContextFormatting:
    """Test prompt context formatting."""

    def test_format_context_text(self):
        """Test text format context output."""
        candidate = get_candidate("candidate-001")
        assert candidate is not None
        
        context = format_candidate_context(candidate)
        assert isinstance(context, str)
        assert "CANDIDATE PROFILE:" in context
        assert "PROGRESS:" in context
        assert "STRENGTHS:" in context
        assert "GROWTH AREAS:" in context
        assert candidate.name in context

    def test_format_context_json(self):
        """Test JSON format context output."""
        candidate = get_candidate("candidate-002")
        assert candidate is not None
        
        context_json = format_candidate_context_json(candidate)
        assert isinstance(context_json, dict)
        assert "profile" in context_json
        assert "progress" in context_json
        assert "metrics" in context_json


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_pipeline_candidate_001(self):
        """Test complete analysis pipeline for candidate-001."""
        candidate = get_candidate("candidate-001")
        assert candidate is not None
        assert candidate.name == "Aarav Sharma"
        
        progress = calculate_candidate_progress(candidate)
        assert progress["total_missions"] > 0
        
        metrics = calculate_evaluation_metrics(candidate)
        assert metrics["overall_performance_score"] >= 0
        
        analysis = analyze_candidate(candidate)
        assert analysis["profile"]["name"] == "Aarav Sharma"
        
        context = format_candidate_context(candidate)
        assert "Aarav Sharma" in context

    def test_full_pipeline_candidate_002(self):
        """Test complete analysis pipeline for candidate-002."""
        candidate = get_candidate("candidate-002")
        assert candidate is not None
        
        progress = calculate_candidate_progress(candidate)
        metrics = calculate_evaluation_metrics(candidate)
        analysis = analyze_candidate(candidate)
        context_json = format_candidate_context_json(candidate)
        
        assert progress["total_missions"] > 0
        assert metrics["overall_performance_score"] >= 0
        assert "profile" in analysis
        assert "profile" in context_json

    def test_all_candidates_valid(self):
        """Test that all seed candidates can be fully analyzed."""
        candidates = load_candidates()
        assert len(candidates) >= 3
        
        for candidate in candidates:
            # Each candidate should be analyzable
            progress = calculate_candidate_progress(candidate)
            metrics = calculate_evaluation_metrics(candidate)
            analysis = analyze_candidate(candidate)
            context = format_candidate_context(candidate)
            
            assert isinstance(progress, dict)
            assert isinstance(metrics, dict)
            assert isinstance(analysis, dict)
            assert isinstance(context, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
