function ChatMessage({ message }) {
  return (
    <div className={`message-row ${message.role}`}>

      <div className="avatar">
        {message.role === "assistant"
          ? "AI"
          : "You"}
      </div>

      <div className="message-content">

        <span className="message-author">
          {message.role === "assistant"
            ? "Interview Agent"
            : "You"}
        </span>

        <div className="message-bubble">
          {message.content}
        </div>

      </div>

    </div>
  );
}

export default ChatMessage;