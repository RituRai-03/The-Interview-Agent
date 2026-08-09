import {
  calculateCandidateStats,
  loadCurriculum,
  buildCurriculumProgress,
} from "../utils/dataLoader";
import { useState, useEffect } from "react";

function CandidateOverview({ candidate }) {
  const [stats, setStats] = useState(null);
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    async function load() {
      const candidateStats =
        calculateCandidateStats(candidate);
      setStats(candidateStats);

      try {
        const curriculum =
          await loadCurriculum();
        const progressData =
          buildCurriculumProgress(
            candidate,
            curriculum
          );
        setProgress(progressData);
      } catch (err) {
        console.error(
          "Failed to load curriculum:",
          err
        );
      }
    }
    load();
  }, [candidate]);

  if (!stats) {
    return null;
  }

  return (
    <div className="candidate-overview">
      <h2>Candidate Profile</h2>

      <div className="overview-grid">
        {/* Profile Section */}
        <div className="overview-section profile-section">
          <h3>Profile</h3>

          <div className="profile-item">
            <span className="label">Name</span>
            <span className="value">
              {candidate.name}
            </span>
          </div>

          <div className="profile-item">
            <span className="label">Role</span>
            <span className="value">
              {candidate.role}
            </span>
          </div>

          <div className="profile-item">
            <span className="label">Experience</span>
            <span className="value">
              {candidate.experience} years
            </span>
          </div>

          <div className="profile-item">
            <span className="label">Education</span>
            <span className="value">
              {candidate.education}
            </span>
          </div>

          <div className="profile-item">
            <span className="label">Status</span>
            <span className="value status-badge">
              {candidate.metrics
                .assessment_status}
            </span>
          </div>
        </div>

        {/* Progress Section */}
        <div className="overview-section progress-section">
          <h3>Progress</h3>

          <div className="stat-item">
            <span className="label">
              Overall Progress
            </span>
            <div className="stat-value">
              <span className="number">
                {stats.completionPercent}%
              </span>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${stats.completionPercent}%`,
                  }}
                ></div>
              </div>
            </div>
          </div>

          <div className="stat-item">
            <span className="label">
              Missions Completed
            </span>
            <span className="number">
              {stats.passed}/{stats.total}
            </span>
          </div>

          <div className="stat-item">
            <span className="label">Pass Rate</span>
            <span className="number">
              {stats.passRate}%
            </span>
          </div>

          <div className="stat-item">
            <span className="label">
              First-Try Missions
            </span>
            <span className="number">
              {stats.firstTryCount}
            </span>
          </div>

          <div className="stat-item">
            <span className="label">
              Total Commit Days
            </span>
            <span className="number">
              {stats.totalCommitDays}
            </span>
          </div>
        </div>
      </div>

      {/* Skills Section */}
      {candidate.skills && (
        <div className="overview-section skills-section">
          <h3>Skills</h3>
          <div className="skills-list">
            {candidate.skills.map((skill, idx) => (
              <span key={idx} className="skill-tag">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Growth Areas Section */}
      {candidate.growth_areas && (
        <div className="overview-section growth-section">
          <h3>Growth Areas</h3>
          <div className="growth-list">
            {candidate.growth_areas.map(
              (area, idx) => (
                <div key={idx} className="growth-item">
                  • {area}
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default CandidateOverview;
