const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "");

/**
 * Verify candidate by ID against backend server
 * @param {string} candidateId - Candidate identifier (e.g. candidate-001 or CAND-001)
 * @returns {Promise<object>} Response with { verified: true, candidate: {...} }
 */
export async function verifyCandidate(candidateId) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidates/${encodeURIComponent(candidateId)}`,
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Candidate verification failed (${response.status}): ${errorText}`
    );
  }

  return response.json();
}

/**
 * Start a new interview session
 * @param {string} sessionId - Unique session identifier
 * @param {object} candidate - Candidate object from candidates.json
 * @returns {Promise<object>} Response with { reply, done, feedback? }
 */
export async function startInterview(sessionId, candidate) {
  const candidateId = typeof candidate === "object" ? candidate.id : candidate;
  const response = await fetch(
    `${API_BASE_URL}/api/interview`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        sessionId: sessionId,
        candidate_id: candidateId,
        candidate: candidate,
      }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Failed to start interview: ${response.status} - ${errorText}`
    );
  }

  return response.json();
}

/**
 * Send a message during an interview
 * @param {string} sessionId - Unique session identifier
 * @param {string} message - Candidate's message
 * @returns {Promise<object>} Response with { reply, done, feedback? }
 */
export async function sendInterviewMessage(sessionId, message) {
  const response = await fetch(
    `${API_BASE_URL}/api/interview`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        sessionId: sessionId,
        message: message,
      }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Failed to send message: ${response.status} - ${errorText}`
    );
  }

  return response.json();
}