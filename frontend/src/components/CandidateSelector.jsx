import { useState, useEffect } from "react";
import { loadCandidates } from "../utils/dataLoader";

function CandidateSelector({ onSelect, loading }) {
  const [candidates, setCandidates] = useState([]);
  const [loadingCandidates, setLoadingCandidates] =
    useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    async function fetch() {
      try {
        const data = await loadCandidates();
        setCandidates(data);
        if (data.length > 0) {
          setSelectedId(data[0].id);
        }
      } catch (err) {
        console.error("Failed to load candidates:", err);
        setError(
          "Failed to load candidates. Please refresh."
        );
      } finally {
        setLoadingCandidates(false);
      }
    }
    fetch();
  }, []);

  function handleSelect() {
    const candidate = candidates.find(
      c => c.id === selectedId
    );
    if (candidate) {
      onSelect(candidate);
    }
  }

  if (loadingCandidates) {
    return (
      <div className="candidate-card">
        <div className="card-heading">
          <span className="step">01</span>
          <div>
            <h2>Candidate Details</h2>
            <p>Loading candidates...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="candidate-card">
        <div className="card-heading">
          <span className="step">01</span>
          <div>
            <h2>Candidate Details</h2>
            <p className="error-text">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="candidate-card">
        <div className="card-heading">
          <span className="step">01</span>
          <div>
            <h2>Candidate Details</h2>
            <p>No candidates available.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="candidate-card">
      <div className="card-heading">
        <span className="step">01</span>
        <div>
          <h2>Candidate Details</h2>
          <p>
            Select a candidate profile to start the
            interview.
          </p>
        </div>
      </div>

      <div className="candidates-grid">
        {candidates.map(candidate => (
          <div
            key={candidate.id}
            className={`candidate-option ${
              selectedId === candidate.id
                ? "selected"
                : ""
            }`}
            onClick={() =>
              setSelectedId(candidate.id)
            }
          >
            <div className="candidate-avatar">
              {candidate.name
                .split(" ")
                .map(n => n[0])
                .join("")}
            </div>

            <div className="candidate-info">
              <h3>{candidate.name}</h3>
              <p className="role">
                {candidate.role}
              </p>
              <p className="meta">
                {candidate.experience} years
                experience
              </p>
            </div>

            {selectedId === candidate.id && (
              <div className="check-mark">✓</div>
            )}
          </div>
        ))}
      </div>

      <button
        className="start-button"
        onClick={handleSelect}
        disabled={loading || !selectedId}
      >
        {loading
          ? "Starting..."
          : "Start Interview →"}
      </button>
    </div>
  );
}

export default CandidateSelector;
