# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════╗
# ║  FILE: rag_pipeline.py                                       ║
# ║  CÔNG DỤNG: Luồng xử lý RAG chính (QUAN TRỌNG NHẤT)         ║
# ║  - Điều phối toàn bộ 6 bước theo đề bài                     ║
# ║  - Nhận câu hỏi → Tìm ngữ cảnh → Gọi Gemini → Trả lời      ║
# ║  ĐƯỢC GỌI BỞI: routes/chat.py                               ║
# ╚══════════════════════════════════════════════════════════════╝
"""
RAG Pipeline chính của TBD Chatbot.

Triển khai đúng theo 6 bước trong đề bài, có bổ sung thêm:
- Quản lý lịch sử hội thoại (Lời khuyên 1 đề bài)
- Lưu trữ DB lâu dài bằng PersistentClient (Lời khuyên 3 đề bài)
- Chia văn bản thông minh bằng RecursiveCharacterTextSplitter (Lời khuyên 2)

Luồng xử lý mỗi câu hỏi:
  Bước 1: Lấy lịch sử hội thoại của người dùng
  Bước 2: Truy xuất ngữ cảnh liên quan từ ChromaDB
  Bước 3: Gọi Gemini sinh câu trả lời dựa trên ngữ cảnh
  Bước 4: Lưu lịch sử hội thoại và trả về kết quả
"""

import logging
import time
from typing import Optional

from app.config import settings
from app.conversation_store import conversation_store
from app.gemini_client import generate_answer
from app.vector_store import query_similar, get_collection

logger = logging.getLogger(__name__)

# =====================================================================
# CÁC THÔNG BÁO MẶC ĐỊNH KHI KHÔNG TÌM THẤY THÔNG TIN
# =====================================================================

# Tin nhắn trả về khi không tìm thấy ngữ cảnh phù hợp trong database
FALLBACK_MESSAGE = (
    "Dạ, thông tin này hiện chưa có trong tài liệu chính thức của trường. "
    "Bạn vui lòng để lại số điện thoại hoặc liên hệ Hotline tuyển sinh "
    "để được thầy cô tư vấn kỹ hơn ạ."
)

# Tin nhắn trả về khi hệ thống xử lý quá chậm
TIMEOUT_MESSAGE = (
    "Xin lỗi, hệ thống đang xử lý chậm. Bạn vui lòng thử lại sau ạ."
)


# =====================================================================
# HÀM HỖ TRỢ: LỌC VÀ XÂY DỰNG DANH SÁCH NGUỒN
# =====================================================================

def _filter_relevant_chunks(chunks: list[dict]) -> list[dict]:
    """
    Lọc các chunk có độ liên quan đủ tốt (distance đủ nhỏ).

    ChromaDB trả về distance theo cosine: giá trị càng nhỏ = càng liên quan.
    Chỉ giữ lại các chunk có distance ≤ ngưỡng RELEVANCE_DISTANCE_THRESHOLD.

    Args:
        chunks: Danh sách chunk trả về từ ChromaDB

    Returns:
        Danh sách chunk đủ liên quan
    """
    threshold = settings.RELEVANCE_DISTANCE_THRESHOLD
    relevant = [c for c in chunks if c.get("distance", 1.0) <= threshold]

    # Cảnh báo nếu tất cả chunk đều vượt ngưỡng (câu hỏi quá khác biệt với tài liệu)
    if chunks and not relevant:
        min_dist = min(c.get("distance", 1.0) for c in chunks)
        logger.warning(
            "Tất cả %d chunk vượt ngưỡng RELEVANCE_DISTANCE_THRESHOLD (%.2f). "
            "Khoảng cách nhỏ nhất: %.4f",
            len(chunks), threshold, min_dist
        )
    return relevant


