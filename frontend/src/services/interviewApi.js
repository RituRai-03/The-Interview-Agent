const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? "http://localhost:8000" : "");

/**
 * Start a new interview session
 * @param {string} sessionId - Unique session identifier
 * @param {object} candidate - Candidate object from candidates.json
 * @returns {Promise<object>} Response with { reply, done, feedback? }
 */
export async function startInterview(sessionId, candidate) {
  const response = await fetch(
    `${API_BASE_URL}/api/interview`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        sessionId: sessionId,
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