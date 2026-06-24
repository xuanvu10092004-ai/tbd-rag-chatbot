// Ung dung chinh - dieu huong giua trang Chat va trang Admin
// Su dung useState don gian thay vi React Router de giam phu thuoc

import { useCallback, useState, useEffect } from 'react';
import { AdminPage } from './components/AdminPage';
import { ChatPanel } from './components/ChatPanel';
import { SourcePanel } from './components/SourcePanel';
import { StatusIndicator } from './components/StatusIndicator';
import { SuggestedQuestions } from './components/SuggestedQuestions';
import type { Source } from './types';
import logo from './assets/logo.png';

type Page = 'chat' | 'admin';

export function App() {
  const [currentPage, setCurrentPage] = useState<Page>('chat');
  const [sources, setSources] = useState<Source[]>([]);
  // Tham chieu den ham gui cau hoi tu ChatPanel (de SuggestedQuestions co the kich hoat)
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [showDebug, setShowDebug] = useState<boolean>(false);

  useEffect(() => {
    if (currentPage === 'admin') {
      document.body.classList.add('admin-body-active');
      document.documentElement.classList.add('admin-body-active');
    } else {
      document.body.classList.remove('admin-body-active');
      document.documentElement.classList.remove('admin-body-active');
    }
    return () => {
      document.body.classList.remove('admin-body-active');
      document.documentElement.classList.remove('admin-body-active');
    };
  }, [currentPage]);

  // Xu ly khi nguoi dung chon cau hoi goi y
  const handleSuggestedQuestion = useCallback((question: string) => {
    setCurrentPage('chat');
    setPendingQuestion(question);
  }, []);

  // Xu ly cap nhat nguon trich dan tu ChatPanel
  const handleSourcesUpdate = useCallback((newSources: Source[]) => {
    setSources(newSources);
  }, []);

  return (
    <div className="app-layout">
      {/* Background blobs for Glassmorphism */}
      <div className="bg-blob blob-purple"></div>
      <div className="bg-blob blob-blue"></div>
      <div className="bg-blob blob-indigo"></div>

      {/* Header voi tieu de va dieu huong */}
      <header className="app-header">
        <div className="app-header-left">
          <img src={logo} alt="TBD Logo" className="app-logo" />
          <div className="app-header-info">
            <div className="app-header-title">
              <span>TBD</span> Chatbot Hỗ Trợ Tuyển Sinh
            </div>
            <div className="app-header-subtitle">
              Trợ lý tra cứu thông tin từ dữ liệu chính thức của trường
            </div>
          </div>
        </div>
        <nav className="app-header-nav">
          <button
            className={`nav-btn${currentPage === 'chat' ? ' active' : ''}`}
            onClick={() => setCurrentPage('chat')}
            type="button"
          >
            <svg className="nav-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            Chatbot
          </button>
          <button
            className={`nav-btn${currentPage === 'admin' ? ' active' : ''}`}
            onClick={() => setCurrentPage('admin')}
            type="button"
          >
            <svg className="nav-btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l-.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06-.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            Quản trị
          </button>
        </nav>
      </header>

      {/* Noi dung chinh */}
      <main className="main-content">
        {currentPage === 'chat' ? (
          <div className="chat-layout">
            {/* Panel chat chinh */}
            <div className="chat-main">
              <ChatPanel
                onSourcesUpdate={handleSourcesUpdate}
                pendingQuestion={pendingQuestion}
                onPendingQuestionHandled={() => setPendingQuestion(null)}
                showDebug={showDebug}
                onShowDebugChange={setShowDebug}
              />
            </div>

            {/* Sidebar ben phai */}
            <aside className="chat-sidebar">
              <StatusIndicator showDebug={showDebug} />
              <SuggestedQuestions
                onSelect={handleSuggestedQuestion}
              />
              <SourcePanel sources={sources} isAdminMode={showDebug} />
            </aside>
          </div>
        ) : (
          <AdminPage />
        )}
      </main>
    </div>
  );
}
