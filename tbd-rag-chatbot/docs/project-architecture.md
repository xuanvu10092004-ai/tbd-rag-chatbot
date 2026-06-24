#  Kiến Trúc Dự Án - TBD RAG Chatbot

## Tổng quan

TBD RAG Chatbot là hệ thống hỏi đáp tự động tuyển sinh cho **Trường Đại học Thái Bình Dương (TBD)**. 
Hệ thống sử dụng kiến trúc **Retrieval-Augmented Generation (RAG)** để đảm bảo chatbot phản hồi chính xác dựa trên dữ liệu tuyển sinh chính thức đã được phê duyệt, tránh hiện tượng ảo tưởng thông tin (hallucination) của mô hình AI.

---

##  Sơ đồ luồng dữ liệu xử lý câu hỏi

```text
[Người dùng]
    | POST /api/chat { question, conversation_id? }
    v
[FastAPI Backend]
    |
    +--[1] ConversationStore.get_history(conversation_id)
    |         -> Lấy lịch sử 10 tin nhắn gần nhất để làm ngữ cảnh
    |
    +--[2] rewrite_query_with_history(question, history)
    |         -> Gemini viết lại câu hỏi nối tiếp (follow-up) thành câu độc lập
    |         -> Ví dụ: "Ngành đó học phí thế nào?" -> "Ngành CNTT tại TBD học phí thế nào?"
    |
    +--[3] embed_query(standalone_query)
    |         -> Chuyển đổi câu hỏi độc lập thành vector nhúng 768 chiều
    |
    +--[4] ChromaDB.query(vector, n_results=12)
    |         -> Tìm kiếm 12 chunk có khoảng cách ngữ nghĩa gần nhất (cosine distance)
    |
    +--[5] _find_exact_faq_match(question, retrieved_chunks)
    |         -> Đối soát nhanh các FAQ tĩnh. Nếu khớp (khoảng cách <= 0.25 + trùng từ khóa cốt lõi):
    |            Trả về kết quả trực tiếp ngay lập tức, BỎ QUA gọi Gemini API để tiết kiệm tài nguyên
    |
    +--[6] _filter_relevant_chunks(chunks, threshold=0.65)
    |         -> Bỏ qua các chunk có distance > 0.65 (không liên quan)
    |         -> Nếu không còn chunk nào liên quan: trả về thông báo Fallback tĩnh lập tức
    |
    +--[7] generate_answer(context, question, standalone, history)
    |         -> Gọi mô hình Gemini Flash tổng hợp câu trả lời dựa trên ngữ cảnh đã lọc
    |
    +--[8] ConversationStore.add_message(conversation_id, ...)
    |         -> Lưu câu hỏi và câu trả lời vào lịch sử cuộc trò chuyện
    |
    v
[Kết quả trả về] { answer, sources, has_context, retrieved_count, conversation_id }
```

---

##  Luồng Nạp Dữ Liệu Cục Bộ (Local-First Ingestion)

```text
[Giao diện Admin / CLI Script]
    | POST /api/admin/sync/seed-urls hoặc chạy python scripts/sync_and_ingest_official_data.py
    v
[document_loader.py]
    | Tải nội dung trang web chính thức (HTML -> Markdown sạch)
    | Kiểm tra danh sách tên miền được phép (Domain Whitelist)
    v
[chunker.py]
    | Tách văn bản thành các đoạn nhỏ bằng RecursiveCharacterTextSplitter
    | Cấu hình CHUNK_SIZE = 800 ký tự, CHUNK_OVERLAP = 150 ký tự
    | Bỏ qua việc chia nhỏ đối với nguồn "curated_faq" để giữ trọn vẹn câu hỏi-trả lời
    v
[hasher.py]
    | Tạo mã định danh duy nhất (chunk_id) bằng hàm băm SHA-256
    v
[vector_store.py]
    | Kiểm tra xem chunk_id đã tồn tại trong database chưa
    |   -> Đã tồn tại: Bỏ qua (Tránh nạp trùng lặp dữ liệu)
    |   -> Chưa tồn tại: Nhúng vector -> Lưu trữ vào ChromaDB
    v
[ChromaDB] (Lưu trữ lâu dài, so khớp bằng cosine distance)
```

---

##  Các module chính ở Backend

| Module | Chức năng |
| :--- | :--- |
| `config.py` | Quản lý biến môi trường, validate API key và cấu hình hệ thống ghi log |
| `gemini_client.py` | Tương tác trực tiếp với API Gemini (Nhúng vector, Viết lại câu hỏi, Sinh câu trả lời) |
| `document_loader.py` | Đọc và làm sạch tài liệu từ các định dạng file (`.txt`, `.pdf`, `.docx`, `.md`) và crawl URL |
| `chunker.py` | Chia nhỏ văn bản thông minh, hỗ trợ xử lý đặc biệt cho tệp FAQ |
| `hasher.py` | Tạo mã hash SHA-256 để chống trùng lặp dữ liệu trong CSDL Vector |
| `vector_store.py` | Quản lý kết nối, tìm kiếm và cập nhật dữ liệu trên ChromaDB PersistentClient |
| `conversation_store.py` | Bộ nhớ tạm trong RAM (Thread-safe) lưu lịch sử các cuộc hội thoại |
| `rag_pipeline.py` | Module quan trọng nhất - Điều phối toàn bộ luồng RAG và kiểm tra so khớp FAQ nhanh |
| `routes/chat.py` | Cung cấp API endpoint `/api/chat` cho frontend gọi |
| `routes/ingest.py` | Các API nạp dữ liệu từ URL, file hoặc xây dựng lại (rebuild) database |
| `routes/health.py` | Cung cấp API kiểm tra tình trạng kết nối cơ sở dữ liệu và cấu hình mô hình |

---

##  Các Quyết Định Thiết Kế Quan Trọng

### 1. Lưu lịch sử hội thoại trong bộ nhớ tạm (In-memory)
*   Giúp tối ưu hóa tốc độ truy xuất lịch sử cuộc trò chuyện.
*   Chatbot tự kiểm soát chính xác cấu trúc prompt và lịch sử gửi đi thay vì phụ thuộc hoàn toàn vào cơ chế Chat của SDK.
*   Cho phép cắt bớt các tin nhắn cũ khi vượt giới hạn (`MAX_HISTORY_MESSAGES`).

### 2. Sử dụng khoảng cách Cosine (Cosine Distance) cho so khớp Vector
*   Embedding sinh ra từ mô hình của Google đã được chuẩn hóa (normalized vector).
*   Cosine distance biểu thị chính xác sự tương quan ngữ nghĩa giữa câu hỏi và tài liệu tuyển sinh tốt hơn khoảng cách Euclidean thông thường.

### 3. Viết lại câu hỏi (Query Rewriting)
*   Khi người dùng hỏi tiếp các câu như *"Học phí ngành đó thế nào?"*, hệ thống dùng Gemini để viết lại thành *"Học phí ngành Công nghệ thông tin thế nào?"*.
*   Điều này giúp cơ chế so khớp vector tìm đúng đoạn thông tin học phí, thay vì bị nhiễu bởi các từ chỉ định không xác định như *"ngành đó"*, *"trường này"*.
