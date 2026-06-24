import { useEffect, useRef, useState } from 'react';
import {
  getSyncStatus,
  uploadFiles,
  getHealth,
} from '../services/api';
import type { IngestResult } from '../types';

export function AdminPage() {
  // Trạng thái hệ thống đơn giản
  const [dbCount, setDbCount] = useState<number>(0);
  const [lastSyncTime, setLastSyncTime] = useState<string>('');
  const [isSystemOnline, setIsSystemOnline] = useState<boolean>(true);

  // Trạng thái tải tệp tài liệu
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState<IngestResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Tải thông tin thống kê cơ bản
  const loadSystemInfo = async () => {
    try {
      const health = await getHealth();
      setDbCount(health.vector_db_count);
      setIsSystemOnline(true);
      
      const status = await getSyncStatus();
      if (status.last_sync_time) {
        setLastSyncTime(new Date(status.last_sync_time).toLocaleString('vi-VN'));
      }
    } catch (err) {
      console.error('Không thể kết nối đến máy chủ:', err);
      setIsSystemOnline(false);
    }
  };

  useEffect(() => {
    loadSystemInfo();
  }, []);

  // Xử lý tải tệp tài liệu mới lên
  const handleUploadFiles = async () => {
    if (selectedFiles.length === 0) return;

    setUploadLoading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const res = await uploadFiles(selectedFiles);
      setUploadResult(res);
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadSystemInfo();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Có lỗi xảy ra khi tải tài liệu lên.');
    } finally {
      setUploadLoading(false);
    }
  };

  // Quản lý danh sách file đã chọn
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    setSelectedFiles((prev) => [...prev, ...files]);
    setUploadError(null);
    setUploadResult(null);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="admin-layout" style={{ maxWidth: '800px', margin: '0 auto', width: '100%', height: 'auto', overflow: 'visible' }}>
      {/* Banner cảnh báo nội bộ thân thiện */}
      <div className="admin-warning-banner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 20, height: 20, flexShrink: 0 }}>
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <div className="admin-warning-content">
          <strong>KHU VỰC QUẢN TRỊ DỮ LIỆU</strong>
          <p>Tại đây, thầy cô hoặc quản trị viên có thể dễ dàng tải tài liệu tuyển sinh mới lên để cập nhật kiến thức cho chatbot.</p>
        </div>
      </div>

      {/* Tải tài liệu bổ sung */}
      <div className="admin-card">
        <div className="admin-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 16, height: 16 }}>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>Tải Lên Tài Liệu Tuyển Sinh Mới</span>
        </div>
        <div className="admin-card-body">
          <p className="admin-card-desc">
            Chọn các tệp văn bản từ máy tính của bạn (hỗ trợ định dạng PDF, Word hoặc văn bản thô) để cung cấp tài liệu tuyển sinh mới cho AI.
          </p>
          
          <div
            className="file-drop-zone"
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.pdf,.docx,.md,.markdown"
              onChange={handleFileChange}
              disabled={uploadLoading}
              style={{ display: 'none' }}
            />
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="dropzone-cloud-icon">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <div className="file-drop-label">
              <strong>Chọn tài liệu từ máy tính</strong>
              <span>hoặc kéo thả tệp vào đây (.pdf, .docx, .txt)</span>
            </div>
          </div>

          {selectedFiles.length > 0 && (
            <div className="selected-files-list">
              <div className="selected-files-title">Các tài liệu đã chọn ({selectedFiles.length}):</div>
              {selectedFiles.map((f, idx) => (
                <div key={`${f.name}-${idx}`} className="selected-file-item">
                  <div className="selected-file-info">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 13, height: 13, color: 'var(--color-primary)' }}>
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    <span className="selected-file-name">{f.name}</span>
                    <span className="selected-file-size">({(f.size / 1024).toFixed(1)} KB)</span>
                  </div>
                  <button
                    type="button"
                    className="btn-remove-selected-file"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveFile(idx);
                    }}
                    title="Hủy chọn"
                  >
                    &times;
                  </button>
                </div>
              ))}
            </div>
          )}

          {uploadError && <div className="admin-result-box error admin-margin-top-12">{uploadError}</div>}
          
          {uploadResult && (
            <div className="admin-result-box success admin-margin-top-12">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 14, height: 14, marginRight: 6 }}>
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>Nạp tài liệu thành công! Chatbot đã tích hợp thêm {uploadResult.added} kiến thức từ tệp tải lên.</span>
            </div>
          )}

          <button
            className="btn btn-primary w-full admin-margin-top-12"
            onClick={handleUploadFiles}
            disabled={uploadLoading || selectedFiles.length === 0}
            type="button"
          >
            {uploadLoading ? 'Đang nạp tài liệu vào bộ nhớ AI...' : `Xác nhận tải lên ${selectedFiles.length} tài liệu`}
          </button>
        </div>
      </div>

      {/* Trạng thái hệ thống ở cuối */}
      <div className="admin-card admin-margin-top-24">
        <div className="admin-card-header">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ width: 16, height: 16 }}>
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
          </svg>
          <span>Trạng Thái Bộ Nhớ Chatbot</span>
        </div>
        <div className="admin-card-body">
          <div className="admin-test-success-grid">
            <div className="test-metric-card">
              <div className="metric-title">Kết nối Máy chủ</div>
              <div className={`metric-value ${isSystemOnline ? 'green' : 'orange'}`}>
                {isSystemOnline ? 'ĐÃ KẾT NỐI' : 'MẤT KẾT NỐI'}
              </div>
            </div>
            <div className="test-metric-card">
              <div className="metric-title">Số lượng phân mảnh kiến thức</div>
              <div className="metric-value glow-blue">{dbCount} phân mảnh</div>
            </div>
            <div className="test-metric-card">
              <div className="metric-title">Cập nhật gần nhất</div>
              <div className="metric-value">{lastSyncTime || 'Chưa đồng bộ'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
