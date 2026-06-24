import { useEffect, useState } from 'react';
import type { ChatMessage } from '../types';
import logoTbd from '../assets/logo-tbd.png';

// Component CodeBlock hiển thị mã nguồn với nút Sao chép (Copy)
function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-container">
      <div className="code-block-header">
        <span className="code-block-lang">{language || 'code'}</span>
        <button className="btn-copy-code" onClick={handleCopy} type="button">
          {copied ? (
            <>
              <svg className="copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 13, height: 13, marginRight: 4 }}>
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              Đã sao chép
            </>
          ) : (
            <>
              <svg className="copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 13, height: 13, marginRight: 4 }}>
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              Sao chép
            </>
          )}
        </button>
      </div>
      <pre className="markdown-pre">
        <code className="markdown-code">{code}</code>
      </pre>
    </div>
  );
}

// Bộ phân tích văn bản: Hỗ trợ định dạng in đậm (**) và in nghiêng (*)
const renderFormattedText = (text: string) => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    const italicParts = part.split(/(\*[^*]+\*)/g);
    return italicParts.map((subPart, subIdx) => {
      if (subPart.startsWith('*') && subPart.endsWith('*')) {
        return <em key={`${idx}-${subIdx}`}>{subPart.slice(1, -1)}</em>;
      }
      return subPart;
    });
  });
};

// Định dạng văn bản cho các đoạn văn, tiêu đề, danh sách và code block
function formatMessageContent(content: string): React.ReactNode {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let currentListType: 'ul' | 'ol' | null = null;
  let currentList: React.ReactNode[] = [];
  
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let codeLanguage = '';

  const flushList = (key: number) => {
    if (currentList.length > 0) {
      if (currentListType === 'ul') {
        elements.push(<ul key={`ul-${key}`} className="markdown-list">{currentList}</ul>);
      } else {
        elements.push(<ol key={`ol-${key}`} className="markdown-list">{currentList}</ol>);
      }
      currentList = [];
      currentListType = null;
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Phát hiện Code Block ```
    if (trimmed.startsWith('```')) {
      if (inCodeBlock) {
        // Đóng block và render
        const codeText = codeLines.join('\n');
        elements.push(
          <CodeBlock key={`code-${idx}`} code={codeText} language={codeLanguage} />
        );
        codeLines = [];
        codeLanguage = '';
        inCodeBlock = false;
      } else {
        // Mở block mới
        flushList(idx);
        inCodeBlock = true;
        codeLanguage = trimmed.substring(3).trim();
      }
      return;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      return;
    }

    const isBullet = trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ');
    const isNumbered = /^\d+\.\s+/.test(trimmed);

    if (isBullet) {
      if (currentListType !== 'ul') {
        flushList(idx);
        currentListType = 'ul';
      }
      const cleanLine = trimmed.replace(/^[*\-•]\s+/, '');
      currentList.push(
        <li key={`li-${idx}`} className="markdown-list-item">
          {renderFormattedText(cleanLine)}
        </li>
      );
    } else if (isNumbered) {
      if (currentListType !== 'ol') {
        flushList(idx);
        currentListType = 'ol';
      }
      const cleanLine = trimmed.replace(/^\d+\.\s+/, '');
      currentList.push(
        <li key={`li-${idx}`} className="markdown-list-item">
          {renderFormattedText(cleanLine)}
        </li>
      );
    } else {
      flushList(idx);
      if (trimmed === '') {
        elements.push(<div key={`br-${idx}`} className="markdown-para-spacing" />);
      } else {
        if (trimmed.startsWith('### ')) {
          elements.push(
            <h4 key={`h3-${idx}`} className="markdown-h4">
              {renderFormattedText(trimmed.substring(4))}
            </h4>
          );
        } else if (trimmed.startsWith('## ')) {
          elements.push(
            <h3 key={`h2-${idx}`} className="markdown-h3">
              {renderFormattedText(trimmed.substring(3))}
            </h3>
          );
        } else if (trimmed.startsWith('# ')) {
          elements.push(
            <h2 key={`h1-${idx}`} className="markdown-h2">
              {renderFormattedText(trimmed.substring(2))}
            </h2>
          );
        } else {
          elements.push(
            <p key={`p-${idx}`} className="markdown-paragraph">
              {renderFormattedText(line)}
            </p>
          );
        }
      }
    }
  });

  // Xử lý khối code chưa đóng thẻ
  if (inCodeBlock && codeLines.length > 0) {
    const codeText = codeLines.join('\n');
    elements.push(
      <CodeBlock key={`code-unclosed`} code={codeText} language={codeLanguage} />
    );
  }

  flushList(lines.length);
  return elements;
}

