import { useState } from "react";

function CandidateForm({ onStart, loading }) {
  const [form, setForm] = useState({
    name: "",
    email: "",
    role: "",
    experience: "",
    skills: "",
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
      name: form.name,
      email: form.email,
      role: form.role,
      experience: form.experience,
      skills: form.skills
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean),
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
            Enter your information to start the interview.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-grid">

          <div className="input-group">
            <label>Full Name</label>

            <input
              type="text"
              name="name"
              placeholder="Your Name"
              value={form.name}
              onChange={handleChange}
              required
            />
          </div>

          <div className="input-group">
            <label>Email</label>

            <input
              type="email"
              name="email"
              placeholder="your@email.com"
              value={form.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="input-group">
            <label>Role</label>

            <input
              type="text"
              name="role"
              placeholder="Frontend Developer"
              value={form.role}
              onChange={handleChange}
              required
            />
          </div>

          <div className="input-group">
            <label>Experience</label>

            <input
              type="text"
              name="experience"
              placeholder="2 years"
              value={form.experience}
              onChange={handleChange}
              required
            />
          </div>

        </div>

        <div className="input-group">
          <label>Skills</label>

          <input
            type="text"
            name="skills"
            placeholder="React, JavaScript, HTML, CSS"
            value={form.skills}
            onChange={handleChange}
            required
          />

          <small>
            Separate multiple skills using commas.
          </small>
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