def _build_source_list(chunks: list[dict]) -> list[dict]:
    """
    Chuyển đổi danh sách chunk thành danh sách nguồn trích dẫn cho response.

    Loại bỏ các nguồn trùng lặp (cùng URL và nội dung đầu).

    Args:
        chunks: Danh sách chunk đã lọc

    Returns:
        Danh sách nguồn trích dẫn theo đúng API schema
    """
    sources = []
    seen = set()  # Tập hợp để theo dõi và loại trùng

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        source_url = meta.get("source", "")
        snippet = chunk.get("content", "")[:200]  # Trích 200 ký tự đầu làm preview

        # Khóa dedup: kết hợp URL + 30 ký tự đầu nội dung
        dedup_key = f"{source_url}|{snippet[:30]}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        sources.append({
            "title": meta.get("title", source_url),
            "source": source_url,
            "source_type": meta.get("source_type", "official_website"),
            "snippet": snippet,
            "distance": chunk.get("distance", 0.0),
            "original_url": meta.get("original_url") or (
                source_url if meta.get("source_type") == "official_website" else None
            ),
            "local_path": meta.get("local_path") or None
        })
    return sources


# =====================================================================
# HÀM CHÀO HỎI: Phát hiện lời chào và trả về tĩnh (không gọi Gemini)
# =====================================================================

def _is_greeting(question: str) -> bool:
    """
    Kiểm tra xem câu hỏi có phải là lời chào đơn giản không.

    Nếu là lời chào → trả về câu chào tĩnh mà không cần gọi Gemini API,
    giúp tiết kiệm thời gian và chi phí API.

    Args:
        question: Câu hỏi của người dùng

    Returns:
        True nếu là lời chào, False nếu không
    """
    q_norm = question.lower().strip()
    greetings = {
        "xin chào", "chào", "hello", "hi", "chào bạn",
        "xin chao", "chao", "chao ban", "hey"
    }
    return q_norm in greetings


def _find_exact_faq_match(question: str, chunks: list[dict]) -> Optional[str]:
    """
    Nếu có chunk là curated_faq hoặc chứa định dạng câu hỏi thường gặp có độ tương đồng cực kỳ cao (distance <= 0.22)
    và khớp từ khóa tốt, trích xuất câu trả lời trực tiếp từ FAQ đó mà không cần gọi Gemini.
    """
    if not chunks:
        return None

    stop_words = {"và", "là", "ai", "gì", "của", "tại", "ở", "có", "không", "như", "thế", "nào", "được", "cho", "để", "những", "các"}
    q_words = {w for w in question.lower().split() if w not in stop_words and len(w) > 1}
    if not q_words:
        q_words = set(question.lower().split())

    # Các từ chung chung về tên trường
    generic_words = {"trường", "đại", "học", "thái", "bình", "dương", "tbd"}
    core_q_words = q_words - generic_words

    best_chunk = None
    best_score = -1.0

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        # Chỉ tự động bypass đối với nguồn FAQ (curated_faq)
        if meta.get("source_type") != "curated_faq":
            continue

        dist = chunk.get("distance", 1.0)
        # Chỉ xét các chunk cực kỳ gần (distance <= 0.25)
        if dist > 0.25:
            continue

        content = chunk.get("content", "")
        
        # Trích xuất phần câu hỏi thường gặp
        faq_question = ""
        if "Câu hỏi thường gặp:" in content:
            parts = content.split("Câu hỏi thường gặp:", 1)[1]
            if "Trả lời:" in parts:
                faq_question = parts.split("Trả lời:", 1)[0].strip()
        
        if not faq_question:
            faq_question = content

        faq_words = {w for w in faq_question.lower().split() if w not in stop_words and len(w) > 1}
        core_faq_words = faq_words - generic_words

        # Yêu cầu phải trùng ít nhất 1 từ cốt lõi ngoài tên trường
        core_intersection = core_q_words.intersection(core_faq_words)
        if not core_intersection and (core_q_words or core_faq_words):
            continue

        # Đếm số từ trùng khớp trên toàn bộ chunk
        content_lower = content.lower()
        match_count = sum(1 for w in q_words if w in content_lower)

        # Trọng số: số từ trùng khớp và khoảng cách cosine
        score = match_count * 2.0 + (1.0 - dist)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_chunk:
        content = best_chunk.get("content", "")
        if "Trả lời:" in content:
            parts = content.split("Trả lời:", 1)
            return parts[1].strip()
        return content
    return None


