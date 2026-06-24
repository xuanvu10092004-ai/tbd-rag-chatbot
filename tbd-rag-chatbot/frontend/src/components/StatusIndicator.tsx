import { useEffect, useState } from 'react';
import { getHealth } from '../services/api';
import type { HealthStatus } from '../types';

interface StatusIndicatorProps {
  showDebug?: boolean;
}

export function StatusIndicator({ showDebug = false }: StatusIndicatorProps) {
  const [status, setStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Kiểm tra trạng thái định kỳ 30s
  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const result = await getHealth();
        if (!cancelled) {
          setStatus(result);
          setError(null);
        }
      } catch (err: any) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unknown Network Error');
          setStatus(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 30_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Xác định class CSS, biểu tượng SVG và văn bản hiển thị
  let statusType: 'loading' | 'ok' | 'warning' | 'error' = 'loading';
  let statusText = 'Đang kiểm tra kết nối...';
  let statusIcon = (
    <span className="status-dot-pulse" />
  );

  if (!loading) {
    if (error || !status) {
      statusType = 'error';
      statusText = 'Không thể kết nối API';
      statusIcon = (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="status-shield-svg error" style={{ width: 16, height: 16 }}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      );
    } else if (!status.gemini_configured) {
      statusType = 'warning';
      statusText = 'Gemini chưa được cấu hình';
      statusIcon = (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="status-shield-svg warning" style={{ width: 16, height: 16 }}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      );
    } else if (status.vector_db_count <= 0) {
      statusType = 'warning';
      statusText = 'Cơ sở dữ liệu Vector trống';
      statusIcon = (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="status-shield-svg warning" style={{ width: 16, height: 16 }}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      );
    } else {
      statusType = 'ok';
      statusText = 'Hệ thống: Sẵn sàng';
      statusIcon = (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="status-shield-svg ok" style={{ width: 16, height: 16 }}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <polyline points="9 11 12 14 15 9" />
        </svg>
      );
    }
  }

  return (
    <div className="card status-panel-card">
      <div className="card-header">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 15, height: 15, marginRight: 8, color: 'var(--color-primary)' }}>
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <line x1="9" y1="9" x2="15" y2="9" />
          <line x1="9" y1="13" x2="15" y2="13" />
          <line x1="9" y1="17" x2="13" y2="17" />
        </svg>
        Trạng thái hệ thống
      </div>
      <div className="status-card-body">
        <div className={`status-state-container ${statusType}`}>
          <div className="status-icon-wrapper">{statusIcon}</div>
          <span className="status-text">{statusText}</span>
        </div>

        {showDebug && error && (
          <div className="status-debug-hint ingest-result error">
            <div className="status-debug-title">Chi tiết lỗi kết nối (Debug):</div>
            <div>- URL: http://localhost:8001/api/health</div>
            <div>- Lỗi: {error}</div>
          </div>
        )}


      </div>
    </div>
  );
}
