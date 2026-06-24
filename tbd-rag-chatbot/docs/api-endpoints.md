# 🔌 Các Cổng API (API Endpoints) - TBD RAG Chatbot

Đường dẫn cơ bản (Base URL): `http://localhost:8001`

---

##  GET `/api/health`

Dùng để kiểm tra trạng thái hoạt động của hệ thống.

### Phản hồi mẫu (Response):
```json
{
  "status": "ok",
  "backend_port": 8001,
  "gemini_configured": true,
  "vector_db_count": 235,
  "collection_name": "tbd_knowledge_base",
  "local_data_ready": true,
  "message": "Backend đang hoạt động bình thường"
}
```

Các giá trị của trạng thái `status`:
*   `ok`: API Gemini đã được cấu hình và cơ sở dữ liệu ChromaDB có dữ liệu sẵn sàng.
*   `degraded`: Thiếu khóa API hoặc cơ sở dữ liệu trống (cần chạy Ingestion để nạp dữ liệu).
*   `error`: Không thể kết nối tới cơ sở dữ liệu ChromaDB.

---

##  POST `/api/chat`

Gửi câu hỏi của người dùng và nhận câu trả lời từ luồng xử lý RAG.

### Yêu cầu mẫu (Request Body):
```json
{
  "question": "Học phí ngành Công nghệ thông tin là bao nhiêu?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
*   `question` *(bắt buộc)*: Tối đa 2000 ký tự.
*   `conversation_id` *(tùy chọn)*: ID cuộc hội thoại dạng UUID4 nhận được ở phản hồi trước. Nếu để trống hoặc null, hệ thống sẽ tự khởi tạo một cuộc hội thoại mới.

### Phản hồi mẫu (Response):
```json
{
  "answer": "Học phí ngành Công nghệ thông tin là 740.000 đồng mỗi tín chỉ.",
  "sources": [
    {
      "title": "Học phí - Trường Đại học Thái Bình Dương",
      "source": "https://tbd.edu.vn/tuyen-sinh/hoc-phi/",
      "source_type": "url",
      "snippet": "Học phí ngành Công nghệ thông tin: 740.000đ/tín chỉ..."
    }
  ],
  "has_context": true,
  "retrieved_count": 1,
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer_type": "faq_direct_match",
  "performance": {
    "total_ms": 30,
    "gemini_called": false
  }
}
```
*   `has_context`: Trả về `false` khi câu hỏi nằm ngoài phạm vi dữ liệu đã nạp.
*   `sources`: Danh sách nguồn trích dẫn tương ứng (sẽ trống nếu `has_context` là `false`).
*   `answer_type`: Cho biết câu trả lời được sinh từ đâu (`faq_direct_match`, `rag_generated` hoặc `fallback`).

---

##  POST `/api/ingest/urls`

Nạp nội dung trực tiếp từ danh sách các đường dẫn liên kết được chỉ định.

### Yêu cầu mẫu (Request Body):
```json
{
  "urls": [
    "https://tbd.edu.vn/tuyen-sinh/hoc-phi/",
    "https://tbd.edu.vn/tuyen-sinh/hoc-bong-va-ho-tro-tai-chinh/"
  ]
}
```

### Các giới hạn tích hợp:
*   Chỉ chấp nhận các liên kết thuộc tên miền chính thức `https://tbd.edu.vn/`.
*   Tối đa nạp 20 liên kết trong một lần gọi API.
*   Không thu thập đệ quy (recursive crawl) để tránh quá tải máy chủ của trường.

### Phản hồi mẫu (Response):
```json
{
  "added": 12,
  "skipped": 4,
  "failed": 0,
  "message": "Đã xử lý xong: Thêm 12 đoạn văn mới, bỏ qua 4 đoạn trùng lặp, 0 lỗi."
}
```

---

##  POST `/api/ingest/files`

Tải lên và nạp nội dung từ các tệp tài liệu cục bộ.

*   **Định dạng yêu cầu (Request Type):** `multipart/form-data`
*   **Tham số:** File đính kèm truyền vào trường `files`.

### Các định dạng được hỗ trợ:
*   `.txt`, `.md`, `.markdown`: Các tệp văn bản thuần.
*   `.pdf`: Tệp tài liệu PDF (Sử dụng thư viện `pypdf`).
*   `.docx`: Tệp tài liệu Word (Sử dụng thư viện `python-docx`).
*   **Dung lượng giới hạn:** Tối đa 10 MB cho mỗi tệp.

### Phản hồi mẫu (Response):
```json
{
  "added": 15,
  "skipped": 0,
  "failed": 0,
  "message": "Đã xử lý xong: Thêm 15 đoạn văn mới, bỏ qua 0 trùng lặp, 0 lỗi."
}
```

---

##  POST `/api/ingest/local`

Đọc toàn bộ tài liệu đã được tải về máy cục bộ (trong thư mục `backend/data/raw/`) và nạp vào CSDL Vector ChromaDB.

### Yêu cầu mẫu (Request Body):
```json
{
  "rebuild": true
}
```
*   `rebuild`: Nếu đặt là `true`, hệ thống sẽ xóa toàn bộ dữ liệu cũ trong ChromaDB trước khi nạp lại. Nếu đặt là `false`, hệ thống chỉ nạp thêm các phần dữ liệu mới chưa tồn tại (Incremental).

### Phản hồi mẫu (Response):
```json
{
  "added": 235,
  "skipped": 0,
  "failed": 0,
  "message": "Nạp dữ liệu cục bộ thành công: Thêm 235 đoạn văn mới."
}
```
