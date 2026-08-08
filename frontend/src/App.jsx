

import { useState } from "react";

import Header from "./components/Header";
import CandidateForm from "./components/CandidateForm";
import ChatWindow from "./components/ChatWindow";
import FeedbackCard from "./components/FeedbackCard";

import {
  startInterview,
  sendInterviewMessage,
} from "./services/interviewApi";

import { generateSessionId } from "./utils/session";


function App() {
  const [started, setStarted] = useState(false);

  const [sessionId, setSessionId] = useState(null);

  const [messages, setMessages] = useState([]);

  const [loading, setLoading] = useState(false);

  const [done, setDone] = useState(false);

  const [feedback, setFeedback] = useState(null);

  const [error, setError] = useState("");


  // Start interview
  async function handleStart(candidate) {
    setLoading(true);
    setError("");

    const newSessionId = generateSessionId();

    try {
      const data = await startInterview(
        newSessionId,
        candidate
      );

      setSessionId(newSessionId);

      setStarted(true);

      setMessages([
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.reply,
        },
      ]);

      setDone(Boolean(data.done));

      if (data.feedback) {
        setFeedback(data.feedback);
      }

    } catch (error) {
      console.error(error);

      setError(
        "Unable to connect with the interview server."
      );

    } finally {
      setLoading(false);
    }
  }


  // Send candidate answer
  async function handleSend(message) {
    if (!sessionId || done) {
      return;
    }

    setError("");

    // Show user's message immediately
    setMessages((previous) => [
      ...previous,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
      },
    ]);

    setLoading(true);

    try {
      const data = await sendInterviewMessage(
        sessionId,
        message
      );

      // Show AI reply
      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.reply,
        },
      ]);

      // Interview finished
      if (data.done) {
        setDone(true);

        if (data.feedback) {
          setFeedback(data.feedback);
        }
      }

    } catch (error) {
      console.error(error);

      setError(
        "Something went wrong while sending your answer."
      );

    } finally {
      setLoading(false);
    }
  }


  // Restart interview
  function handleRestart() {
    setStarted(false);

    setSessionId(null);

    setMessages([]);

    setDone(false);

    setFeedback(null);

    setError("");
  }


  return (
    <div className="app">

      <Header />


      <main className="main">

        {!started ? (

          <>
            {/* Hero section */}

            <section className="hero">

              <div className="hero-badge">
                AI INTERVIEW AGENT
              </div>


              <h1>
                Practice interviews.
                <br />

                <span>
                  Get real feedback.
                </span>
              </h1>


              <p>
                Have a conversational interview
                with an AI interviewer and receive
                actionable feedback at the end.
              </p>

            </section>


            {/* Error */}

            {error && (
              <div className="error">
                {error}
              </div>
            )}


            {/* Candidate form */}

            <CandidateForm
              onStart={handleStart}
              loading={loading}
            />

          </>

        ) : (

          <section className="interview-layout">

            {/* Chat */}

            <ChatWindow
              messages={messages}
              onSend={handleSend}
              loading={loading}
              done={done}
            />


            {/* Final feedback */}

            {done && (
              <>
                <FeedbackCard
                  feedback={feedback}
                />

                <button
                  className="restart-button"
                  onClick={handleRestart}
                >
                  Start New Interview
                </button>
              </>
            )}


            {/* Error */}

            {error && (
              <div className="error">
                {error}
              </div>
            )}

          </section>

        )}

      </main>

    </div>
  );
}


export default App;