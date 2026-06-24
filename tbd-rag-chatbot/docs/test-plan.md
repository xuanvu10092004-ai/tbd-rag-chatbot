#  Kế Hoạch Kiểm Thử - TBD RAG Chatbot

##  Điều kiện tiên quyết trước khi kiểm thử

1.  Backend đang chạy thành công tại: [http://localhost:8001](http://localhost:8001)
2.  Dữ liệu đã được nạp đầy đủ (kiểm tra `GET /api/health` có `vector_db_count` khoảng 235).
3.  Frontend đang chạy tại: [http://localhost:5173](http://localhost:5173)

---

##  Các kịch bản kiểm thử (Test Cases)

### Kịch bản 1: Hỏi về học phí ngành cụ thể
*   **Câu hỏi:** *"Học phí ngành Công nghệ thông tin là bao nhiêu?"*
*   **Kết quả kỳ vọng:**
    *   Hệ thống khớp trực tiếp FAQ với `answer_type: "faq_direct_match"`.
    *   Câu trả lời có chứa thông tin chính xác: *"740.000 đồng mỗi tín chỉ."*
    *   Thời gian phản hồi siêu tốc (<100ms).

---

### Kịch bản 2: Hỏi danh sách các ngành học đầy đủ
*   **Câu hỏi:** *"Trường có những ngành nào?"* hoặc *"Đại học Thái Bình Dương đào tạo những ngành gì?"*
*   **Kết quả kỳ vọng:**
    *   Hệ thống khớp trực tiếp FAQ và trả về danh sách đầy đủ tất cả các ngành học (gồm 5 khối ngành/26 ngành học đã cập nhật).
    *   Nội dung phản hồi không bị cắt cụt do chia nhỏ văn bản.

---

### Kịch bản 3: Hỏi về chính sách học bổng
*   **Câu hỏi:** *"Trường có những loại học bổng tuyển sinh nào?"*
*   **Kết quả kỳ vọng:**
    *   `has_context: true`.
    *   Đọc và trích dẫn nguồn từ trang chính thức của trường về chính sách hỗ trợ tài chính và học bổng (ví dụ: học bổng 100%, 50%, học bổng doanh nghiệp...).

---

### Kịch bản 4: Hỏi ngoài ngữ cảnh (An toàn hệ thống)
*   **Câu hỏi:** *"Công thức nấu phở bò ngon là gì?"*
*   **Kết quả kỳ vọng:**
    *   `has_context: false`.
    *   Hệ thống chặn không gửi câu hỏi tới Gemini để tránh sinh câu trả lời bịa đặt.
    *   Trả về câu thông báo Fallback tĩnh được quy định sẵn: *"Dạ, thông tin này hiện chưa có trong tài liệu chính thức..."*

---

### Kịch bản 5: Câu hỏi nối tiếp sử dụng đại từ (Query Rewriting)
*   **Bước 1:** Hỏi *"Trường Đại học Thái Bình Dương có ngành Công nghệ bán dẫn không?"*
*   **Bước 2:** Hỏi tiếp *"Ngành đó học phí thế nào?"* (sử dụng cùng `conversation_id`).
*   **Kết quả kỳ vọng:**
    *   Trong log backend hiển thị câu hỏi đã được viết lại thành: *"Học phí ngành Công nghệ bán dẫn tại Trường Đại học Thái Bình Dương là bao nhiêu?"*
    *   Tìm kiếm chính xác và trả về thông tin học phí của ngành Công nghệ bán dẫn/CNTT.

---

### Kịch bản 6: Kiểm tra bảo mật tên miền khi nạp dữ liệu
*   **Câu lệnh kiểm tra (curl):**
    ```bash
    curl -X POST http://localhost:8001/api/ingest/urls \
      -H "Content-Type: application/json" \
      -d '{"urls": ["https://google.com/"]}'
    ```
*   **Kết quả kỳ vọng:**
    *   Hệ thống từ chối xử lý và trả về mã lỗi HTTP `422 Unprocessable Entity`.
    *   Thông báo lỗi: Chỉ chấp nhận các tên miền thuộc `https://tbd.edu.vn/`.

---

##  Kiểm thử trên giao diện người dùng (UI Testing)

1.  Truy cập giao diện [http://localhost:5173](http://localhost:5173) kiểm tra độ phản hồi và màu sắc nhận diện của trường (Xanh navy kết hợp đỏ đô).
2.  Bật **Chế độ Debug** ở góc dưới màn hình.
3.  Nhập câu hỏi và kiểm tra xem bảng đo lường hiệu năng có xuất hiện bên dưới bong bóng chat của chatbot không.
4.  Kiểm tra xem thanh hiển thị nguồn trích dẫn (Source Panel) ở cột bên phải có cập nhật chính xác đường dẫn khi chatbot trả lời không.
5.  Thử nghiệm thu nhỏ kích thước trình duyệt để kiểm tra tính tương thích (Responsive Design) trên thiết bị di động.