def _get_best_local_fallback(question: str, chunks: list[dict]) -> Optional[str]:
    """
    Trong trường hợp Gemini gặp sự cố (503, 429, timeout), cố gắng tìm câu trả lời tốt nhất
    từ các chunk hiện có (distance <= 0.45) bằng cách tính kết hợp từ khóa trùng khớp và distance.
    """
    if not chunks:
        return None

    stop_words = {"và", "là", "ai", "gì", "của", "tại", "ở", "có", "không", "như", "thế", "nào", "được", "cho", "để", "những", "các"}
    q_words = {w for w in question.lower().split() if w not in stop_words and len(w) > 1}
    if not q_words:
        q_words = set(question.lower().split())

    generic_words = {"trường", "đại", "học", "thái", "bình", "dương", "tbd"}
    core_q_words = q_words - generic_words

    best_chunk = None
    best_score = -1.0

    for chunk in chunks:
        dist = chunk.get("distance", 1.0)
        # Chỉ xét các chunk có độ tương đồng tương đối tốt (distance <= 0.45)
        if dist > 0.45:
            continue

        content = chunk.get("content", "")
        meta = chunk.get("metadata", {})

        # Nếu là FAQ, ta kiểm tra độ trùng khớp câu hỏi
        if meta.get("source_type") == "curated_faq" or "Câu hỏi thường gặp:" in content:
            faq_question = ""
            if "Câu hỏi thường gặp:" in content:
                parts = content.split("Câu hỏi thường gặp:", 1)[1]
                if "Trả lời:" in parts:
                    faq_question = parts.split("Trả lời:", 1)[0].strip()
            
            if faq_question:
                faq_words = {w for w in faq_question.lower().split() if w not in stop_words and len(w) > 1}
                core_faq_words = faq_words - generic_words
                core_intersection = core_q_words.intersection(core_faq_words)
                # Nếu không khớp từ khóa cốt lõi nào trong câu hỏi FAQ, bỏ qua
                if not core_intersection and (core_q_words or core_faq_words):
                    continue

        content_lower = content.lower()
        match_count = sum(1 for w in q_words if w in content_lower)

        score = match_count * 2.0 + (1.0 - dist)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_chunk:
        content = best_chunk.get("content", "")
        if "Trả lời:" in content:
            parts = content.split("Trả lời:", 1)
            return parts[1].strip()
        return content
    return None


# =====================================================================================
# LUỒNG RAG CHÍNH (Async) - Theo đúng 6 bước đề bài
# =====================================================================

