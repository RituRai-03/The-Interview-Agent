function Header() {
  return (
    <header className="header">

      <div className="logo">

        <div className="logo-icon">
          AI
        </div>

        <div>
          <h1>InterviewAI</h1>
          <span>AI-Powered Interview</span>
        </div>

      </div>

      <div className="status">
        <span className="status-dot"></span>
        Interview Agent Online
      </div>

    </header>
  );
}

export default Header;