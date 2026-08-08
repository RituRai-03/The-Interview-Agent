# Data-Parsing Module

**Data ingestion, validation, analysis, and context formatting for The Interview Agent.**

This module handles all candidate data management, progress tracking, curriculum mapping, and evaluation metrics. It provides a clean, type-safe interface for the Backend to analyze candidates and generate interview context.

## Overview

The Data-Parsing module is responsible for:

- 📥 **Data Loading** - Safe loading and validation of candidate and curriculum JSON files
- ✅ **Validation** - Type-safe Pydantic models for data integrity
- 📊 **Progress Tracking** - Calculate mission completion rates, attempt counts, commit activity
- 🎯 **Evaluation Metrics** - Performance scoring (0-100 scale)
- 📚 **Curriculum Mapping** - Link candidate missions to curriculum modules
- 🔍 **Candidate Analysis** - Generate comprehensive profiles with strengths, gaps, and focus areas
- 💬 **Context Formatting** - Convert analysis to LLM-ready text and JSON formats

## Installation

### Prerequisites

- Python 3.10+
- Pydantic v2

### Setup

```bash
# Install dependencies
pip install pydantic python-dotenv

# Run tests (optional)
pip install pytest
pytest test_data_logic.py -v
```

## Quick Start

### Basic Usage

```python
from Data-Parsing import (
    load_candidates,
    get_candidate,
    analyze_candidate,
    format_candidate_context
)

# Load all candidates
candidates = load_candidates()

# Get specific candidate
candidate = get_candidate("candidate-001")

# Generate comprehensive analysis
analysis = analyze_candidate(candidate)
print(analysis["profile"])      # Name, role, experience, education
print(analysis["progress"])     # Mission metrics
print(analysis["metrics"])      # Performance scores
print(analysis["strengths"])    # Strengths list
print(analysis["gaps"])         # Growth areas
print(analysis["interview_focus"])  # Recommended focus areas

# Format for LLM prompts
context = format_candidate_context(candidate)
print(context)  # Text formatted for inclusion in prompts
```

### API Integration Example

```python
from fastapi import FastAPI, HTTPException
from Data-Parsing import get_candidate, analyze_candidate, format_candidate_context_json

app = FastAPI()

@app.post("/api/interview")
def create_interview_session(payload):
    # Validate candidate exists
    candidate_data = get_candidate(payload.candidate_id)
    if not candidate_data:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Generate analysis
    analysis = analyze_candidate(candidate_data)
    
    # Include in response
    return {
        "session_id": session_id,
        "candidate_id": payload.candidate_id,
        "analysis": analysis,
        "status": "active"
    }
```

## Core API

### Data Loading

#### `load_candidates(filepath=None) -> List[CandidateModel]`

Load and validate candidates from JSON file.

**Args:**
- `filepath` (str, optional): Path to candidates.json. Defaults to `Backend/candidates.json`

**Returns:**
- List of validated `CandidateModel` instances

**Raises:**
- `FileNotFoundError`: If candidates.json not found
- `json.JSONDecodeError`: If JSON is malformed
- `ValueError`: If data doesn't match schema

**Example:**
```python
candidates = load_candidates()
print(f"Loaded {len(candidates)} candidates")

# Custom path
candidates = load_candidates("/path/to/custom/candidates.json")
```

#### `load_curriculum(filepath=None) -> CurriculumModel`

Load and validate curriculum from JSON file.

**Args:**
- `filepath` (str, optional): Path to curriculum.json. Defaults to `Backend/curriculum.json`

**Returns:**
- Validated `CurriculumModel` instance

**Raises:**
- `FileNotFoundError`: If curriculum.json not found
- `json.JSONDecodeError`: If JSON is malformed
- `ValueError`: If data doesn't match schema

**Example:**
```python
curriculum = load_curriculum()
print(f"Loaded curriculum: {curriculum.title}")
print(f"Total days: {curriculum.total_days}")
print(f"Modules: {len(curriculum.modules)}")
```

### Candidate Lookup

#### `get_candidate(candidate_id: str) -> Optional[CandidateModel]`

Retrieve a single candidate by ID.

**Args:**
- `candidate_id` (str): Unique candidate identifier

**Returns:**
- `CandidateModel` if found, `None` otherwise

**Example:**
```python
candidate = get_candidate("candidate-001")
if candidate:
    print(f"Found: {candidate.name}")
else:
    print("Candidate not found")
```

### Progress Calculation

#### `calculate_candidate_progress(candidate: CandidateModel) -> Dict[str, Any]`

