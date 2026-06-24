#  TBD RAG Chatbot — Trợ Lý Tuyển Sinh Trường Đại Học Thái Bình Dương

> Hệ thống chatbot thông minh hỗ trợ tư vấn tuyển sinh chính thức của **Trường Đại học Thái Bình Dương (TBD)**, xây dựng trên kiến trúc **RAG (Retrieval-Augmented Generation)** kết hợp **Gemini AI** và **ChromaDB**.

---

###  Thông Tin Dự Án

| Mục | Nội dung |
|---|---|
| **Sinh viên thực hiện** | Nguyễn Xuân Vũ — MSSV: 230440 |
| **Giảng viên hướng dẫn** | TS. Nguyễn Trùng Lập |
| **Trường** | Đại học Thái Bình Dương (TBD) |
| **Lớp học phần** | Dự án Công nghệ Thông tin |
| **Hoàn thành** | Tháng 06/2026 |

---

##  Tính Năng Chính

-  **Trả lời tức thì (FAQ Direct Match):** Câu hỏi thường gặp được khớp ngữ nghĩa trực tiếp, phản hồi trong ~50ms, không tốn quota API.
-  **Tìm kiếm RAG thông minh:** Truy xuất các đoạn tài liệu liên quan từ ChromaDB rồi dùng Gemini tổng hợp câu trả lời chính xác.
-  **Viết lại câu hỏi hội thoại:** Tự động làm rõ câu hỏi tiếp nối dựa vào lịch sử trò chuyện.
-  **Chống thông tin sai (Fallback):** Từ chối trả lời các câu hỏi nằm ngoài phạm vi tuyển sinh một cách lịch sự.
-  **Trang Quản trị:** Upload tài liệu PDF/TXT mới và xem trạng thái hệ thống trực tiếp trên giao diện.
-  **Khởi động 1-click:** Chỉ cần chạy `start.bat` — tự động cài đặt và khởi động toàn hệ thống.

---

##  Kiến Trúc Hệ Thống

```
Người dùng
    │
    ▼
Frontend (React + TypeScript + Vite)
    │  HTTP API
    ▼
Backend (Python FastAPI)
    ├── Khớp nhanh FAQ? ──► Trả lời ngay (không gọi LLM)
    ├── Viết lại câu hỏi (Gemini)
    ├── Nhúng vector (Gemini Embedding)
    ├── Tìm kiếm ChromaDB
    └── Tổng hợp câu trả lời (Gemini Flash)
```

| Thành phần | Công nghệ |
|---|---|
| **Frontend** | React 18 + TypeScript + Vite |
| **Backend** | Python 3.10 + FastAPI |
| **Vector DB** | ChromaDB (lưu cục bộ) |
| **AI Model** | Gemini 2.5 Flash |
| **Embedding** | `gemini-embedding-001` (768 chiều) |

---

##  Yêu Cầu Hệ Thống

- **Node.js** ≥ 18
- **Python** ≥ 3.10
- **Gemini API Key** — lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/)

---

##  Hướng Dẫn Cài Đặt & Khởi Động

### Cách 1 — Tự động 1-click (Windows)  Khuyên dùng

```
1. Nhấp đúp vào file  start.bat
2. Lần đầu: điền GEMINI_API_KEY vào file .env khi được yêu cầu
3. Lưu file và nhấn phím bất kỳ → hệ thống tự cài & khởi động
4. Truy cập: http://localhost:5173
5. Để dừng: nhấp đúp stop.bat
```

### Cách 2 — Thủ công từng bước

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # Điền GEMINI_API_KEY vào file .env
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

##  Nạp Dữ Liệu Tuyển Sinh

Sau khi khởi động, truy cập trang **Quản trị** tại `http://localhost:5173` → nhấn nút **"Quản trị"** trên header → kéo thả file tài liệu (PDF, TXT) để nạp vào hệ thống.

Hoặc dùng script để đồng bộ dữ liệu website TBD:
```bash
cd backend
venv\Scripts\activate
python scripts/sync_and_ingest_official_data.py
```

---

##  Cấu Trúc Thư Mục

```
tbd-rag-chatbot/
├── README.md                        # File này
├── start.bat                        # Khởi động toàn hệ thống (1-click)
├── stop.bat                         # Dừng toàn hệ thống
├── .gitignore
│
├── backend/
│   ├── .env.example                 # Mẫu cấu hình (copy → .env)
│   ├── requirements.txt             # Thư viện Python
│   ├── app/
│   │   ├── main.py                  # Khởi chạy FastAPI
│   │   ├── config.py                # Cấu hình & biến môi trường
│   │   ├── rag_pipeline.py          # Luồng xử lý RAG chính
│   │   ├── vector_store.py          # Thao tác ChromaDB
│   │   ├── document_loader.py       # Đọc tài liệu PDF/TXT/JSON
│   │   ├── chunker.py               # Chia văn bản thông minh
│   │   ├── gemini_client.py         # Gọi Gemini API
│   │   ├── conversation_store.py    # Lưu lịch sử hội thoại
│   │   ├── hasher.py                # Băm SHA-256 chống trùng lặp
│   │   ├── routes/                  # API endpoints (chat, health, ingest)
│   │   └── services/                # Dịch vụ crawl website
│   ├── scripts/
│   │   ├── seed_urls.py             # Danh sách URL crawl
│   │   ├── seed_official_data.py    # Script nạp dữ liệu ban đầu
│   │   └── sync_and_ingest_official_data.py
│   ├── data/
│   │   ├── raw/faq/                 # Bộ FAQ chuẩn hóa (.json)
│   │   ├── raw/web_pages/           # Trang web đã crawl (.json)
│   │   ├── raw/uploaded_files/      # File do admin upload
│   │   ├── processed/               # sync_manifest.json
│   │   └── snapshots/               # Snapshot mới nhất
│   ├── chroma_db/                   # CSDL vector (tự tạo lúc chạy)
│   └── logs/                        # Log hệ thống
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx                  # Component gốc & điều hướng
│       ├── index.css                # Giao diện Light Theme TBD
│       ├── components/              # Chat, Admin, Message, Source...
│       ├── services/api.ts          # Gọi API backend
│       └── types/                   # TypeScript types
│
└── docs/
    ├── BAO_CAO.md                   # Báo cáo chi tiết dự án
    ├── api-endpoints.md             # Tài liệu API
    ├── project-architecture.md      # Kiến trúc hệ thống
    └── test-plan.md                 # Kế hoạch kiểm thử
```

---

##  Kiểm Tra Nhanh qua API

```bash
# Kiểm tra hệ thống còn sống không
curl http://localhost:8001/api/health

# Hỏi về ngành học
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Trường TBD có những ngành nào?"}'
```

---

>  Xem báo cáo đầy đủ: [docs/BAO_CAO.md](docs/BAO_CAO.md)
