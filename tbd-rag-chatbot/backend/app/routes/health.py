"""
Route health check: GET /api/health
Tra ve trang thai cua backend, Gemini API, va ChromaDB.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.vector_store import get_stats

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Schema response cho health check."""

    status: str
    backend_port: int
    gemini_configured: bool
    vector_db_count: int
    collection_name: str
    local_data_ready: bool
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Kiem tra trang thai he thong.
    Tra ve thong tin ve Gemini API va ChromaDB.
    """
    # Kiem tra API key da cau hinh chua
    gemini_ok = bool(
        settings.GEMINI_API_KEY
        and settings.GEMINI_API_KEY != "your_gemini_api_key_here"
    )

    # Lay thong ke ChromaDB
    try:
        db_stats = get_stats()
        db_count = db_stats.get("count", 0)
        collection_name = db_stats.get("collection_name", settings.COLLECTION_NAME)
        db_error = False
    except Exception as e:
        logger.error("Khong the lay thong ke ChromaDB: %s", str(e))
        db_count = -1
        collection_name = settings.COLLECTION_NAME
        db_error = True

    # Xac dinh trang thai tong the
    if db_error:
        status = "error"
    elif not gemini_ok:
        status = "degraded"
    elif db_count == 0:
        # Database trong - van chay duoc nhung can ingest du lieu
        status = "degraded"
    else:
        status = "ok"

    # Kiem tra local data folders va curated_faq.json
    local_data_ready = (
        settings.faq_file_path.exists() and
        settings.raw_dir_path.exists() and
        settings.web_pages_dir_path.exists()
    )

    logger.info(
        "Health check: status=%s, db_count=%d, gemini_ok=%s, local_data_ready=%s",
        status, db_count, gemini_ok, local_data_ready
    )

    return HealthResponse(
        status=status,
        backend_port=8001,
        gemini_configured=gemini_ok,
        vector_db_count=db_count,
        collection_name=collection_name,
        local_data_ready=local_data_ready,
        message="Backend đang hoạt động",
    )
