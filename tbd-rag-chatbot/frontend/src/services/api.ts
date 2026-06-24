// Service goi API backend cho TBD RAG Chatbot
// Tat ca request deu di qua /api (duoc proxy boi Vite den localhost:8000)
// Khong bao gio gui GEMINI_API_KEY tu frontend

import type {
  ChatRequest,
  ChatResponse,
  HealthStatus,
  IngestResult,
  IngestUrlsRequest,
} from '../types';

// Base URL - Doc tu env config, mac dinh localhost:8001 de phu hop voi moi truong standardized
const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8001') + '/api';

/** Custom fetch with timeout wrapper */
async function fetchWithTimeout(resource: string, options: RequestInit & { timeout?: number } = {}): Promise<Response> {
  const { timeout = 20000, ...fetchOptions } = options;
  
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(resource, {
      ...fetchOptions,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error: any) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new Error('Hệ thống phản hồi quá lâu. Vui lòng thử lại hoặc kiểm tra backend.');
    }
    throw error;
  }
}

/** Xu ly loi chung khi goi API */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `Lỗi ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch {
      // Giu nguyen thong bao loi mac dinh
    }
    throw new Error(errorMessage);
  }
  return response.json() as Promise<T>;
}

/**
 * Gui cau hoi den chatbot.
 * Truyen conversation_id de duy tri lich su hoi thoai.
 */
export async function sendMessage(
  question: string,
  conversationId?: string,
): Promise<ChatResponse> {
  const body: ChatRequest = {
    question,
    conversation_id: conversationId,
  };

  const response = await fetchWithTimeout(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    timeout: 20000,
  });

  return handleResponse<ChatResponse>(response);
}

/**
 * Ingest danh sach URL cua TBD vao ChromaDB.
 * Backend se tu choi URL ngoai domain tbd.edu.vn.
 */
export async function ingestUrls(urls: string[]): Promise<IngestResult> {
  const body: IngestUrlsRequest = { urls };

  const response = await fetchWithTimeout(`${API_BASE}/ingest/urls`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    timeout: 20000,
  });

  return handleResponse<IngestResult>(response);
}

/**
 * Upload va ingest file tai lieu vao ChromaDB.
 * Ho tro: .txt, .pdf, .docx, .md (toi da 10MB moi file)
 */
export async function uploadFiles(files: File[]): Promise<IngestResult> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await fetchWithTimeout(`${API_BASE}/ingest/files`, {
    method: 'POST',
    body: formData,
    timeout: 20000,
    // Khong dat Content-Type - de browser tu dong dat multipart/form-data
  });

  return handleResponse<IngestResult>(response);
}

/**
 * Xoa va xay lai toan bo ChromaDB tu danh sach URL mac dinh cua TBD.
 */
export async function rebuildIndex(): Promise<IngestResult> {
  const response = await fetchWithTimeout(`${API_BASE}/ingest/rebuild`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    timeout: 20000,
  });

  return handleResponse<IngestResult>(response);
}

/**
 * Lay trang thai he thong (Gemini API, ChromaDB, model ID).
 */
export async function getHealth(): Promise<HealthStatus> {
  const response = await fetchWithTimeout(`${API_BASE}/health`, {
    method: 'GET',
    timeout: 5000,
  });

  return handleResponse<HealthStatus>(response);
}

/**
 * Dong bo tat ca seed URLs tu admin.
 */
export async function syncSeedUrls(): Promise<{ total_urls: number; successful_urls: number; failed_urls: number; snapshot_file: string | null }> {
  const response = await fetchWithTimeout(`${API_BASE}/admin/sync/seed-urls`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    timeout: 20000,
  });

  return handleResponse(response);
}

/**
 * Dong bo mot URL bat ky tu admin.
 */
export async function syncUrl(url: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/admin/sync/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    timeout: 20000,
  });

  return handleResponse(response);
}

/**
 * Lay trang thai dong bo tu manifest cuc bo.
 */
export async function getSyncStatus(): Promise<{
  total_pages: number;
  last_sync_time: string | null;
  total_content_size_bytes: number;
  total_monitored_urls: number;
  failed_urls: Array<{ url: string; error: string }>;
}> {
  const response = await fetchWithTimeout(`${API_BASE}/admin/sync/status`, {
    method: 'GET',
    timeout: 20000,
  });

  return handleResponse(response);
}

/**
 * Nap du lieu tu thu muc cuc bo vao vector database ChromaDB.
 */
export async function ingestLocal(rebuild: boolean = true): Promise<IngestResult> {
  const response = await fetchWithTimeout(`${API_BASE}/ingest/local`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rebuild }),
    timeout: 20000,
  });

  return handleResponse<IngestResult>(response);
}