interface MessageBubbleProps {
  message: ChatMessage;
  showDebug?: boolean;
}

export function MessageBubble({ message, showDebug = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isLoading = message.is_loading === true;
  
  const [loadingStage, setLoadingStage] = useState('Đang kết nối...');

  useEffect(() => {
    if (!isLoading) return;

    const stages = [
      { text: 'Đang kết nối...', delay: 0 },
      { text: 'Đang tìm kiếm tài liệu...', delay: 500 },
      { text: 'Đang tổng hợp câu trả lời...', delay: 1500 },
    ];

    const timeouts = stages.map((stage) =>
      setTimeout(() => {
        setLoadingStage(stage.text);
      }, stage.delay)
    );

    return () => {
      timeouts.forEach(clearTimeout);
    };
  }, [isLoading]);

  // Định dạng thời gian hiển thị theo kiểu Việt Nam
  const timeLabel = new Date(message.timestamp).toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
  });

  // Cảnh báo không có tài liệu trích dẫn phù hợp
  const shouldShowNoContextNotice =
    !isLoading &&
    !isUser &&
    message.has_context === false &&
    message.answer_type !== 'greeting' &&
    message.answer_type !== 'clarification' &&
    message.answer_type !== 'error';

  return (
    <div className={`message-bubble-wrapper ${message.role}`}>
      {/* Avatar tròn với Logo TBD */}
      <div className={`bubble-avatar ${message.role}`} style={!isUser ? { background: 'white' } : undefined}>
        {isUser ? (
          // Student SVG icon
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="avatar-svg">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <img src={logoTbd} alt="TBD Logo" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'contain', background: 'white' }} />
        )}
      </div>

      <div className="message-bubble-body">
        {/* Nhãn vai trò */}
        <div className="bubble-role-label">
          {isUser ? 'Bạn' : 'TBD Chatbot'}
        </div>

        {/* Nội dung chính hoặc đang tải */}
        {isLoading ? (
          <div className="loading-bubble-content">
            <span className="loading-stage-text">{loadingStage}</span>
            <div className="loading-indicator">
              <div className="loading-indicator-dot" />
              <div className="loading-indicator-dot" />
              <div className="loading-indicator-dot" />
            </div>
          </div>
        ) : (
          <div className="bubble-content">
            {formatMessageContent(message.content)}
          </div>
        )}

        {/* Cảnh báo không có nguồn */}
        {shouldShowNoContextNotice && (
          <div className="bubble-no-context">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 14, height: 14, flexShrink: 0 }} className="no-context-icon">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>Thông tin này chưa có trong cơ sở dữ liệu hiện tại. Chatbot chỉ trả lời từ dữ liệu chính thức đã được nạp.</span>
          </div>
        )}

        {/* Debug performance info */}
        {showDebug && !isLoading && !isUser && message.performance && (
          <div className="bubble-perf-details">
            <div className="bubble-perf-title">Đo lường hiệu năng (Debug)</div>
            <div className="perf-header-line">
              <strong>API:</strong> http://localhost:8001/api/chat | <strong>Loại:</strong> {message.answer_type}
            </div>
            <div className="perf-grid">
              <div className="perf-cell"><strong>Ý định:</strong> {message.performance.intent}</div>
              <div className="perf-cell"><strong>Khớp FAQ:</strong> {message.performance.faq_matched ? 'Có' : 'Không'}</div>
              <div className="perf-cell"><strong>Khớp Cache:</strong> {message.performance.cache_hit ? 'Có' : 'Không'}</div>
              <div className="perf-cell"><strong>Gọi Gemini:</strong> {message.performance.gemini_called ? 'Có' : 'Không'}</div>
              <div className="perf-cell"><strong>Tổng thời gian:</strong> {message.performance.total_ms}ms</div>
            </div>
            {message.performance.gemini_called && (
              <div className="perf-details-gemini">
                <div className="gemini-metric"><span>• Nhúng (Embedding):</span> <strong>{message.performance.embedding_ms}ms</strong></div>
                <div className="gemini-metric"><span>• Tìm kiếm Vector:</span> <strong>{message.performance.vector_search_ms}ms</strong></div>
                <div className="gemini-metric"><span>• Sinh câu trả lời:</span> <strong>{message.performance.generation_ms}ms</strong></div>
              </div>
            )}
          </div>
        )}

        {/* Metadata thời gian */}
        {!isLoading && (
          <div className="bubble-meta">{timeLabel}</div>
        )}
      </div>
    </div>
  );
}
