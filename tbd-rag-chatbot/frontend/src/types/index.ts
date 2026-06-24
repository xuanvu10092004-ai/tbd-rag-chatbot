// Dinh nghia TypeScript interfaces cho TBD RAG Chatbot
// Phu hop chinh xac voi schema API Revision 3.1

/** Mot nguon trich dan tu ChromaDB */
export interface Source {
  title: string;
  source: string;
  source_type: 'official_website' | 'curated_faq' | 'uploaded_file';
  snippet: string;
  distance: number;
  original_url: string | null;
  local_path: string | null;
}

/** Response tu POST /api/chat */
export interface ChatResponse {
  answer: string;
  sources: Source[];
  has_context: boolean;
  retrieved_count: number;
  conversation_id: string;
  answer_type: 'greeting' | 'clarification' | 'faq_direct' | 'rag_generated' | 'fallback' | 'error';
  performance: {
    total_ms: number;
    gemini_called: boolean;
    rewrite_called: boolean;
    faq_matched: boolean;
    cache_hit: boolean;
    embedding_ms: number;
    vector_search_ms: number;
    generation_ms: number;
    intent: string;
    search_strategy: string;
  };
}

/** Mot tin nhan trong giao dien chat */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  has_context?: boolean;
  timestamp: string;
  is_loading?: boolean; // Dung de hien thi trang thai cho
  answer_type?: 'greeting' | 'clarification' | 'faq_direct' | 'rag_generated' | 'fallback' | 'error';
  performance?: {
    total_ms: number;
    gemini_called: boolean;
    rewrite_called: boolean;
    faq_matched: boolean;
    cache_hit: boolean;
    embedding_ms: number;
    vector_search_ms: number;
    generation_ms: number;
    intent: string;
    search_strategy: string;
  };
}

/** Response tu GET /api/health */
export interface HealthStatus {
  status: 'ok' | 'degraded' | 'error';
  backend_port: number;
  gemini_configured: boolean;
  vector_db_count: number;
  collection_name: string;
  local_data_ready: boolean;
  message: string;
  model_id?: string;
  embed_model?: string;
}

/** Response tu cac endpoint ingest */
export interface IngestResult {
  added: number;
  skipped: number;
  failed: number;
  message: string;
}

/** Request toi POST /api/chat */
export interface ChatRequest {
  question: string;
  conversation_id?: string;
}

/** Request toi POST /api/ingest/urls */
export interface IngestUrlsRequest {
  urls: string[];
}

