/**
 * Load candidates from candidates.json
 * @returns {Promise<array>} Array of candidate objects
 */
export async function loadCandidates() {
  try {
    const response = await fetch('/candidates.json');
    if (!response.ok) {
      throw new Error(`Failed to load candidates: ${response.status}`);
    }
    const data = await response.json();
    
    // Handle both wrapped and direct formats
    const candidates = data.candidates || data;
    return Array.isArray(candidates) ? candidates : [];
  } catch (error) {
    console.error('Error loading candidates:', error);
    return [];
  }
}

/**
 * Load curriculum from curriculum.json
 * @returns {Promise<object>} Curriculum object with modules and days
 */
export async function loadCurriculum() {
  try {
    const response = await fetch('/curriculum.json');
    if (!response.ok) {
      throw new Error(`Failed to load curriculum: ${response.status}`);
    }
    const data = await response.json();
    
    // Handle both wrapped and direct formats
    return data.curriculum || data;
  } catch (error) {
    console.error('Error loading curriculum:', error);
    return null;
  }
}

/**
 * Get a specific candidate by ID
 * @param {string} candidateId - Candidate ID
 * @param {array} candidates - Array of candidates
 * @returns {object|null} Candidate object or null
 */
export function getCandidateById(candidateId, candidates) {
  return candidates.find(c => c.id === candidateId) || null;
}

/**
 * Calculate candidate progress stats
 * @param {object} candidate - Candidate object
 * @returns {object} Progress stats including pass rate, completion, etc.
 */
export function calculateCandidateStats(candidate) {
  const missions = candidate.missions || [];
  
  const passed = missions.filter(m => m.passed && !m.skipped).length;
  const failed = missions.filter(m => !m.passed && !m.skipped).length;
  const skipped = missions.filter(m => m.skipped).length;
  
  const total = missions.length;
  const completionPercent = total > 0 ? Math.round((passed / total) * 100) : 0;
  const passRate = total > 0 ? Math.round(((passed) / (passed + failed)) * 100) : 0;
  
  return {
    total,
    passed,
    failed,
    skipped,
    completionPercent,
    passRate,
    firstTryCount: missions.filter(m => m.passed && m.attempts === 1).length,
    totalCommitDays: missions.reduce((sum, m) => sum + (m.commit_days || 0), 0),
  };
}

/**
 * Map missions to curriculum modules
 * @param {object} candidate - Candidate object
 * @param {object} curriculum - Curriculum object
 * @returns {object} Progress by day and module
 */
export function buildCurriculumProgress(candidate, curriculum) {
  if (!curriculum || !curriculum.modules) {
    return null;
  }

  const missions = candidate.missions || [];
  const missionsByDay = {};
  
  missions.forEach(mission => {
    missionsByDay[mission.day] = mission;
  });

  // Build day-by-day progress
  const dayProgress = {};
  for (let day = 1; day <= 31; day++) {
    const mission = missionsByDay[day];
    if (mission) {
      if (mission.skipped) {
        dayProgress[day] = 'skipped';
      } else if (mission.passed) {
        dayProgress[day] = 'passed';
      } else {
        dayProgress[day] = 'failed';
      }
    } else {
      dayProgress[day] = 'not-started';
    }
  }

  // Build module progress
  const moduleProgress = {};
  curriculum.modules.forEach(module => {
    const { start, end } = module.days;
    const daysInModule = [];
    const statuses = [];
    
    for (let day = start; day <= end; day++) {
      daysInModule.push(day);
      statuses.push(dayProgress[day]);
    }

    const passed = statuses.filter(s => s === 'passed').length;
    const failed = statuses.filter(s => s === 'failed').length;
    const skipped = statuses.filter(s => s === 'skipped').length;
    const notStarted = statuses.filter(s => s === 'not-started').length;

    moduleProgress[module.module_id] = {
      name: module.module_name,
      passed,
      failed,
      skipped,
      notStarted,
      total: daysInModule.length,
      completionPercent: daysInModule.length > 0 
        ? Math.round(((passed + failed + skipped) / daysInModule.length) * 100) 
        : 0,
    };
  });

  return {
    dayProgress,
    moduleProgress,
    curriculum,
  };
}
