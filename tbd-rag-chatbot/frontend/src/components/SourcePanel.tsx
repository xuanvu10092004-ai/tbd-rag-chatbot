import type { Source } from '../types';

interface SourcePanelProps {
  sources: Source[];
  isAdminMode?: boolean;
}

export function SourcePanel({ sources, isAdminMode = false }: SourcePanelProps) {
  // Map loai nguon sang tieng Viet
  const getSourceTypeLabel = (type: string) => {
    switch (type) {
      case 'official_website':
        return 'Dữ liệu website chính thức';
      case 'curated_faq':
        return 'Câu hỏi tuyển sinh';
      case 'uploaded_file':
        return 'Tài liệu đã tải lên';
      default:
        return 'Nguồn tài liệu';
    }
  };

  // Tra ve Icon SVG tuong ung voi loai nguon
  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'official_website':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="source-badge-icon" style={{ width: 12, height: 12 }}>
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
        );
      case 'curated_faq':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="source-badge-icon" style={{ width: 12, height: 12 }}>
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        );
      case 'uploaded_file':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="source-badge-icon" style={{ width: 12, height: 12 }}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        );
      default:
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="source-badge-icon" style={{ width: 12, height: 12 }}>
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
        );
    }
  };

  return (
    <div className="card source-panel">
      <div className="card-header">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15, marginRight: 8, color: 'var(--color-primary)' }}>
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
        Nguồn trích dẫn
      </div>

      {sources.length === 0 ? (
        <div className="source-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 28, height: 28, marginBottom: 12, opacity: 0.2 }}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Chưa có nguồn trích dẫn
          <div className="source-empty-sub">
            Khi chatbot trả lời từ cơ sở dữ liệu, các tài liệu đối sánh cụ thể sẽ hiển thị tại đây.
          </div>
        </div>
      ) : (
        <div className="source-list">
          {sources.map((source, index) => (
            <div key={`${source.source}-${index}`} className="source-item">
              {/* Tiêu đề nguồn */}
              <div className="source-item-title">
                <span className="source-title-text">{source.title || source.source}</span>
                <span className={`source-type-badge ${source.source_type}`}>
                  {getSourceIcon(source.source_type)}
                  {getSourceTypeLabel(source.source_type)}
                </span>
              </div>

              {/* URL gốc nếu có */}
              {source.original_url ? (
                <a
                  href={source.original_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-item-url"
                  title={source.original_url}
                >
                  {source.original_url}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 10, height: 10, marginLeft: 4, display: 'inline-block' }}>
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              ) : source.source_type === 'official_website' ? (
                <a
                  href={source.source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="source-item-url"
                  title={source.source}
                >
                  {source.source}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 10, height: 10, marginLeft: 4, display: 'inline-block' }}>
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              ) : null}

              {/* Đoạn trích ngắn */}
              {source.snippet && (
                <p className="source-item-snippet">{source.snippet}</p>
              )}

              {/* Hiển thị đường dẫn local trong debug */}
              {isAdminMode && source.local_path && (
                <div className="source-item-debug-path">
                  Đường dẫn: {source.local_path}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