async def run(question: str, conversation_id: Optional[str] = None) -> dict:
    """
    Chạy toàn bộ luồng RAG: Retrieval → Augmentation → Generation.

    Bám sát cấu trúc đề bài (Bước 1 → Bước 6), có thêm:
    - Quản lý conversation_id để lưu lịch sử hội thoại
    - Lọc chunk theo ngưỡng relevance để tránh trả lời sai

    Args:
        question: Câu hỏi của người dùng
        conversation_id: ID phiên hội thoại (None = tạo mới)

    Returns:
        Dict chứa: answer, sources, has_context, retrieved_count,
                   conversation_id, answer_type, performance
    """
    # Bắt đầu tính thời gian xử lý
    start_time = time.perf_counter()

    # Tạo conversation_id mới nếu chưa có (phiên hội thoại mới)
    if not conversation_id or not conversation_store.exists(conversation_id):
        conversation_id = conversation_store.create_conversation()

    # Lấy lịch sử hội thoại của phiên này để truyền cho Gemini
    history = conversation_store.get_history(conversation_id)

    # ─────────────────────────────────────────────────────────────────
    # FAST PATH: Xử lý lời chào - không cần gọi Gemini API
    # ─────────────────────────────────────────────────────────────────
    if _is_greeting(question):
        greeting_response = (
            "Xin chào! Mình là chatbot hỗ trợ tuyển sinh của Trường Đại học Thái Bình Dương (TBD). "
            "Bạn có thể hỏi mình về ngành học, học phí, học bổng, "
            "phương thức xét tuyển hoặc thông tin liên hệ tuyển sinh nhé! 😊"
        )
        # Lưu lịch sử hội thoại
        conversation_store.add_message(conversation_id, "user", question)
        conversation_store.add_message(conversation_id, "assistant", greeting_response)

        total_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info("Lời chào → trả lời tĩnh | total_ms: %d", total_ms)

        return {
            "answer": greeting_response,
            "sources": [],
            "has_context": False,
            "retrieved_count": 0,
            "conversation_id": conversation_id,
            "answer_type": "greeting",
            "performance": {"total_ms": total_ms, "gemini_called": False},
        }

    # ─────────────────────────────────────────────────────────────────
    # BƯỚC 5 ĐỀ BÀI: TRUY XUẤT THÔNG TIN LIÊN QUAN (Retrieval)
    # Tìm các đoạn văn bản có ngữ nghĩa gần giống nhất với câu hỏi
    # ─────────────────────────────────────────────────────────────────
    retrieved_chunks = query_similar(
        question_text=question,
        n_results=12  # Lấy 12 kết quả để tăng khả năng khớp FAQ chính xác
    )

    # Check for direct high-confidence FAQ match first using all retrieved chunks
    direct_faq_answer = _find_exact_faq_match(question, retrieved_chunks)
    if direct_faq_answer:
        logger.info("Direct FAQ match found! Bypassing Gemini API.")
        answer = direct_faq_answer
        
        # Tìm chunk FAQ khớp để làm trích dẫn nguồn
        matched_chunk = None
        for c in retrieved_chunks:
            meta = c.get("metadata", {})
            if meta.get("source_type") == "curated_faq" and c.get("distance", 1.0) <= 0.25:
                content = c.get("content", "")
                if "Trả lời:" in content:
                    ans_part = content.split("Trả lời:", 1)[1].strip()
                    if ans_part == direct_faq_answer:
                        matched_chunk = c
                        break
        
        sources = _build_source_list([matched_chunk] if matched_chunk else retrieved_chunks[:1])
        conversation_store.add_message(conversation_id, "user", question)
        conversation_store.add_message(conversation_id, "assistant", answer)

        total_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "RAG hoàn thành | câu hỏi: '%s...' | chunks: %d → 1 | answer_type: faq_direct_match | total_ms: %d",
            question[:50],
            len(retrieved_chunks),
            total_ms,
        )
        return {
            "answer": answer,
            "sources": sources,
            "has_context": True,
            "retrieved_count": 1,
            "conversation_id": conversation_id,
            "answer_type": "faq_direct_match",
            "performance": {"total_ms": total_ms, "gemini_called": False},
        }

    # Lọc bỏ các chunk quá xa về ngữ nghĩa (khoảng cách cosine > ngưỡng) và giới hạn top K cho Gemini
    gemini_retrieved_chunks = retrieved_chunks[:settings.TOP_K_RESULTS]
    relevant_chunks = _filter_relevant_chunks(gemini_retrieved_chunks)

    # Giới hạn tổng độ dài ngữ cảnh để tránh prompt quá dài gửi Gemini
    context_texts = []
    current_length = 0
    final_chunks = []

    for c in relevant_chunks:
        text = c["content"]
        if current_length + len(text) > 3000:
            # Nếu đã đủ ngữ cảnh (>3000 ký tự), dừng lại
            if not context_texts:
                # Trường hợp đặc biệt: chunk đầu tiên đã > 3000 ký tự → vẫn lấy
                context_texts.append(text)
                final_chunks.append(c)
            break
        context_texts.append(text)
        final_chunks.append(c)
        current_length += len(text)

    # ─────────────────────────────────────────────────────────────────
    # FALLBACK: Không có ngữ cảnh phù hợp → không gọi Gemini
    # Tránh để AI "bịa đặt" thông tin không có trong tài liệu
    # ─────────────────────────────────────────────────────────────────
    if not context_texts:
        conversation_store.add_message(conversation_id, "user", question)
        conversation_store.add_message(conversation_id, "assistant", FALLBACK_MESSAGE)

        total_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning("Không có ngữ cảnh phù hợp → fallback | total_ms: %d", total_ms)

        return {
            "answer": FALLBACK_MESSAGE,
            "sources": [],
            "has_context": False,
            "retrieved_count": len(retrieved_chunks),
            "conversation_id": conversation_id,
            "answer_type": "fallback",
            "performance": {"total_ms": total_ms, "gemini_called": False},
        }

    # ─────────────────────────────────────────────────────────────────
    # BƯỚC 6 ĐỀ BÀI: TỔNG HỢP CÂU TRẢ LỜI VỚI GEMINI
    # Kết hợp ngữ cảnh + câu hỏi + lịch sử → gửi Gemini sinh câu trả lời
    # ─────────────────────────────────────────────────────────────────
    sources = _build_source_list(final_chunks)

    try:
        # Gọi Gemini để sinh câu trả lời (có timeout 15 giây)
        import asyncio
        answer = await asyncio.wait_for(
            asyncio.to_thread(
                generate_answer,
                context_chunks=context_texts,   # Ngữ cảnh truy xuất được
                question=question,              # Câu hỏi gốc của người dùng
                conversation_history=history,   # Lịch sử hội thoại để hiểu ngữ cảnh
            ),
            timeout=15.0
        )
        answer_type = "rag_generated"

    except asyncio.TimeoutError:
        # Gemini phản hồi quá chậm → dùng fallback
        logger.error("Gemini timeout (>15s) khi sinh câu trả lời")
        answer = _get_best_local_fallback(question, final_chunks) or TIMEOUT_MESSAGE
        if answer == TIMEOUT_MESSAGE:
            sources = []
        answer_type = "fallback"

    except Exception as e:
        # Các lỗi khác (rate limit, mạng...) → dùng fallback
        logger.error("Lỗi khi gọi Gemini: %s", str(e))
        answer = _get_best_local_fallback(question, final_chunks) or FALLBACK_MESSAGE
        if answer == FALLBACK_MESSAGE:
            sources = []
        answer_type = "fallback"

    # ─────────────────────────────────────────────────────────────────
    # LƯU LỊCH SỬ HỘI THOẠI (Lời khuyên 1 đề bài)
    # Giúp chatbot nhớ được ngữ cảnh câu trước → câu sau
    # ─────────────────────────────────────────────────────────────────
    conversation_store.add_message(conversation_id, "user", question)
    conversation_store.add_message(conversation_id, "assistant", answer)

    # Tính tổng thời gian xử lý
    total_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "RAG hoàn thành | câu hỏi: '%s...' | chunks: %d → %d | answer_type: %s | total_ms: %d",
        question[:50],
        len(retrieved_chunks),
        len(final_chunks),
        answer_type,
        total_ms,
    )

    return {
        "answer": answer,
        "sources": sources,
        "has_context": len(final_chunks) > 0,
        "retrieved_count": len(final_chunks),
        "conversation_id": conversation_id,
        "answer_type": answer_type,
        "performance": {"total_ms": total_ms, "gemini_called": answer_type == "rag_generated"},
    }
