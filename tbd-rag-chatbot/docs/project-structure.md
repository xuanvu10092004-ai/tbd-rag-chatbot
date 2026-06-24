# Cấu trúc và Chi tiết Dự án TBD RAG Chatbot

Tài liệu này mô tả chi tiết cấu trúc thư mục và vai trò của từng file trong dự án chatbot hỗ trợ tuyển sinh của Trường Đại học Thái Bình Dương (TBD).

## 1. Cấu trúc tổng quan

```text
tbd-rag-chatbot/
├── .gitignore                  # Cấu hình bỏ qua các file không cần thiết khi commit Git
├── README.md                   # Thông tin chung về dự án, hướng dẫn cài đặt và sử dụng
├── start.bat                   # Script khởi động chính, tự động gọi 2 script con bên dưới
├── stop.bat                    # Script dừng hệ thống (tắt các tiến trình Node và Python)
├── _run_backend.bat            # Script phụ để kích hoạt môi trường ảo (venv) và chạy server FastAPI
├── _run_frontend.bat           # Script phụ để chạy server React/Vite (npm run dev)
├── backend/                    # Mã nguồn Backend (Python FastAPI)
├── frontend/                   # Mã nguồn Frontend (React + TypeScript + Vite)
└── docs/                       # Thư mục chứa các tài liệu kỹ thuật của dự án
```

---

## 2. Thư mục Backend (`backend/`)

Backend xử lý logic luồng RAG, thao tác với Vector DB (ChromaDB), và giao tiếp với Google Gemini AI.

### 2.1. Cấu hình chung

- **`.env` / `.env.example`**: Chứa các biến môi trường cấu hình hệ thống (như `GEMINI_API_KEY`).
- **`requirements.txt`**: Danh sách các thư viện Python cần thiết (`fastapi`, `chromadb`, `google-genai`, v.v.).

### 2.2. Module chính (`app/`)

- **`main.py`**: Điểm vào (entry point) của ứng dụng FastAPI. Khởi tạo server, cấu hình CORS, đăng ký các router API và quản lý vòng đời ứng dụng (startup/shutdown).
- **`config.py`**: Định nghĩa class cấu hình trung tâm (sử dụng `pydantic-settings`). Đọc và xác thực các biến môi trường từ file `.env`. Cung cấp đường dẫn cố định đến các thư mục dữ liệu.
- **`rag_pipeline.py`**: **Core logic của hệ thống RAG**. Chịu trách nhiệm điều phối toàn bộ luồng xử lý: nhận câu hỏi → truy xuất lịch sử hội thoại → tìm kiếm ngữ cảnh liên quan (ChromaDB) → xử lý Fallback (nếu không có ngữ cảnh) → gọi Gemini API sinh câu trả lời → lưu lại lịch sử. Có cơ chế "fast path" trả lời ngay các câu hỏi FAQ khớp chính xác.
- **`vector_store.py`**: Tương tác với ChromaDB. Định nghĩa các hàm khởi tạo DB, thêm tài liệu mới (`add_documents`), và truy vấn các đoạn văn bản tương đồng với câu hỏi (`query_similar`). Sử dụng `PersistentClient` để lưu dữ liệu xuống đĩa cứng.
- **`document_loader.py`**: Phụ trách việc đọc và trích xuất nội dung từ nhiều nguồn khác nhau: tải file cục bộ (.txt, .pdf, .docx, .md) hoặc tải nội dung trực tiếp từ URL website TBD (có kiểm tra whitelist domain).
- **`chunker.py`**: Chịu trách nhiệm chia nhỏ văn bản dài thành các đoạn (chunks) hợp lý để đưa vào Vector DB. Sử dụng `RecursiveCharacterTextSplitter` của LangChain để tách theo ngữ nghĩa (đoạn, câu, từ) thay vì cắt ngang chữ.
- **`gemini_client.py`**: Wrapper giao tiếp với Google Gemini API. Cung cấp các hàm nhúng tài liệu (`embed_document`), nhúng câu hỏi (`embed_query`), và sinh câu trả lời dựa trên ngữ cảnh (`generate_answer`).
- **`conversation_store.py`**: Lưu trữ và quản lý lịch sử hội thoại trong bộ nhớ (RAM) để giữ ngữ cảnh cho chatbot, cho phép người dùng hỏi các câu hỏi tiếp nối.
- **`hasher.py`**: Chứa các hàm tạo mã băm (hash) SHA-256 để định danh duy nhất cho từng chunk và tài liệu. Giúp phát hiện và bỏ qua các nội dung trùng lặp khi nạp dữ liệu nhiều lần.
- **`seed_urls.py`**: Danh sách các URL chính thức của trường TBD được cấu hình sẵn để crawl dữ liệu ban đầu.

