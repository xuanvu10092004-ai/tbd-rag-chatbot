# TRƯỜNG ĐẠI HỌC THÁI BÌNH DƯƠNG
## KHOA CÔNG NGHỆ THÔNG TIN VÀ BÁN DẪN

---

# BÁO CÁO DỰ ÁN CUỐI KỲ

## ĐỀ TÀI: XÂY DỰNG TRỢ LÝ TUYỂN SINH THÔNG MINH
### TBD RAG CHATBOT — Ứng dụng kiến trúc RAG, ChromaDB và Gemini API

---

## THÔNG TIN THỰC HIỆN

| Mục | Nội dung |
|---|---|
| **Sinh viên thực hiện** | Nguyễn Xuân Vũ |
| **Mã số sinh viên (MSSV)** | 230440 |
| **Giảng viên hướng dẫn** | TS. Nguyễn Trùng Lập |
| **Lớp học phần** | Dự án Công nghệ Thông tin |
| **Thời gian hoàn thành** | Tháng 06/2026 |

---

## MỤC LỤC

1. [Chương 1 — Đặt vấn đề và Mục tiêu](#chương-1--đặt-vấn-đề-và-mục-tiêu)
2. [Chương 2 — Kiến trúc Hệ thống](#chương-2--kiến-trúc-hệ-thống)
3. [Chương 3 — Các Giải pháp Kỹ thuật](#chương-3--các-giải-pháp-kỹ-thuật)
4. [Chương 4 — Kết quả và Thử nghiệm](#chương-4--kết-quả-và-thử-nghiệm)
5. [Chương 5 — Kết luận và Hướng phát triển](#chương-5--kết-luận-và-hướng-phát-triển)

---

## Chương 1 — Đặt vấn đề và Mục tiêu

### 1.1. Sự cần thiết

Công tác tư vấn tuyển sinh tại các trường đại học đòi hỏi xử lý lượng thông tin lớn và đa dạng — từ học phí, ngành đào tạo, học bổng đến quy trình đăng ký. Việc phản hồi thủ công qua fanpage hay hotline thường xuyên gặp tình trạng quá tải, phản hồi chậm trễ, đặc biệt ngoài giờ hành chính.

### 1.2. Hạn chế của các giải pháp hiện tại

**Chatbot theo kịch bản (Rule-based):**
- Cứng nhắc, không hiểu các cách diễn đạt tự nhiên của học sinh.
- Phải cập nhật thủ công mỗi khi thông tin thay đổi.

**Mô hình ngôn ngữ lớn thuần túy (LLM):**
- Dễ xảy ra **ảo tưởng (Hallucination)** — sinh ra thông tin sai về học phí, số điện thoại, ngành học.
- Không có cơ chế kiểm soát nguồn thông tin tin cậy.

### 1.3. Giải pháp đề xuất — TBD RAG Chatbot

Dự án xây dựng hệ thống **TBD RAG Chatbot** theo kiến trúc **Retrieval-Augmented Generation (RAG)**:

- Chỉ truy xuất thông tin từ **kho tri thức chính thức** đã được kiểm duyệt của TBD.
- Dùng mô hình **Gemini** để tổng hợp câu trả lời tự nhiên, dễ hiểu.
- **Cam kết không tự chế thông tin** nằm ngoài ngữ cảnh được cung cấp.

---

## Chương 2 — Kiến trúc Hệ thống

### 2.1. Sơ đồ tổng quan

```
Người dùng
    │  (gõ câu hỏi)
    ▼
Frontend — React + TypeScript + Vite
    │  (HTTP POST /api/chat)
    ▼
Backend — Python FastAPI
    │
    ├─► Kiểm tra khớp nhanh FAQ?
    │       └─► CÓ: Trả về ngay (~50ms, không gọi LLM)
    │
    ├─► Viết lại câu hỏi kèm lịch sử hội thoại (Gemini, temp=0)
    │
    ├─► Nhúng câu hỏi thành vector (gemini-embedding-001)
    │
    ├─► Tìm kiếm 12 chunks gần nhất trong ChromaDB
    │
    ├─► Lọc theo ngưỡng khoảng cách cosine
    │
    └─► Tổng hợp câu trả lời (Gemini 2.5 Flash)
            │
            ▼
        Phản hồi kèm nguồn trích dẫn → Người dùng
```

### 2.2. Các công nghệ sử dụng

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite | Giao diện người dùng |
| **Backend** | Python 3.10, FastAPI | API server, điều phối RAG |
| **Vector DB** | ChromaDB (PersistentClient) | Lưu trữ và tìm kiếm vector |
| **AI Embedding** | `gemini-embedding-001` | Chuyển văn bản → vector 768 chiều |
| **AI Model** | Gemini 2.5 Flash | Tổng hợp câu trả lời |
| **Giao diện** | Light Theme, CSS thuần | UI chuyên nghiệp, màu TBD xanh navy |

---

## Chương 3 — Các Giải pháp Kỹ thuật

Trong quá trình phát triển, dự án triển khai 4 kỹ thuật tối ưu hóa cốt lõi:

### 3.1. Khớp nhanh FAQ (Direct FAQ Matching)

Đối với câu hỏi thường gặp có tính lặp cao (địa chỉ, học phí, danh sách ngành...):

- Mở rộng tìm kiếm lên **12 kết quả gần nhất** thay vì 4.
- Khi khoảng cách cosine ≤ **0.25** và khớp từ khóa cốt lõi → trả về câu trả lời chuẩn ngay lập tức.

**Kết quả:** Phản hồi trong **~30–100ms**, tiêu tốn **0% quota Gemini API**.

### 3.2. Chia tài liệu thông minh (Smart Chunking)

- Dùng `RecursiveCharacterTextSplitter` (800 ký tự) cho văn bản trang web thông thường.
- Các file FAQ chuẩn hóa (`curated_faq.json`) **không bị chia nhỏ** — giữ nguyên toàn bộ cặp hỏi-đáp liên kết.

**Kết quả:** Không mất thông tin, danh sách ngành học và học phí luôn đầy đủ.

### 3.3. Viết lại truy vấn hội thoại (Query Rewriting)

Gửi lịch sử 10 tin nhắn gần nhất + câu hỏi hiện tại qua Gemini (temperature = 0) để tạo ra câu hỏi độc lập, rõ nghĩa trước khi tìm kiếm.

**Ví dụ:**
- Người dùng: *"Học phí ngành đó thế nào?"* (sau câu hỏi về CNTT)
- Hệ thống tự chuyển thành: *"Học phí ngành Công nghệ thông tin của TBD thế nào?"*

### 3.4. Chống trùng lặp bằng Hash SHA-256

Mỗi chunk tài liệu được băm SHA-256 trước khi nạp vào ChromaDB. Nếu nội dung đã tồn tại → bỏ qua, không nạp lại. Đảm bảo kho dữ liệu luôn sạch và không trùng.

---

## Chương 4 — Kết quả và Thử nghiệm

### 4.1. Dữ liệu tuyển sinh đã nạp

- **10 trang web tuyển sinh** chính thức của TBD đã được crawl và xử lý.
- **3 bộ FAQ chuẩn hóa** bao gồm: câu hỏi thường gặp, thông tin liên hệ, thông tin bổ sung.
- Tổng cộng **hơn 235 chunks** lưu trữ không trùng lặp trong ChromaDB.
- **26 ngành học** thuộc 5 khối ngành đã được tích hợp đầy đủ.

### 4.2. Kết quả kiểm thử

| Loại câu hỏi | Ví dụ | Kết quả | Ghi chú |
|---|---|---|---|
| **FAQ trực tiếp** | *"Trường có ngành nào?"* | `faq_direct_match` | ~50ms, không gọi LLM |
| **RAG thông thường** | *"Học bổng điều kiện gì?"* | `rag_generated` | Chính xác, có nguồn trích dẫn |
| **Ngoài phạm vi** | *"Cách nấu phở?"* | `fallback` | Từ chối lịch sự, không ảo tưởng |
| **Câu hỏi tiếp nối** | *"Ngành đó học phí bao nhiêu?"* | `rag_generated` | Query rewriting hoạt động đúng |

### 4.3. Giao diện hoàn thiện

- **Trang Chat:** Light theme chuyên nghiệp màu TBD xanh navy, hiển thị nguồn trích dẫn, gợi ý câu hỏi.
- **Trang Quản trị:** Upload tài liệu drag-and-drop, xem trạng thái kết nối ChromaDB.
- **Khởi động 1-click:** `start.bat` tự động cài đặt toàn bộ và mở trình duyệt.

---

## Chương 5 — Kết luận và Hướng phát triển

### 5.1. Kết luận

Dự án **TBD RAG Chatbot** đã hoàn thành đầy đủ các mục tiêu đặt ra:

- ✅ Xây dựng chatbot tuyển sinh phản hồi **chính xác, nhanh, an toàn** — không ảo tưởng.
- ✅ Giao diện **trực quan, chuyên nghiệp** phù hợp nhận diện thương hiệu TBD.
- ✅ Hệ thống **dễ vận hành** — khởi động 1-click, quản trị qua giao diện web.
- ✅ **Mở rộng được** — admin có thể tự thêm tài liệu mới mà không cần lập trình.

### 5.2. Hướng phát triển tương lai

| Hướng | Mô tả |
|---|---|
| **Hỗ trợ đa phương thức** | Nhận câu hỏi qua giọng nói, phản hồi bằng giọng đọc tự nhiên |
| **Kết nối cơ sở dữ liệu động** | Tra cứu trạng thái hồ sơ tuyển sinh theo thời gian thực |
| **Triển khai đám mây** | Đóng gói Docker, deploy lên AWS/Google Cloud để phục vụ nhiều người dùng |
| **Phân tích thống kê** | Dashboard thống kê câu hỏi phổ biến, hỗ trợ cải thiện nội dung tuyển sinh |

---

*Báo cáo hoàn thành tháng 06/2026 — Trường Đại học Thái Bình Dương*
