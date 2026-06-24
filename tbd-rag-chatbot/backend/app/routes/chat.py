# -*- coding: utf-8 -*-
"""
Route xử lý câu hỏi chat: POST /api/chat

Nhận câu hỏi từ frontend, gọi RAG pipeline xử lý và trả về câu trả lời.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app import rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


# =====================================================================
# SCHEMA REQUEST VÀ RESPONSE CHO ENDPOINT /api/chat
# =====================================================================

class ChatRequest(BaseModel):
    """Schema dữ liệu đầu vào từ người dùng."""

    question: str                    # Câu hỏi của người dùng
    conversation_id: str | None = None  # ID phiên hội thoại (None = tạo mới)

    @field_validator("question")
    @classmethod
    def question_must_not_be_empty(cls, v: str) -> str:
        """Kiểm tra câu hỏi không được rỗng và không quá dài."""
        v = v.strip()
        if not v:
            raise ValueError("Câu hỏi không được để trống")
        if len(v) > 2000:
            raise ValueError("Câu hỏi quá dài (tối đa 2000 ký tự)")
        return v


class PerformanceSchema(BaseModel):
    """Schema thống kê hiệu năng xử lý (để debug và theo dõi)."""
    total_ms: int        # Tổng thời gian xử lý (mili giây)
    gemini_called: bool  # Có gọi Gemini API không


class SourceSchema(BaseModel):
    """Schema cho một nguồn trích dẫn kèm theo câu trả lời."""
    title: str               # Tiêu đề tài liệu nguồn
    source: str              # URL hoặc đường dẫn file nguồn
    source_type: str         # Loại nguồn: "official_website" | "uploaded_file"
    snippet: str             # Đoạn trích ngắn từ tài liệu
    distance: float          # Khoảng cách cosine (0=giống nhất, 1=khác nhất)
    original_url: str | None = None  # URL gốc nếu là trang web
    local_path: str | None = None    # Đường dẫn file local nếu là tài liệu tải lên


class ChatResponse(BaseModel):
    """Schema dữ liệu trả về cho frontend."""
    answer: str                    # Câu trả lời của chatbot
    sources: list[SourceSchema]    # Danh sách nguồn trích dẫn
    has_context: bool              # Có tìm được ngữ cảnh phù hợp không
    retrieved_count: int           # Số chunk đã truy xuất được
    conversation_id: str           # ID phiên hội thoại (để gửi lại lần sau)
    answer_type: str               # Loại câu trả lời: "greeting" | "rag_generated" | "fallback"
    performance: PerformanceSchema # Thông tin hiệu năng


# =====================================================================
# ENDPOINT POST /api/chat
# =====================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Xử lý câu hỏi người dùng và trả về câu trả lời từ RAG pipeline.

    Luồng xử lý:
    1. Nhận câu hỏi + conversation_id (tùy chọn) từ frontend
    2. Gọi rag_pipeline.run() để thực hiện toàn bộ luồng RAG
    3. Định dạng kết quả và trả về cho frontend
    """
    logger.info(
        "Nhận câu hỏi chat | conversation: %s | câu hỏi: '%s'",
        request.conversation_id or "mới",
        request.question[:80],
    )

    try:
        # Gọi RAG pipeline xử lý câu hỏi (async)
        result = await rag_pipeline.run(
            question=request.question,
            conversation_id=request.conversation_id,
        )
    except RuntimeError as e:
        # Lỗi cấu hình (thiếu API key, v.v.)
        logger.error("Lỗi cấu hình khi xử lý chat: %s", str(e))
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Lỗi không xác định
        logger.error("Lỗi không xác định khi xử lý chat: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="Lỗi hệ thống. Vui lòng thử lại sau.",
        )

    # Định dạng danh sách nguồn trích dẫn theo đúng SourceSchema
    formatted_sources = []
    for s in result["sources"]:
        formatted_sources.append(
            SourceSchema(
                title=s["title"],
                source=s["source"],
                source_type=s["source_type"],
                snippet=s["snippet"],
                distance=float(s.get("distance", 0.0) or 0.0),
                original_url=s.get("original_url"),
                local_path=s.get("local_path")
            )
        )

    # Lấy thông tin hiệu năng từ pipeline (total_ms và gemini_called)
    perf = result.get("performance", {})

    return ChatResponse(
        answer=result["answer"],
        sources=formatted_sources,
        has_context=result["has_context"],
        retrieved_count=result["retrieved_count"],
        conversation_id=result["conversation_id"],
        answer_type=result["answer_type"],
        performance=PerformanceSchema(
            total_ms=perf.get("total_ms", 0),
            gemini_called=perf.get("gemini_called", False),
        ),
    )
