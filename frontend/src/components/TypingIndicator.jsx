function TypingIndicator() {
  return (
    <div className="message-row assistant">

      <div className="avatar">
        AI
      </div>

      <div className="message-content">

        <span className="message-author">
          Interview Agent
        </span>

        <div className="message-bubble typing">

          <span></span>
          <span></span>
          <span></span>

        </div>

      </div>

    </div>
  );
}

export default TypingIndicator;