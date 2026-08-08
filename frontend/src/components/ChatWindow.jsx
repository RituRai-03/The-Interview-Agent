import { useEffect, useRef, useState } from "react";

import ChatMessage from "./ChatMessage";
import TypingIndicator from "./TypingIndicator";

function ChatWindow({
  messages,
  onSend,
  loading,
  done,
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

  return (
    <div className="chat-container">

      <div className="chat-header">

        <div>
          <h2>Interview Session</h2>
          <p>
            Answer naturally and clearly.
          </p>
        </div>

        {!done && (
          <div className="live-badge">

            <span></span>

            LIVE

          </div>
        )}

      </div>


      <div className="messages">

        {messages.map((message) => (
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

          <input
            value={input}
            onChange={(e) =>
              setInput(e.target.value)
            }
            placeholder="Type your answer..."
            disabled={loading}
          />

          <button
            type="submit"
            disabled={
              loading || !input.trim()
            }
          >
            Send
          </button>

        </form>

      ) : (

        <div className="completed-bar">
          ✓ Interview completed
        </div>

      )}

    </div>
  );
}

export default ChatWindow;