import { useState } from "react";

function CandidateForm({ onStart, loading }) {
  const [form, setForm] = useState({
    candidate_id: "candidate-001",
  });

  function handleChange(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  }

  function handleSubmit(e) {
    e.preventDefault();

    const candidate = {
      candidate_id: form.candidate_id,
    };

    onStart(candidate);
  }

  return (
    <div className="candidate-card">
      <div className="card-heading">
        <span className="step">01</span>

        <div>
          <h2>Candidate Details</h2>
          <p>
            Select a candidate profile to start the interview.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-grid">

          <div className="input-group">
            <label>Candidate ID</label>

            <input
              type="text"
              name="candidate_id"
              placeholder="candidate-001"
              value={form.candidate_id}
              onChange={handleChange}
              required
            />
          </div>

        </div>

        <button
          className="start-button"
          type="submit"
          disabled={loading}
        >
          {loading
            ? "Starting..."
            : "Start Interview →"}
        </button>

      </form>
    </div>
  );
}

export default CandidateForm;