Calculate comprehensive progress metrics for a candidate.

**Args:**
- `candidate` (CandidateModel): Candidate instance

**Returns:**
Dict with keys:
- `total_missions`: Total missions assigned
- `completed_missions`: Successfully passed missions
- `passed_missions`: Missions with `passed=True`
- `failed_missions`: Missions with `passed=False` (not skipped)
- `skipped_missions`: Missions with `skipped=True`
- `attempted_missions`: Missions that were not skipped
- `completion_rate`: % of non-skipped missions completed
- `pass_rate`: % of attempted missions passed
- `first_try_rate`: % of passed missions completed on first attempt
- `average_attempts`: Average attempts for attempted missions
- `total_attempts`: Sum of all attempts
- `total_commit_days`: Sum of distinct commit days
- `current_day`: Highest day reached
- `progress_percentage`: Overall progress (0-100)

**Example:**
```python
progress = calculate_candidate_progress(candidate)
print(f"Completion rate: {progress['completion_rate']}%")
print(f"First-try success: {progress['first_try_rate']}%")
print(f"Current progress: Day {progress['current_day']}/31")
```

### Curriculum Mapping

#### `map_mission_to_curriculum(mission_title: str, curriculum=None) -> Optional[Dict]`

Map a mission title to its corresponding curriculum module.

**Args:**
- `mission_title` (str): Title of mission to map
- `curriculum` (CurriculumModel, optional): Curriculum model. Loads if not provided

**Returns:**
Dict with module info or `None` if not found:
- `module_id`: Module identifier
- `module_name`: Name of module
- `day_start`: Start day of module
- `day_end`: End day of module
- `topics`: Topics in module
- `key_skills`: Key skills for module

**Example:**
```python
mapping = map_mission_to_curriculum("Python Fundamentals - Part 1")
if mapping:
    print(f"Module: {mapping['module_name']}")
    print(f"Topics: {', '.join(mapping['topics'])}")
```

#### `get_candidate_curriculum_coverage(candidate: CandidateModel, curriculum=None) -> Dict[str, Any]`

Analyze which curriculum modules a candidate has covered.

**Args:**
- `candidate` (CandidateModel): Candidate instance
- `curriculum` (CurriculumModel, optional): Curriculum model. Loads if not provided

**Returns:**
Dict with:
- `total_modules`: Total modules in curriculum
- `covered_modules`: Number of modules with completed missions
- `partial_modules`: Modules with any mission attempted
- `covered_module_names`: List of covered module names
- `uncovered_module_names`: List of uncovered module names
- `coverage_percentage`: % of modules covered

**Example:**
```python
coverage = get_candidate_curriculum_coverage(candidate)
print(f"Coverage: {coverage['coverage_percentage']}%")
print(f"Covered modules: {coverage['covered_module_names']}")
print(f"Next focus: {coverage['uncovered_module_names']}")
```

### Evaluation Metrics

#### `calculate_evaluation_metrics(candidate: CandidateModel) -> Dict[str, Any]`

Calculate standardized evaluation metrics for a candidate.

**Args:**
- `candidate` (CandidateModel): Candidate instance

**Returns:**
Dict with:
- `mission_completion_rate`: % missions passed
- `first_try_rate`: % first attempts successful
- `pass_rate`: % attempted missions passed
- `skipped_mission_count`: Number of skipped missions
- `failed_mission_count`: Number of failed missions
- `average_attempts`: Average attempts per mission
- `commit_activity_score`: Score based on commit days (0-100)
- `curriculum_coverage_score`: Score based on modules covered (0-100)
- `overall_performance_score`: Weighted combination (0-100)

**Scoring Formula:**
```
overall_score = (pass_rate × 0.4) + (commit_activity × 0.3) + (coverage × 0.3)
```

**Example:**
```python
metrics = calculate_evaluation_metrics(candidate)
print(f"Overall score: {metrics['overall_performance_score']}/100")
print(f"Commit activity: {metrics['commit_activity_score']}/100")
print(f"Coverage: {metrics['curriculum_coverage_score']}/100")
```

### Candidate Analysis

#### `analyze_candidate(candidate: CandidateModel, curriculum=None) -> Dict[str, Any]`

Generate comprehensive structured analysis for a candidate.

**Args:**
- `candidate` (CandidateModel): Candidate instance
- `curriculum` (CurriculumModel, optional): Curriculum model. Loads if not provided

