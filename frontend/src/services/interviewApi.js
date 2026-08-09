const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";


// Start a new interview
export async function startInterview(
  candidateInput,
  interviewType = "technical"
) {
  const candidateId =
    typeof candidateInput === "string"
      ? candidateInput
      : candidateInput?.candidate_id ||
        candidateInput?.id ||
        "candidate-001";

  const response = await fetch(
    `${API_URL}/api/interview`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        candidate_id: candidateId,
        interview_type: interviewType,
        conversation: [],
      }),
    }
  );

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `Failed to start interview: ${detail}`
    );
  }

  return response.json();
}


// Send candidate's answer
export async function sendInterviewMessage(
  sessionId,
  message
) {
  const response = await fetch(
    `${API_URL}/api/interview/${sessionId}/answer`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        answer: message,
        transcript_turn: "candidate_answer",
      }),
    }
  );

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `Failed to send message: ${detail}`
    );
  }

  return response.json();
}