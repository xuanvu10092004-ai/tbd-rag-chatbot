interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
  disabled?: boolean;
}

// Danh sach cau hoi goi y theo yeu cau du an
const SUGGESTED_QUESTIONS = [
  'Học phí ngành Công nghệ thông tin là bao nhiêu?',
  'Trường có những ngành nào?',
  'Học phí có tăng qua các năm không?',
  'Trường có học bổng không?',
  'Thông tin liên hệ tuyển sinh là gì?',
  'Phương thức xét tuyển của trường là gì?',
];

export function SuggestedQuestions({ onSelect, disabled = false }: SuggestedQuestionsProps) {
  return (
    <div className="card suggested-questions">
      <div className="card-header">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15, marginRight: 8, color: 'var(--color-primary)' }}>
          <circle cx="12" cy="12" r="10" />
          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
        </svg>
        Câu hỏi gợi ý
      </div>
      <div className="suggestions-grid">
        {SUGGESTED_QUESTIONS.map((question) => (
          <button
            key={question}
            className="suggestion-btn"
            onClick={() => onSelect(question)}
            disabled={disabled}
            type="button"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="suggestion-icon" style={{ width: 14, height: 14, flexShrink: 0 }}>
              <circle cx="12" cy="12" r="10" />
              <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
            </svg>
            <span className="suggestion-text">{question}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