**Returns:**
Dict with:
- `profile`: Candidate info (id, name, role, experience_years, education)
- `progress`: Progress metrics
- `metrics`: Evaluation scores
- `strengths`: List of strengths (skills + performance-based)
- `gaps`: List of growth areas
- `technical_topics`: Dict with `covered` and `next_focus` topics
- `curriculum_coverage`: Module coverage details
- `interview_focus`: Personalized interview focus areas
- `learning_signals`: Dict with `engagement`, `consistency`, `problem_solving` levels

**Example:**
```python
analysis = analyze_candidate(candidate)

print("Profile:")
print(f"  Name: {analysis['profile']['name']}")
print(f"  Role: {analysis['profile']['role']}")
print(f"  Experience: {analysis['profile']['experience_years']} years")

print("Strengths:")
for strength in analysis['strengths']:
    print(f"  - {strength}")

print("Interview Focus:")
for focus in analysis['interview_focus']:
    print(f"  - {focus}")
```

### Context Formatting

#### `format_candidate_context(candidate: CandidateModel) -> str`

Format candidate analysis into text for LLM prompts.

**Args:**
- `candidate` (CandidateModel): Candidate instance

**Returns:**
- Formatted string with sections: PROFILE, PROGRESS, STRENGTHS, GROWTH AREAS, TECHNICAL TOPICS, INTERVIEW FOCUS, OVERALL SCORE

**Example:**
```python
context = format_candidate_context(candidate)
print(context)

# Use in LLM prompt
llm_prompt = f"""
You are a technical interviewer. Here's the candidate information:

{context}

Generate an appropriate interview question based on this profile.
"""
response = llm.generate(llm_prompt)
```

#### `format_candidate_context_json(candidate: CandidateModel) -> Dict[str, Any]`

Format candidate analysis as structured JSON.

**Args:**
- `candidate` (CandidateModel): Candidate instance

**Returns:**
- Dictionary with same structure as `analyze_candidate()`, suitable for JSON serialization

**Example:**
```python
import json

context_json = format_candidate_context_json(candidate)
json_string = json.dumps(context_json, indent=2)

# Include in API response
return {"candidate_analysis": context_json}
```

## Data Models

### CandidateModel

Represents a candidate profile with mission tracking.

```python
from Data-Parsing import CandidateModel, MissionModel

candidate = CandidateModel(
    id="candidate-001",
    name="Aarav Sharma",
    role="Full-stack Engineer",
    experience=2,
    education="B.S. Computer Science",
    metrics={
        "technical_score": 78,
        "communication_score": 88,
    },
    skills=["Python", "FastAPI", "JavaScript"],
    growth_areas=["system design", "testing"],
    missions=[
        MissionModel(
            title="Python Fundamentals",
            day=1,
            passed=True,
            attempts=1,
            commit_days=1
        )
    ]
)
```

### MissionModel

Represents a single mission in the curriculum.

**Fields:**
- `title` (str): Mission title
- `day` (int): Curriculum day (1-31)
- `passed` (bool): Whether mission was passed
- `skipped` (bool): Whether mission was skipped
- `attempts` (int): Number of attempts
- `commit_days` (int): Number of distinct commit days

### CurriculumModel

Represents the complete 31-day curriculum.

**Fields:**
- `title` (str): Curriculum title
- `subtitle` (str, optional): Curriculum subtitle
- `total_days` (int): Total number of days (default: 31)
- `modules` (List[CurriculumModuleModel]): Curriculum modules
- `focus_areas` (List[str]): Focus areas
- `requirements` (Dict): Curriculum requirements

### CurriculumModuleModel

Represents a single module in the curriculum.

**Fields:**
- `module_id` (str): Unique module identifier
- `module_name` (str): Module name
- `days` (CurriculumDayRangeModel): Day range (start, end)
- `topics` (List[str]): Topics covered
- `key_skills` (List[str]): Key skills developed

## 31-Day Curriculum Structure

The curriculum consists of 8 modules:

1. **Environment & Tooling** (Days 1-2)
   - Command line, Git, Python environment setup

2. **Python & Data Foundations** (Days 3-8)
   - Python fundamentals, data structures, algorithms, Pandas, NumPy

3. **Embeddings & Vector Search** (Days 9-12)
   - Embeddings, vectors, vector databases, similarity search

4. **LLM Core, Prompting & Fine-Tuning** (Days 13-18)
   - LLM architecture, prompt engineering, fine-tuning, RAG

5. **Chatbot Application Build** (Days 19-22)
   - Chatbot architecture, conversation state, multi-turn interactions

6. **Agentic AI & MCP** (Days 23-25)
   - Agent architecture, tool integration, Model Context Protocol

