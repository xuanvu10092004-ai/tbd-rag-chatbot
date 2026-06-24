# -*- coding: utf-8 -*-
"""
Module chia nhỏ văn bản thành các chunk (đoạn).

Theo lời khuyên 2 của đề bài: dùng RecursiveCharacterTextSplitter của LangChain
thay vì tự cắt chuỗi thô bạo theo ký tự.

Ưu điểm của RecursiveCharacterTextSplitter:
- Ưu tiên tách tại ranh giới ngữ nghĩa: đoạn văn → dòng → câu → từ
- Tránh bị cắt đôi chữ hoặc cắt giữa câu quan trọng
- Hỗ trợ tốt tiếng Việt (Unicode)
- Có phần gối đầu (overlap) giữa các chunk để không mất ngữ cảnh
"""

import hashlib
import logging
from datetime import datetime, timezone

# Thư viện chia nhỏ văn bản thông minh của LangChain
# pip install langchain-text-splitters
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.hasher import generate_chunk_id

logger = logging.getLogger(__name__)

# Thứ tự ưu tiên chia nhỏ văn bản:
# 1. Tách tại dòng trống (\n\n) → giữ nguyên đoạn văn
# 2. Tách tại xuống dòng (\n)   → giữ nguyên dòng
# 3. Tách tại dấu chấm (.)      → giữ nguyên câu
# 4. Tách tại khoảng trắng ( )  → giữ nguyên từ
# 5. Tách ký tự (dự phòng)      → trường hợp cuối cùng
SEPARATORS = ["\n\n", "\n", ".", " ", ""]


# =====================================================================
# BƯỚC 2 (Đề bài): ĐỌC VÀ XỬ LÝ TÀI LIỆU - Chia nhỏ thành chunks
# =====================================================================

def _create_splitter() -> RecursiveCharacterTextSplitter:
    """
    Tạo bộ chia văn bản với cấu hình từ file .env.

    CHUNK_SIZE    : độ dài tối đa mỗi chunk (mặc định 800 ký tự)
    CHUNK_OVERLAP : số ký tự gối đầu giữa 2 chunk liền kề (mặc định 150 ký tự)
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,       # Kích thước mỗi đoạn
        chunk_overlap=settings.CHUNK_OVERLAP, # Phần gối đầu để giữ ngữ cảnh
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def split_into_chunks(document: dict) -> list[dict]:
    """
    Tách một tài liệu thành danh sách các chunk nhỏ, mỗi chunk có đủ metadata.

    Theo đề bài (Bước 2 nâng cao): thay vì cắt chuỗi thô bạo, dùng
    RecursiveCharacterTextSplitter để giữ nguyên ý nghĩa câu/đoạn.

    Args:
        document: Dict chứa:
            - content (str)     : nội dung văn bản
            - source (str)      : URL hoặc đường dẫn file nguồn
            - source_type (str) : loại nguồn ("url" hoặc "file")
            - title (str)       : tiêu đề tài liệu

    Returns:
        Danh sách chunk dict, mỗi chunk chứa: content, metadata đầy đủ
    """
    content = document.get("content", "").strip()
    source = document.get("source", "")
    raw_source_type = document.get("source_type", "file")
    title = document.get("title", source)

    # Chuẩn hóa loại nguồn sang schema thống nhất
    if raw_source_type == "url":
        source_type = "official_website"
    elif raw_source_type == "file":
        source_type = "uploaded_file"
    else:
        source_type = raw_source_type

    # Bỏ qua tài liệu rỗng
    if not content:
        logger.warning("Tài liệu rỗng, bỏ qua: %s", source)
        return []

    # Tiến hành chia nhỏ văn bản bằng RecursiveCharacterTextSplitter
    if source_type == "curated_faq":
        text_chunks = [content]
    else:
        splitter = _create_splitter()
        try:
            text_chunks = splitter.split_text(content)
        except Exception as e:
            logger.error("Lỗi khi tách văn bản '%s': %s", source, str(e))
            return []

    if not text_chunks:
        logger.warning("Không có chunk nào được tạo từ: %s", source)
        return []

    # Thời điểm nạp dữ liệu (dùng chung cho tất cả chunk trong cùng tài liệu)
    ingested_at = document.get("ingested_at") or datetime.now(timezone.utc).isoformat()
    local_path = document.get("local_path", "")
    original_url = document.get("original_url") or ""

    # Xác định URL gốc cho loại tài liệu từ website chính thức
    if not original_url and source_type == "official_website":
        original_url = source

    # Xác định độ ưu tiên nguồn: website chính thức > file tải lên > khác
    if source_type == "official_website":
        source_priority = 1
    elif source_type == "uploaded_file":
        source_priority = 2
    else:
        source_priority = 3

    # Tạo danh sách chunk kèm đầy đủ metadata
    chunks = []
    for idx, chunk_text in enumerate(text_chunks):
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue  # Bỏ qua chunk rỗng sau khi trim

        # Tạo ID duy nhất và ổn định cho chunk (dựa trên source + index + nội dung)
        chunk_id = generate_chunk_id(source=source, chunk_index=idx, content=chunk_text)

        # Trích xuất tiêu đề mục nếu chunk bắt đầu bằng dấu '#' (markdown heading)
        section = ""
        for line in chunk_text.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                section = line.lstrip("#").strip()
                break

        # Hash nội dung chunk để phát hiện thay đổi khi cập nhật dữ liệu
        content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()

        chunk = {
            "content": chunk_text,
            "source": source,
            "source_type": source_type,
            "title": title,
            "section": document.get("section") or section,
            "chunk_id": chunk_id,
            "ingested_at": ingested_at,
            "source_priority": source_priority,
            "content_hash": content_hash,
            "local_path": local_path,
            "original_url": original_url,
        }
        chunks.append(chunk)

    logger.info(
        "Đã chia '%s' thành %d chunk (CHUNK_SIZE=%d, OVERLAP=%d)",
        source[:60],
        len(chunks),
        settings.CHUNK_SIZE,
        settings.CHUNK_OVERLAP,
    )
    return chunks


def split_documents(documents: list[dict]) -> list[dict]:
    """
    Chia nhiều tài liệu cùng lúc thành danh sách chunk.

    Tiện ích xử lý hàng loạt: lặp qua từng tài liệu và gọi split_into_chunks().

    Args:
        documents: Danh sách tài liệu đã tải từ document_loader

    Returns:
        Danh sách tất cả chunk từ tất cả tài liệu
    """
    all_chunks: list[dict] = []
    for doc in documents:
        chunks = split_into_chunks(doc)
        all_chunks.extend(chunks)

    logger.info("Tổng số chunk từ %d tài liệu: %d", len(documents), len(all_chunks))
    return all_chunks
