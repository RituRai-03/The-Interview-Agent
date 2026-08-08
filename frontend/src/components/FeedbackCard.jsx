function FeedbackCard({ feedback }) {
  if (!feedback) {
    return null;
  }

  return (
    <div className="feedback-card">

      <div className="feedback-title">

        <div className="feedback-icon">
          ✓
        </div>

        <div>
          <h2>Interview Feedback</h2>

          <p>
            Here is your interview assessment.
          </p>
        </div>

      </div>


      <div className="summary">

        <h3>Summary</h3>

        <p>
          {feedback.summary}
        </p>

      </div>


      <div className="feedback-section">

        <h3>Strengths</h3>

        <ul>
          {feedback.strengths?.map(
            (item, index) => (
              <li key={index}>
                {item}
              </li>
            )
          )}
        </ul>

      </div>


      <div className="feedback-section">

        <h3>Gaps</h3>

        <ul>
          {feedback.gaps?.map(
            (item, index) => (
              <li key={index}>
                {item}
              </li>
            )
          )}
        </ul>

      </div>


      <div className="feedback-section">

        <h3>Next Steps</h3>

        <ul>
          {feedback.next?.map(
            (item, index) => (
              <li key={index}>
                {item}
              </li>
            )
          )}
        </ul>

      </div>

    </div>
  );
}

export default FeedbackCard;