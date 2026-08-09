import { useState, useEffect } from "react";
import { loadCandidates } from "../utils/dataLoader";
import { verifyCandidate } from "../services/interviewApi";

function CandidateSelector({ onSelect, loading }) {
  const [candidates, setCandidates] = useState([]);
  const [candidateIdInput, setCandidateIdInput] = useState("candidate-001");
  const [verifiedCandidate, setVerifiedCandidate] = useState(null);
  const [isVerified, setIsVerified] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [loadingCandidates, setLoadingCandidates] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchAndAutoVerify() {
      try {
        const data = await loadCandidates();
        setCandidates(data);
        if (data.length > 0) {
          const defaultCand = data[0];
          setCandidateIdInput(defaultCand.id);
          setVerifiedCandidate(defaultCand);
          setIsVerified(true);
        }
      } catch (err) {
        console.error("Failed to load candidates:", err);
        setError("Failed to load candidates. Please refresh.");
      } finally {
        setLoadingCandidates(false);
      }
    }
    fetchAndAutoVerify();
  }, []);

  async function handleVerify(targetId) {
    const idToVerify = targetId || candidateIdInput;
    if (!idToVerify.trim()) {
      setError("Please enter a valid Candidate ID.");
      return;
    }

    setVerifying(true);
    setError("");
    try {
      // Server-side verification API call
      const result = await verifyCandidate(idToVerify);
      if (result && result.verified && result.candidate) {
        setVerifiedCandidate(result.candidate);
        setCandidateIdInput(result.candidate.id);
        setIsVerified(true);
      } else {
        throw new Error("Candidate record not found");
      }
    } catch (err) {
      console.warn("Server verification warning, falling back to local dataset:", err.message);
      // Fallback verification against loaded dataset
      const found = candidates.find(
        (c) =>
          c.id.toLowerCase() === idToVerify.trim().toLowerCase() ||
          c.id.toLowerCase().includes(idToVerify.trim().toLowerCase())
      );
      if (found) {
        setVerifiedCandidate(found);
        setCandidateIdInput(found.id);
        setIsVerified(true);
      } else {
        setVerifiedCandidate(null);
        setIsVerified(false);
        setError(`Invalid Candidate ID "${idToVerify}". Please enter a valid ID (e.g., candidate-001 or CAND-001).`);
      }
    } finally {
      setVerifying(false);
    }
  }

  function handleSelect() {
    if (isVerified && verifiedCandidate) {
      onSelect(verifiedCandidate);
    }
  }

  if (loadingCandidates) {
    return (
      <div className="candidate-card">
        <div className="card-heading">
          <span className="step">01</span>
          <div>
            <h2>Candidate Verification</h2>
            <p>Loading candidate records...</p>
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
          <h2>Candidate Verification & Selection</h2>
          <p>Verify authoritative candidate record before launching technical interview.</p>
        </div>
      </div>

      {/* Candidate ID Form Input */}
      <div style={{ marginBottom: "1.5rem", background: "rgba(255,255,255,0.03)", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)" }}>
        <label style={{ display: "block", fontSize: "0.85rem", color: "#94a3b8", marginBottom: "0.5rem" }}>
          Candidate ID:
        </label>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <input
            type="text"
            value={candidateIdInput}
            onChange={(e) => {
              setCandidateIdInput(e.target.value);
              setIsVerified(false);
            }}
            placeholder="e.g. candidate-001 or CAND-001"
            style={{
              flex: 1,
              padding: "0.6rem 0.9rem",
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: "6px",
              color: "#f8fafc",
              fontSize: "0.95rem",
            }}
          />
          <button
            type="button"
            onClick={() => handleVerify()}
            disabled={verifying}
            style={{
              padding: "0.6rem 1.2rem",
              background: "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            {verifying ? "Verifying..." : "Verify Candidate"}
          </button>
        </div>
        {error && <p style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: "0.5rem" }}>{error}</p>}
      </div>

      {/* Verification Status Banner */}
      {isVerified && verifiedCandidate && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.4)", borderRadius: "8px" }}>
          <div style={{ color: "#10b981", fontWeight: 700, fontSize: "1.05rem", marginBottom: "0.4rem" }}>
            ✓ Candidate Verified
          </div>
          <div style={{ color: "#f8fafc", fontWeight: 600, fontSize: "1.1rem" }}>
            {verifiedCandidate.name}
          </div>
          <div style={{ color: "#cbd5e1", fontSize: "0.9rem" }}>
            {verifiedCandidate.role} • {verifiedCandidate.experience} Years Experience
          </div>
          <div style={{ color: "#94a3b8", fontSize: "0.85rem", marginTop: "0.2rem" }}>
            Education: {verifiedCandidate.education || "MS Computer Science"}
          </div>
        </div>
      )}

      {/* Quick Select Grid */}
      <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "0.5rem" }}>Or select candidate profile:</p>
      <div className="candidates-grid">
        {candidates.map((candidate) => {
          const isSelected = verifiedCandidate && verifiedCandidate.id === candidate.id;
          return (
            <div
              key={candidate.id}
              className={`candidate-option ${isSelected ? "selected" : ""}`}
              onClick={() => handleVerify(candidate.id)}
            >
              <div className="candidate-avatar">
                {candidate.name
                  .split(" ")
                  .map((n) => n[0])
                  .join("")}
              </div>

              <div className="candidate-info">
                <h3>{candidate.name}</h3>
                <p className="role">{candidate.role}</p>
                <p className="meta">{candidate.experience} yrs exp • ID: {candidate.id}</p>
              </div>

              {isSelected && isVerified && <div className="check-mark">✓</div>}
            </div>
          );
        })}
      </div>

      {/* Start Interview Button */}
      <div style={{ marginTop: "1.5rem" }}>
        {!isVerified && (
          <p style={{ color: "#f59e0b", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            ⚠️ Please verify a candidate ID before starting the interview.
          </p>
        )}
        <button
          className="start-button"
          onClick={handleSelect}
          disabled={loading || !isVerified || !verifiedCandidate}
        >
          {loading ? "Starting..." : "Start Interview →"}
        </button>
      </div>
    </div>
  );
}

export default CandidateSelector;
