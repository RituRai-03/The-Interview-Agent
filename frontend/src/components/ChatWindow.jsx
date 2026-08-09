import { useEffect, useRef, useState } from "react";

import ChatMessage from "./ChatMessage";
import TypingIndicator from "./TypingIndicator";

function ChatWindow({
  messages,
  onSend,
  loading,
  done,
  candidate,
}) {
  const [input, setInput] = useState("");

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  function handleSubmit(e) {
    e.preventDefault();

    const text = input.trim();

    if (!text || loading || done) {
      return;
    }

    onSend(text);

    setInput("");
  }

  function handleKeyDown(e) {
    // Enter to send (Shift+Enter for newline)
    if (
      e.key === "Enter" &&
      !e.shiftKey &&
      !loading &&
      !done
    ) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <div className="chat-container">

      <div className="chat-header">

        <div className="chat-header-info">
          {candidate && (
            <div className="chat-candidate">
              <h3>{candidate.name}</h3>
              <p>{candidate.role}</p>
            </div>
          )}
          <div className="chat-status">
            <h2>Interview Session</h2>
            <p>
              {done
                ? "✓ Interview Complete"
                : "● In Progress"}
            </p>
          </div>
        </div>

        {!done && (
          <div className="live-badge">
            <span></span>
            LIVE
          </div>
        )}

      </div>


      <div className="messages">

        {messages.map(message => (
          <ChatMessage
            key={message.id}
            message={message}
          />
        ))}

        {loading && <TypingIndicator />}

        <div ref={bottomRef}></div>

      </div>


      {!done ? (

        <form
          className="chat-input"
          onSubmit={handleSubmit}
        >

          <textarea
            value={input}
            onChange={e =>
              setInput(e.target.value)
            }
            onKeyDown={handleKeyDown}
            placeholder="Type your answer... (Shift+Enter for newline)"
            disabled={loading}
            rows="3"
          />

          <button
            type="submit"
            disabled={
              loading || !input.trim()
            }
            className="send-button"
          >
            Send
          </button>

        </form>

      ) : (
        <div className="chat-complete">
          <p>
            Interview complete. Review your
            feedback below.
          </p>
        </div>
      )}

    </div>
  );
}

export default ChatWindow;