7. **Evaluation, Security & Deployment** (Days 26-28)
   - Evaluation metrics, security, monitoring, observability

8. **Production & Capstone** (Days 29-31)
   - Production deployment, scaling, capstone project, interview prep

## Testing

The module includes comprehensive test coverage with 40+ tests.

### Run Tests

```bash
pytest test_data_logic.py -v
```

### Test Categories

- **JSON Loading** (5 tests): Valid files, missing files, malformed JSON, invalid schema
- **Candidate Lookup** (3 tests): Find candidates, non-existent IDs, all seed candidates
- **Progress Calculation** (5 tests): All passed, mixed scenarios, skipped missions, empty missions
- **Curriculum Mapping** (4 tests): Map missions, unmappable missions, coverage calculation
- **Evaluation Metrics** (2 tests): Basic metrics, metrics with real candidates
- **Candidate Analysis** (3 tests): Output structure, profile data, strengths/gaps
- **Context Formatting** (2 tests): Text format, JSON format
- **Integration** (3 tests): Full pipeline for each candidate, all candidates analyzable

### Example Test

```python
def test_progress_calculation():
    """Test progress calculation with realistic mission data."""
    from Data-Parsing import get_candidate, calculate_candidate_progress
    
    candidate = get_candidate("candidate-001")
    progress = calculate_candidate_progress(candidate)
    
    assert progress["total_missions"] > 0
    assert progress["completion_rate"] >= 0
    assert progress["pass_rate"] <= 100
```

## Error Handling

### Missing Files

```python
from Data-Parsing import load_candidates

try:
    candidates = load_candidates("/nonexistent/path.json")
except FileNotFoundError as e:
    print(f"Error: {e}")
    # Handle gracefully
```

### Malformed JSON

```python
import json

try:
    candidates = load_candidates()
except json.JSONDecodeError as e:
    print(f"JSON Error: {e}")
    # Handle gracefully
```

### Invalid Schema

```python
from pydantic import ValidationError

try:
    candidates = load_candidates()
except ValueError as e:
    print(f"Schema Error: {e}")
    # Handle gracefully
```

## Performance Considerations

- **Data Loading**: Loads JSON files once per call (consider caching if called frequently)
- **Analysis**: All calculations are deterministic and lightweight
- **Memory**: Holds all candidates in memory (acceptable for typical cohort sizes)
- **Scaling**: Tested with 3+ candidates; scales linearly

## Integration with Backend

### 1. Import Functions

```python
from Data-Parsing import (
    load_candidates,
    get_candidate,
    analyze_candidate,
    format_candidate_context,
    format_candidate_context_json,
    calculate_evaluation_metrics
)
```

### 2. Use in Endpoints

```python
@app.post("/api/interview")
def create_interview_session(payload):
    # Validate candidate
    candidate = get_candidate(payload.candidate_id)
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    
    # Get analysis
    analysis = analyze_candidate(candidate)
    
    # Return response
    return {
        "session_id": session_id,
        "candidate_analysis": analysis,
        "status": "active"
    }
```

### 3. Use in Question Generation

```python
def generate_interview_question(candidate):
    context = format_candidate_context(candidate)
    
    # Pass to LLM
    prompt = f"""
    You are a technical interviewer. Consider this candidate:
    
    {context}
    
    Generate an appropriate technical interview question.
    """
    
    return llm_client.generate(prompt)
```

## Troubleshooting

### Import Errors

```
ModuleNotFoundError: No module named 'Data-Parsing'
```

**Solution:** Ensure you're importing from the correct path:
```python
from Data-Parsing import load_candidates
# or
import sys
sys.path.insert(0, '/path/to/The-Interview-Agent')
from Data-Parsing import load_candidates
```

### File Not Found

```
FileNotFoundError: Candidates file not found: Backend/candidates.json
```

**Solution:** Ensure you're running from the correct directory:
```bash
cd /path/to/The-Interview-Agent
python your_script.py
```

### Pydantic Validation Errors

```
ValueError: Invalid candidate data structure
```

**Solution:** Validate JSON structure matches schema. Use example data from [Data Models](#data-models) section.

## Contributing

When adding new features:

1. Add function to `data_logic.py` with complete docstring
2. Add Pydantic models to `validators.py` if needed
3. Add tests to `test_data_logic.py` (follow existing patterns)
4. Update this README with function documentation

## License

Part of The Interview Agent project.

---

**Ready to integrate!** See [INTEGRATION.md](INTEGRATION.md) for backend integration details.
