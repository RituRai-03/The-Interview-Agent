import {
  loadCurriculum,
  buildCurriculumProgress,
} from "../utils/dataLoader";
import { useState, useEffect } from "react";

function LearningJourney({ candidate }) {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
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
        console.error("Failed to load curriculum:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [candidate]);

  if (loading) {
    return (
      <div className="learning-journey">
        <h2>31-Day Learning Journey</h2>
        <p>Loading curriculum...</p>
      </div>
    );
  }

  if (!progress || !progress.curriculum) {
    return null;
  }

  const { dayProgress, moduleProgress, curriculum } =
    progress;

  return (
    <div className="learning-journey">
      <h2>31-Day Learning Journey</h2>

      <div className="modules-container">
        {curriculum.modules.map(module => {
          const mod = moduleProgress[module.module_id];
          const { start, end } = module.days;

          const days = [];
          for (let d = start; d <= end; d++) {
            days.push(d);
          }

          return (
            <div
              key={module.module_id}
              className="module-block"
            >
              <div className="module-header">
                <h3>{module.module_name}</h3>
                <div className="module-stats">
                  <span className="stat passed">
                    {mod.passed}
                  </span>
                  <span className="stat failed">
                    {mod.failed}
                  </span>
                  <span className="stat skipped">
                    {mod.skipped}
                  </span>
                </div>
              </div>

              <div className="module-progress-bar">
                <div className="progress-fill">
                  <div
                    className="segment passed"
                    style={{
                      width: `${(mod.passed / mod.total) * 100}%`,
                    }}
                    title={`${mod.passed} passed`}
                  ></div>
                  <div
                    className="segment failed"
                    style={{
                      width: `${(mod.failed / mod.total) * 100}%`,
                    }}
                    title={`${mod.failed} failed`}
                  ></div>
                  <div
                    className="segment skipped"
                    style={{
                      width: `${(mod.skipped / mod.total) * 100}%`,
                    }}
                    title={`${mod.skipped} skipped`}
                  ></div>
                  <div
                    className="segment not-started"
                    style={{
                      width: `${(mod.notStarted / mod.total) * 100}%`,
                    }}
                    title={`${mod.notStarted} not started`}
                  ></div>
                </div>
              </div>

              <div className="days-grid">
                {days.map(day => {
                  const status = dayProgress[day];
                  const statusSymbol = {
                    passed: "✓",
                    failed: "✕",
                    skipped: "−",
                    "not-started": "○",
                  }[status];

                  return (
                    <div
                      key={day}
                      className={`day-badge ${status}`}
                      title={`Day ${day}: ${status}`}
                    >
                      <span className="day-number">
                        {day}
                      </span>
                      <span className="status-icon">
                        {statusSymbol}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="module-topics">
                <p className="topics-label">
                  Topics:
                </p>
                <div className="topics-list">
                  {module.topics.map(
                    (topic, idx) => (
                      <span key={idx}>
                        {topic}
                      </span>
                    )
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="legend">
        <div className="legend-item">
          <span className="legend-box passed">
            ✓
          </span>
          Passed
        </div>
        <div className="legend-item">
          <span className="legend-box failed">
            ✕
          </span>
          Failed
        </div>
        <div className="legend-item">
          <span className="legend-box skipped">
            −
          </span>
          Skipped
        </div>
        <div className="legend-item">
          <span className="legend-box not-started">
            ○
          </span>
          Not Started
        </div>
      </div>
    </div>
  );
}

export default LearningJourney;
