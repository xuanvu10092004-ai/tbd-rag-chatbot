# -*- coding: utf-8 -*-
"""
Điểm vào chính của FastAPI backend - TBD RAG Chatbot.
Cấu hình CORS, đăng ký routers, và khởi động ứng dụng.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, setup_logging, validate_settings, initialize_directories
from app.routes import chat, health, ingest

# Cau hinh logging truoc khi bat ky log nao duoc ghi
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Quan ly vong doi ung dung:
    - Startup: validate cau hinh, log banner
    - Shutdown: log thong bao thoat
    """
    # --- Startup ---
    try:
        # Khởi tạo các thư mục dữ liệu cục bộ
        initialize_directories()
        validate_settings(settings)
        gemini_ok = True
    except RuntimeError as e:
        logger.warning("CANH BAO CAU HINH: %s. Backend se chay o che do DEGRADED.", str(e))
        gemini_ok = False

    # Lay thong ke ChromaDB
    try:
        from app.vector_store import get_stats
        db_stats = get_stats()
        db_count = db_stats.get("count", 0)
    except Exception:
        db_count = -1

    logger.info("=" * 60)
    logger.info("TBD RAG Chatbot Backend dang khoi dong...")
    logger.info("Cổng Backend: 8001")
    logger.info("CORS Origins: %s, http://localhost:5173, http://127.0.0.1:5173", settings.FRONTEND_ORIGIN)
    logger.info("ChromaDB Collection: %s", settings.COLLECTION_NAME)
    logger.info("ChromaDB Document Count: %d", db_count)
    logger.info("Thư mục dữ liệu cục bộ:")
    logger.info("  - Raw: %s", settings.raw_dir_path)
    logger.info("  - Web Pages: %s", settings.web_pages_dir_path)
    logger.info("  - FAQ: %s", settings.faq_dir_path)
    logger.info("  - Uploaded Files: %s", settings.uploaded_files_dir_path)
    logger.info("Cấu hình Gemini: %s", "Đã cấu hình" if gemini_ok else "Chưa cấu hình (Thiếu API Key)")
    logger.info("URL API Health: http://localhost:8001/api/health")
    logger.info("=" * 60)

    yield

    # --- Shutdown ---
    logger.info("TBD RAG Chatbot Backend dang tat...")


from fastapi.responses import JSONResponse
import json
import typing

class UnicodeJSONResponse(JSONResponse):
    """
    Custom JSONResponse subclass to ensure that Unicode characters
    are returned directly in the response instead of escaped ASCII.
    """
    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# Tao FastAPI app
app = FastAPI(
    title="TBD RAG Chatbot API",
    description=(
        "Backend RAG cho chatbot ho tro tuyen sinh Truong Dai hoc Thai Binh Duong. "
        "Su dung Gemini va ChromaDB."
    ),
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=UnicodeJSONResponse,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Cau hinh CORS - cho phep frontend goi backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

# Dang ky cac router
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(ingest.router, prefix="/api", tags=["ingest"])


@app.get("/")
async def root():
    """Endpoint gốc - hướng dẫn đến API docs."""
    return {
        "message": "TBD RAG Chatbot API đang chạy",
        "docs": "/api/docs",
        "health": "/api/health",
    }
