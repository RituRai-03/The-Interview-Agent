

import { useState } from "react";

import Header from "./components/Header";
import CandidateSelector from "./components/CandidateSelector";
import CandidateOverview from "./components/CandidateOverview";
import LearningJourney from "./components/LearningJourney";
import ChatWindow from "./components/ChatWindow";
import FeedbackCard from "./components/FeedbackCard";

import {
  startInterview,
  sendInterviewMessage,
} from "./services/interviewApi";


function App() {
  // UI state
  const [selectedCandidate, setSelectedCandidate] =
    useState(null);
  const [interviewStarted, setInterviewStarted] =
    useState(false);
  const [interviewCompleted, setInterviewCompleted] =
    useState(false);

  // Interview state
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [error, setError] = useState("");


  // Handle candidate selection
  function handleCandidateSelect(candidate) {
    setSelectedCandidate(candidate);
  }


  // Start interview
  async function handleStartInterview() {
    if (!selectedCandidate) {
      setError("Please select a candidate first.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Generate a unique sessionId
      const newSessionId = crypto.randomUUID();
      setSessionId(newSessionId);

      // Store sessionId in sessionStorage
      sessionStorage.setItem(
        `interview_${newSessionId}`,
        newSessionId
      );

      // Start interview with sessionId and candidate
      const response = await startInterview(
        newSessionId,
        selectedCandidate
      );

      setInterviewStarted(true);

      // Show opening message
      setMessages([
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.reply,
        },
      ]);

      setDone(Boolean(response.done));

      if (response.feedback) {
        setFeedback(response.feedback);
      }

    } catch (err) {
      console.error(err);
      setError(
        "Unable to connect with the interview server. Make sure the backend is running at http://localhost:8000"
      );
    } finally {
      setLoading(false);
    }
  }


  // Send candidate message
  async function handleSend(message) {
    if (!sessionId || done) {
      return;
    }

    setError("");

    // Show user message immediately
    setMessages(previous => [
      ...previous,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
      },
    ]);

    setLoading(true);

    try {
      const response = await sendInterviewMessage(
        sessionId,
        message
      );

      // Show AI reply
      setMessages(previous => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.reply,
        },
      ]);

      // Check if interview is complete
      if (response.done) {
        setDone(true);
        setInterviewCompleted(true);

        if (response.feedback) {
          setFeedback(response.feedback);
        }
      }

    } catch (err) {
      console.error(err);
      setError(
        "Something went wrong while sending your answer."
      );
    } finally {
      setLoading(false);
    }
  }


  // Restart interview
  function handleRestart() {
    // Clear interview state
    setInterviewStarted(false);
    setInterviewCompleted(false);
    setSessionId(null);
    setMessages([]);
    setDone(false);
    setFeedback(null);
    setError("");

    // Clear sessionStorage
    if (sessionId) {
      sessionStorage.removeItem(
        `interview_${sessionId}`
      );
    }
  }

  // Go back to candidate selection
  function handleBackToCandidates() {
    handleRestart();
    setSelectedCandidate(null);
  }


  return (
    <div className="app">

      <Header />

      <main className="main">

        {!selectedCandidate ? (
          <>
            {/* Hero section */}
            <section className="hero">

              <div className="hero-badge">
                AI INTERVIEW AGENT
              </div>

              <h1>
                Practice interviews.
                <br />
                <span>Get real feedback.</span>
              </h1>

              <p>
                Have a conversational interview with an
                AI interviewer and receive actionable
                feedback at the end.
              </p>

            </section>

            {/* Error */}
            {error && (
              <div className="error">
                <strong>Error:</strong> {error}
              </div>
            )}

            {/* Candidate selector */}
            <CandidateSelector
              onSelect={
                handleCandidateSelect
              }
              loading={loading}
            />

          </>
        ) : !interviewStarted ? (
          <>
            {/* Candidate overview before interview */}
            <div className="candidate-prep">

              <div className="prep-header">
                <button
                  className="back-button"
                  onClick={
                    handleBackToCandidates
                  }
                >
                  ← Back
                </button>
              </div>

              {error && (
                <div className="error">
                  <strong>Error:</strong> {error}
                </div>
              )}

              {/* Candidate info */}
              <CandidateOverview
                candidate={selectedCandidate}
              />

              {/* Learning journey */}
              <LearningJourney
                candidate={selectedCandidate}
              />

              {/* Start interview button */}
              <div className="prep-actions">
                <button
                  className="start-button"
                  onClick={
                    handleStartInterview
                  }
                  disabled={loading}
                >
                  {loading
                    ? "Starting Interview..."
                    : "Start Interview →"}
                </button>
              </div>

            </div>

          </>
        ) : (
          <section className="interview-layout">

            {/* Chat interface */}
            <ChatWindow
              messages={messages}
              onSend={handleSend}
              loading={loading}
              done={done}
              candidate={selectedCandidate}
            />

            {/* Final feedback */}
            {done && (
              <>
                <FeedbackCard
                  feedback={feedback}
                />

                <div className="feedback-actions">
                  <button
                    className="restart-button"
                    onClick={handleRestart}
                  >
                    Start New Interview
                  </button>

                  <button
                    className="back-button-secondary"
                    onClick={
                      handleBackToCandidates
                    }
                  >
                    Back to Candidates
                  </button>
                </div>
              </>
            )}

            {/* Error */}
            {error && (
              <div className="error">
                <strong>Error:</strong> {error}
              </div>
            )}

          </section>
        )}

      </main>

    </div>
  );
}

export default App;