### 2.3. Các API Routes (`app/routes/`)

- **`chat.py`**: Xử lý logic API `POST /api/chat`. Nhận request từ người dùng, gọi `rag_pipeline.run()` và trả kết quả về frontend.
- **`ingest.py`**: Chứa các API dùng để nạp dữ liệu vào hệ thống: tải lên file, crawl URL, hoặc nạp từ dữ liệu local đã đồng bộ.
- **`health.py`**: API `GET /api/health` trả về trạng thái hoạt động của hệ thống (kết nối DB, trạng thái Gemini API).

### 2.4. Services (`app/services/`)

- **`website_sync_service.py`**: Service phụ trách đồng bộ nội dung từ website TBD về lưu trữ cục bộ dưới dạng JSON/Markdown, duy trì một file `sync_manifest.json` để quản lý trạng thái đồng bộ.

### 2.5. Các thư mục dữ liệu

- **`chroma_db/`**: Nơi lưu trữ persistent của Vector Database ChromaDB.
- **`data/`**: Chứa dữ liệu thô và dữ liệu đã xử lý.
  - `data/raw/faq/`: Chứa các file JSON chứa câu hỏi thường gặp đã được chuẩn hóa.
  - `data/raw/web_pages/`: Nơi lưu trữ các trang web đã được đồng bộ về (dưới dạng .json và .md).
  - `data/raw/uploaded_files/`: Nơi lưu các file tài liệu tải lên từ trang quản trị.
- **`logs/`**: Chứa các file log hệ thống sinh ra trong quá trình hoạt động.

### 2.6. Scripts (`scripts/`)

- **`sync_and_ingest_official_data.py`** / **`seed_official_data.py`**: Các công cụ chạy độc lập để tự động crawl dữ liệu từ các link cấu hình và nạp vào ChromaDB.

---

## 3. Thư mục Frontend (`frontend/`)

Cung cấp giao diện người dùng tương tác, xây dựng bằng React và TypeScript.

### 3.1. Thành phần cấu hình

- **`package.json`**: Thông tin metadata của project, chứa các scripts chạy (dev, build) và khai báo các thư viện phụ thuộc (`react`, `vite`, v.v.).
- **`vite.config.ts`**: Cấu hình công cụ Vite, định nghĩa cổng chạy (port) và setup proxy để frontend có thể gọi backend API tránh lỗi CORS.
- **`tsconfig.json`**: Cấu hình TypeScript cho dự án.

### 3.2. Mã nguồn chính (`src/`)

- **`App.tsx`**: Component gốc của ứng dụng. Quản lý state điều hướng (chuyển đổi giữa giao diện Chat và trang Quản trị), và bố cục tổng thể (Header, Main, Sidebar).
- **`index.css`**: Chứa toàn bộ các class CSS dùng để styling cho dự án (sử dụng hệ thống biến CSS, hiệu ứng glassmorphism, responsive design).

### 3.3. Các Components (`src/components/`)

- **`ChatPanel.tsx`**: Khung giao diện chính để hiển thị cuộc trò chuyện. Xử lý việc nhập tin nhắn, hiển thị loading, và tự động cuộn xuống tin nhắn mới nhất.
- **`MessageBubble.tsx`**: Thành phần hiển thị một bong bóng tin nhắn đơn lẻ. Định dạng lại nội dung markdown thành HTML để hiển thị đẹp mắt, phân biệt tin nhắn của User và Bot.
- **`SourcePanel.tsx`**: Panel hiển thị danh sách các tài liệu nguồn (citations) mà chatbot đã sử dụng để trả lời câu hỏi.
- **`SuggestedQuestions.tsx`**: Hiển thị các câu hỏi gợi ý để người dùng có thể nhấp vào hỏi nhanh.
- **`StatusIndicator.tsx`**: Component nhỏ trên Sidebar hiển thị trạng thái hiện tại của hệ thống (đang kết nối, lỗi, offline...).
- **`AdminPage.tsx`**: Giao diện trang quản trị. Cho phép người quản trị theo dõi tổng quan số lượng tài liệu, upload tài liệu mới (kéo thả file), quản lý đồng bộ URL, và xem các trạng thái hệ thống chi tiết.

### 3.4. Dịch vụ và Kiểu dữ liệu

- **`services/api.ts`**: File chứa tất cả các hàm gọi API tương tác với Backend (`sendMessage`, `getHealth`, `uploadFiles`, `ingestUrls`...). Đóng gói logic fetch, timeout và xử lý lỗi.
- **`types/index.ts`**: Khai báo các interface và type cho TypeScript (ví dụ: `ChatRequest`, `Source`, `Message`), giúp code an toàn và dễ maintain.
