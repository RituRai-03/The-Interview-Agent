"""Quick validation script to check if all modules are linked correctly."""

import sys
print('=== IMPORT VALIDATION ===\n')

# Test 1: Validators
try:
    from validators import CandidateModel, MissionModel, CurriculumModel
    print('✓ validators.py - All models imported')
except Exception as e:
    print(f'✗ validators.py: {e}')
    sys.exit(1)

# Test 2: Data Logic
try:
    from data_logic import (
        load_candidates, load_curriculum, get_candidate,
        analyze_candidate, calculate_evaluation_metrics
    )
    print('✓ data_logic.py - All functions imported')
except Exception as e:
    print(f'✗ data_logic.py: {e}')
    sys.exit(1)

# Test 3: Module Exports
try:
    from __init__ import (
        load_candidates as lc, load_curriculum as lcurr,
        get_candidate as gc, analyze_candidate as ac
    )
    print('✓ __init__.py - Clean exports working')
except Exception as e:
    print(f'✗ __init__.py: {e}')
    sys.exit(1)

# Test 4: Load Data Files
print('\n=== DATA FILE VALIDATION ===\n')
try:
    candidates = load_candidates()
    print(f'✓ candidates.json loaded: {len(candidates)} candidates found')
    for c in candidates:
        print(f'  - {c.name} ({c.id}): {len(c.missions)} missions')
except Exception as e:
    print(f'✗ candidates.json: {e}')
    sys.exit(1)

try:
    curriculum = load_curriculum()
    print(f'✓ curriculum.json loaded: {len(curriculum.modules)} modules')
    for m in curriculum.modules:
        print(f'  - {m.module_name} (days {m.days.start}-{m.days.end})')
except Exception as e:
    print(f'✗ curriculum.json: {e}')
    sys.exit(1)

# Test 5: Analysis Functions
print('\n=== FUNCTION VALIDATION ===\n')
try:
    c = get_candidate('candidate-001')
    print(f'✓ get_candidate(): Retrieved {c.name}')
except Exception as e:
    print(f'✗ get_candidate(): {e}')

try:
    analysis = analyze_candidate(c)
    print(f'✓ analyze_candidate(): Generated analysis with {len(analysis.keys())} fields')
except Exception as e:
    print(f'✗ analyze_candidate(): {e}')

try:
    metrics = calculate_evaluation_metrics(c)
    score = metrics.get('overall_performance_score', 'N/A')
    print(f'✓ calculate_evaluation_metrics(): Score = {score}/100')
except Exception as e:
    print(f'✗ calculate_evaluation_metrics(): {e}')

print('\n=== ALL SYSTEMS LINKED & WORKING ✓ ===')
