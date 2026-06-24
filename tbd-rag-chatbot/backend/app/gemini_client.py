# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════╗
# ║  FILE: gemini_client.py                                      ║
# ║  CÔNG DỤNG: Giao tiếp với Google Gemini API                  ║
# ║  - Tạo vector embedding cho tài liệu và câu hỏi             ║
# ║  - Sinh câu trả lời dựa trên ngữ cảnh đã truy xuất          ║
# ║  ĐƯỢC GỌI BỞI: vector_store.py, rag_pipeline.py             ║
# ╚══════════════════════════════════════════════════════════════╝
"""
Module giao tiếp với Google Gemini API.
Cung cấp 3 chức năng chính theo đúng yêu cầu đề bài:
  - embed_document : nhúng văn bản tài liệu vào vector (khi nạp dữ liệu)
  - embed_query    : nhúng câu hỏi người dùng vào vector (khi tìm kiếm)
  - generate_answer: sinh câu trả lời từ ngữ cảnh đã truy xuất
"""

import logging
import time
from typing import Optional

# Import thư viện google-genai theo chuẩn SDK mới nhất của Google
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

# =====================================================================
# KHỞI TẠO GEMINI CLIENT (Singleton - chỉ tạo 1 lần duy nhất)
# =====================================================================

# Biến lưu client toàn cục, tránh tạo lại nhiều lần gây lãng phí kết nối
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Trả về Gemini client đã khởi tạo (pattern singleton)."""
    global _client
    if _client is None:
        # Khởi tạo client với API Key lấy từ file .env
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Đã khởi tạo Gemini client thành công")
    return _client


# =====================================================================
# SYSTEM PROMPT - Giới hạn phạm vi trả lời của AI
# =====================================================================

# System instruction định nghĩa tính cách và quy tắc trả lời của chatbot
# Theo đề bài: AI chỉ được trả lời dựa trên ngữ cảnh, không tự bịa đặt
SYSTEM_PROMPT = (
    "Bạn là Trợ lý ảo tuyển sinh của Trường Đại học Thái Bình Dương (TBD).\n"
    "Hãy trả lời câu hỏi của người dùng một cách thân thiện, chính xác "
    "DỰA TRÊN NGỮ CẢNH được cung cấp bên dưới.\n"
    "QUY TẮC BẮT BUỘC:\n"
    "1. Chỉ trả lời dựa vào phần 'Ngữ cảnh tài liệu' được cung cấp.\n"
    "2. Nếu thông tin không có trong ngữ cảnh, hãy nói: 'Dạ, thông tin này "
    "hiện chưa có trong tài liệu chính thức của trường. Bạn vui lòng liên hệ "
    "Hotline tuyển sinh để được tư vấn kỹ hơn ạ'. Tuyệt đối không tự bịa thông tin.\n"
    "3. Giọng điệu luôn lễ phép, thân thiện, xưng 'Dạ', 'TBD xin chia sẻ'..."
)


# =====================================================================
# BƯỚC 3 (Đề bài): TẠO VECTOR EMBEDDING BẰNG GEMINI API
# =====================================================================

def embed_document(text: str, max_retries: int = 3) -> list[float]:
    """
    Nhúng văn bản TÀI LIỆU vào không gian vector.

    Dùng task_type=RETRIEVAL_DOCUMENT: tối ưu cho văn bản dài, nội dung phong phú.
    Được gọi khi NẠP DỮ LIỆU vào ChromaDB (Bước 4 đề bài).

    Args:
        text: Nội dung đoạn văn bản cần nhúng
        max_retries: Số lần thử lại khi gặp lỗi rate limit

    Returns:
        Danh sách số float biểu diễn vector embedding (thường 3072 chiều)
    """
    for attempt in range(max_retries):
        try:
            client = get_client()
            # Gọi Gemini API để tạo embedding cho tài liệu
            result = client.models.embed_content(
                model=settings.GEMINI_EMBED_MODEL,  # gemini-embedding-001
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",  # Tối ưu cho lưu trữ tài liệu
                ),
            )
            # Lấy danh sách giá trị float từ kết quả trả về
            return result.embeddings[0].values

        except Exception as e:
            if attempt < max_retries - 1:
                # Chờ theo cấp số nhân: 1s, 2s, 4s... để tránh rate limit
                wait = 2 ** attempt
                logger.warning(
                    "embed_document thất bại (lần %d/%d), thử lại sau %ds: %s",
                    attempt + 1, max_retries, wait, str(e)
                )
                time.sleep(wait)
            else:
                logger.error("embed_document thất bại sau %d lần thử: %s", max_retries, str(e))
                raise


def embed_documents(texts: list[str], max_retries: int = 5) -> list[list[float]]:
    """
    Nhúng một DANH SÁCH văn bản cùng lúc (batch embedding).

    Gọi embed_content với nhiều text trong 1 request để tiết kiệm thời gian
    khi nạp số lượng lớn chunk vào ChromaDB.

    Args:
        texts: Danh sách các đoạn văn bản cần nhúng
        max_retries: Số lần thử lại khi gặp lỗi

    Returns:
        Danh sách vector embedding tương ứng với từng đoạn văn bản
    """
    if not texts:
        return []

    for attempt in range(max_retries):
        try:
            client = get_client()
            # Gọi API một lần cho cả batch, tiết kiệm hơn gọi từng cái
            result = client.models.embed_content(
                model=settings.GEMINI_EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                ),
            )
            # Trả về danh sách vector, mỗi phần tử ứng với 1 đoạn văn bản
            return [emb.values for emb in result.embeddings]

        except Exception as e:
            if attempt < max_retries - 1:
                # Khi gặp rate limit (lỗi 429), chờ lâu hơn
                wait = 5 * (attempt + 1)
                logger.warning(
                    "embed_documents thất bại (lần %d/%d), thử lại sau %ds: %s",
                    attempt + 1, max_retries, wait, str(e)[:120]
                )
                time.sleep(wait)
            else:
                logger.error("embed_documents thất bại sau %d lần thử: %s", max_retries, str(e)[:200])
                raise


def embed_query(text: str, max_retries: int = 3) -> list[float]:
    """
    Nhúng CÂU HỎI người dùng vào không gian vector.

    Dùng task_type=RETRIEVAL_QUERY: tối ưu cho câu hỏi ngắn dùng để tìm kiếm.
    Được gọi khi người dùng đặt câu hỏi (Bước 5 đề bài).

    LÝ DO TÁCH RIÊNG embed_query và embed_document:
    - RETRIEVAL_DOCUMENT: biểu diễn nội dung phong phú, đa chiều
    - RETRIEVAL_QUERY: biểu diễn câu hỏi ngắn để khớp với tài liệu
    - Dùng đúng task_type giúp tăng độ chính xác retrieval đáng kể

    Args:
        text: Câu hỏi của người dùng cần nhúng
        max_retries: Số lần thử lại khi gặp lỗi

    Returns:
        Danh sách số float biểu diễn vector embedding của câu hỏi
    """
    for attempt in range(max_retries):
        try:
            client = get_client()
            # Gọi Gemini API để tạo embedding cho câu hỏi
            result = client.models.embed_content(
                model=settings.GEMINI_EMBED_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",  # Tối ưu cho tìm kiếm
                ),
            )
            return result.embeddings[0].values

        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    "embed_query thất bại (lần %d/%d), thử lại sau %ds: %s",
                    attempt + 1, max_retries, wait, str(e)
                )
                time.sleep(wait)
            else:
                logger.error("embed_query thất bại sau %d lần thử: %s", max_retries, str(e))
                raise


# =====================================================================
# BƯỚC 6 (Đề bài): SINH CÂU TRẢ LỜI VỚI GEMINI (Augmentation & Generation)
# =====================================================================

def generate_answer(
    context_chunks: list[str],
    question: str,
    conversation_history: list[dict],
    max_retries: int = 3,
) -> str:
    """
    Sinh câu trả lời chính thức dựa trên ngữ cảnh đã truy xuất và lịch sử hội thoại.

    Đây là bước cuối cùng của RAG pipeline theo đề bài:
    - Kết hợp ngữ cảnh (context) + câu hỏi + lịch sử hội thoại thành 1 Prompt
    - Gửi Prompt cho gemini-2.5-flash để sinh câu trả lời tự nhiên, chính xác
    - temperature=0.2 để AI bám sát dữ liệu thực tế, ít sáng tạo lung tung

    Args:
        context_chunks: Danh sách đoạn văn bản liên quan đã truy xuất từ ChromaDB
        question: Câu hỏi gốc của người dùng
        conversation_history: Lịch sử hội thoại [{role, content}]
        max_retries: Số lần thử lại khi gặp lỗi API

    Returns:
        Câu trả lời bằng tiếng Việt
    """
    # Ghép các đoạn ngữ cảnh lại thành một khối văn bản duy nhất
    combined_context = "\n\n---\n\n".join(context_chunks)

    # Định dạng lịch sử hội thoại để đưa vào prompt
    # Giúp Gemini hiểu được câu hỏi nối tiếp (ví dụ: "ngành này" đề cập đến gì)
    history_text = ""
    if conversation_history:
        # Chỉ lấy 6 tin nhắn gần nhất để tránh prompt quá dài
        recent = conversation_history[-6:]
        lines = []
        for msg in recent:
            role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            lines.append(f"{role_label}: {msg['content']}")
        history_text = "\n\nLịch sử hội thoại gần đây:\n" + "\n".join(lines)

    # Xây dựng Prompt hoàn chỉnh gửi cho Gemini
    # Cấu trúc: System + Ngữ cảnh + Lịch sử (nếu có) + Câu hỏi
    full_prompt = f"""
Ngữ cảnh thông tin về trường TBD:
{combined_context}
{history_text}

---
Câu hỏi của người học: {question}
Trả lời:"""

    for attempt in range(max_retries):
        try:
            client = get_client()
            # Gọi Gemini 2.5 Flash để sinh câu trả lời
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL_ID,  # gemini-2.5-flash
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,  # Giới hạn phạm vi AI
                    temperature=0.2,       # Thấp để bám sát dữ liệu, ít "sáng tạo"
                    max_output_tokens=1024, # Giới hạn độ dài câu trả lời
                ),
            )
            answer = response.text.strip()
            logger.info("Đã sinh câu trả lời thành công (độ dài: %d ký tự)", len(answer))
            return answer

        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 * (attempt + 1)  # 2s, 4s
                logger.warning(
                    "generate_answer thất bại (lần %d/%d), thử lại sau %ds: %s",
                    attempt + 1, max_retries, wait, str(e)[:120]
                )
                time.sleep(wait)
            else:
                logger.error("generate_answer thất bại sau %d lần thử: %s", max_retries, str(e)[:200])
                raise
