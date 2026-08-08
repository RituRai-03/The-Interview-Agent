const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:3000";


// Start a new interview
export async function startInterview(
  sessionId,
  candidate
) {
  const response = await fetch(
    `${API_URL}/api/interview`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        sessionId,
        candidate,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to start interview"
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
    `${API_URL}/api/interview`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        sessionId,
        message,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to send message"
    );
  }

  return response.json();
}