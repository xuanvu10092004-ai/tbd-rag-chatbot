// Panel chat chính: danh sách tin nhắn, ô nhập, nút gửi
// Quản lý conversation_id để duy trì lịch sử hội thoại

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from 'react';
import { sendMessage } from '../services/api';
import type { ChatMessage, Source } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatPanelProps {
  onSourcesUpdate: (sources: Source[]) => void;
  pendingQuestion?: string | null;
  onPendingQuestionHandled?: () => void;
  showDebug?: boolean;
  onShowDebugChange?: (show: boolean) => void;
}

export function ChatPanel({
  onSourcesUpdate,
  pendingQuestion,
  onPendingQuestionHandled,
  showDebug = false,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Xử lý câu hỏi đang chờ từ SuggestedQuestions (truyền qua App.tsx)
  useEffect(() => {
    if (pendingQuestion) {
      handleSend(pendingQuestion);
      onPendingQuestionHandled?.();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingQuestion]);

  const prevLengthRef = useRef(0);
  // Tự động cuộn xuống cuối khi có tin nhắn mới
  useEffect(() => {
    if (messages.length > prevLengthRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    prevLengthRef.current = messages.length;
  }, [messages]);

  // Xử lý gửi câu hỏi
  const handleSend = useCallback(
    async (questionText?: string) => {
      const question = (questionText ?? input).trim();
      if (!question || isLoading) return;

      setInput('');
      setError(null);

      // Tạo tin nhắn của người dùng
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: question,
        timestamp: new Date().toISOString(),
      };

      // Tạo tin nhắn loading của trợ lý
      const loadingId = `loading-${Date.now()}`;
      const loadingMessage: ChatMessage = {
        id: loadingId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        is_loading: true,
      };

      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setIsLoading(true);

      try {
        // Gửi câu hỏi kèm conversation_id (nếu đã có)
        const response = await sendMessage(question, conversationId);

        // Cập nhật conversation_id từ response
        if (response.conversation_id) {
          setConversationId(response.conversation_id);
        }

        // Cập nhật panel nguồn trích dẫn
        onSourcesUpdate(response.sources);

        // Thay thế loading bubble bằng câu trả lời thực sự
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          has_context: response.has_context,
          timestamp: new Date().toISOString(),
          answer_type: response.answer_type,
          performance: response.performance,
        };

        setMessages((prev) =>
          prev.map((m) => (m.id === loadingId ? assistantMessage : m)),
        );
      } catch (err) {
        let errorMsg = 'Hệ thống phản hồi quá lâu. Vui lòng thử lại hoặc kiểm tra backend.';
        if (err instanceof Error) {
          if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError') || err.message.includes('fetch')) {
            errorMsg = 'Không thể kết nối backend. Vui lòng kiểm tra server FastAPI tại cổng 8001.';
          } else {
            errorMsg = err.message;
          }
        }

        setError(errorMsg);

        // Hiển thị lỗi trong bubble thay vì loading
        const errorMessage: ChatMessage = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: `Lỗi hệ thống: ${errorMsg}`,
          has_context: false,
          timestamp: new Date().toISOString(),
          answer_type: 'error',
        };

        setMessages((prev) =>
          prev.map((m) => (m.id === loadingId ? errorMessage : m)),
        );
      } finally {
        setIsLoading(false);
        setTimeout(() => {
          inputRef.current?.focus();
        }, 50);
      }
    },
    [input, isLoading, conversationId, onSourcesUpdate],
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Bắt đầu cuộc hội thoại mới
  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(undefined);
    setError(null);
    onSourcesUpdate([]);
    inputRef.current?.focus();
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="chat-panel">
      {/* Danh sách tin nhắn */}
      <div className="chat-messages">
        {isEmpty ? (
          <div className="chat-empty-container">
            <div className="chat-empty-state">
              <span className="tbd-badge">TBD CHATBOT</span>
              <h2>Hỗ Trợ Tuyển Sinh</h2>
              <p>
                Chào bạn! Tôi là chatbot chính thức hỗ trợ tuyển sinh của Trường Đại học Thái Bình Dương.
                Bạn có thể hỏi tôi về các ngành học, học phí, chính sách học bổng, phương thức xét tuyển hoặc thông tin liên hệ tuyển sinh của trường.
              </p>
              <p className="input-hint">
                Chọn câu hỏi gợi ý bên phải hoặc nhập câu hỏi của bạn bên dưới.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} showDebug={showDebug} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Khung nhap cau hoi */}
      <div className="chat-input-area">
        {error && (
          <div className="chat-error-banner">
            {error}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="chat-input-row"
        >
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Nhập câu hỏi tuyển sinh của bạn tại đây... (Enter để gửi, Shift+Enter để xuống dòng)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            maxLength={2000}
          />
          <button
            type="submit"
            className="chat-submit-btn"
            disabled={isLoading || !input.trim()}
            title="Gửi câu hỏi"
          >
            {isLoading ? (
              <span className="submit-btn-spinner" />
            ) : (
              <svg className="submit-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 18, height: 18 }}>
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            )}
          </button>
        </form>

        <div className="chat-input-footer">
          <button
            type="button"
            className="btn-clear-chat"
            onClick={handleNewConversation}
            disabled={messages.length === 0}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 13, height: 13, marginRight: 6 }}>
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
            </svg>
            Cuộc trò chuyện mới
          </button>
          
          <div className="chat-input-footer-right">
            <span className="char-counter">{input.length}/2000</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export type { ChatPanelProps };
