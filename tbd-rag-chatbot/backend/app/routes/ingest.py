# -*- coding: utf-8 -*-
"""
Routes ingest tài liệu: POST /api/ingest/files, /urls, /rebuild
Quản lý việc thêm tài liệu vào ChromaDB vector database.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, field_validator

from app.chunker import split_documents
from app.config import settings
from app.document_loader import SUPPORTED_EXTENSIONS, load_file, load_url
from app.vector_store import add_documents, clear_collection
from app.services.website_sync_service import website_sync_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Kich thuoc file toi da: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

from app.seed_urls import SEED_URLS


class IngestUrlsRequest(BaseModel):
    """Schema request cho ingest URLs."""

    urls: list[str]

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Danh sách URL không được rỗng")
        if len(v) > settings.MAX_PAGES_PER_INGESTION:
            raise ValueError(
                f"Quá nhiều URL. Tối đa {settings.MAX_PAGES_PER_INGESTION} URL mỗi lần."
            )
        return [url.strip() for url in v if url.strip()]


class IngestResult(BaseModel):
    """Schema response cho ket qua ingest."""

    added: int
    skipped: int
    failed: int
    message: str


@router.post("/ingest/urls", response_model=IngestResult)
async def ingest_urls(request: IngestUrlsRequest) -> IngestResult:
    """
    Ingest noi dung tu danh sach URL cua TBD University.
    Chi chap nhan URL tu domain https://tbd.edu.vn/.
    Khong crawl de quy - chi lay dung cac URL duoc cung cap.

    Kiem tra bao mat:
    - Domain whitelist: tu choi tat ca URL ngoai tbd.edu.vn
    - Gioi han so luong URL: MAX_PAGES_PER_INGESTION
    - Timeout: URL_REQUEST_TIMEOUT giay moi request
    """
    logger.info("Bat dau ingest %d URL", len(request.urls))

    all_documents = []
    failed_count = 0

    for url in request.urls:
        docs = load_url(url)
        if docs:
            all_documents.extend(docs)
        else:
            # load_url tra ve [] khi domain bi tu choi hoac fetch that bai
            failed_count += 1

    if not all_documents:
        return IngestResult(
            added=0,
            skipped=0,
            failed=failed_count,
            message="Không tải được nội dung nào. Kiểm tra lại URL và đảm bảo chỉ dùng tên miền tbd.edu.vn hoặc tuyensinh.tbd.edu.vn.",
        )

    # Tach tai lieu thanh chunk
    chunks = split_documents(all_documents)

    # Them vao ChromaDB (co duplicate prevention)
    stats = add_documents(chunks)
    stats["failed"] = stats.get("failed", 0) + failed_count

    message = (
        f"Đã xử lý {len(request.urls)} URL: "
        f"thêm {stats['added']} chunk mới, "
        f"bỏ qua {stats['skipped']} trùng lặp, "
        f"{stats['failed']} thất bại."
    )
    logger.info(message)

    return IngestResult(
        added=stats["added"],
        skipped=stats["skipped"],
        failed=stats["failed"],
        message=message,
    )


@router.post("/ingest/files", response_model=IngestResult)
async def ingest_files(files: list[UploadFile] = File(...)) -> IngestResult:
    """
    Ingest tai lieu tu file upload.
    Ho tro: .txt, .pdf, .docx, .md, .markdown
    Kich thuoc toi da: 10 MB moi file.

    Bao mat:
    - Kiem tra extension file (whitelist)
    - Kiem tra kich thuoc file
    - Luu vao thu muc uploaded_files cuc bo
    """
    logger.info("Bat dau ingest %d file", len(files))

    # Dam bao thu muc luu tru upload ton tai
    settings.uploaded_files_dir_path.mkdir(parents=True, exist_ok=True)

    all_documents = []
    failed_count = 0
    skipped_count = 0

    for upload in files:
        filename = upload.filename or "unknown"
        ext = Path(filename).suffix.lower()

        # Kiem tra dinh dang file
        if ext not in SUPPORTED_EXTENSIONS:
            logger.warning("Tu choi file khong ho tro: %s (dinh dang: %s)", filename, ext)
            failed_count += 1
            continue

        # Doc noi dung file
        content = await upload.read()

        # Kiem tra kich thuoc
        if len(content) > MAX_FILE_SIZE_BYTES:
            logger.warning(
                "Tu choi file qua lon: %s (%d bytes > %d bytes toi da)",
                filename,
                len(content),
                MAX_FILE_SIZE_BYTES,
            )
            failed_count += 1
            continue

        if len(content) == 0:
            logger.warning("File rong: %s", filename)
            skipped_count += 1
            continue

        # Luu vao thu muc uploaded_files cuc bo
        try:
            file_path = settings.uploaded_files_dir_path / filename
            with open(file_path, "wb") as f:
                f.write(content)

            docs = load_file(str(file_path))
            if docs:
                for doc in docs:
                    doc["source"] = filename
                    doc["source_type"] = "uploaded_file"
                    doc["title"] = doc.get("title") or filename
                    doc["local_path"] = str(file_path.relative_to(settings.backend_root))
                all_documents.extend(docs)
            else:
                failed_count += 1

        except Exception as e:
            logger.error("Loi khi xu ly file '%s': %s", filename, str(e))
            failed_count += 1

    if not all_documents:
        return IngestResult(
            added=0,
            skipped=skipped_count,
            failed=failed_count,
            message="Không xử lý được file nào. Kiểm tra định dạng và kích thước file.",
        )

    # Tach tai lieu thanh chunk
    chunks = split_documents(all_documents)

    # Them vao ChromaDB (luon dung incremental mac dinh cho upload le)
    stats = add_documents(chunks, rebuild=False)
    stats["failed"] = stats.get("failed", 0) + failed_count
    stats["skipped"] = stats.get("skipped", 0) + skipped_count

    message = (
        f"Đã xử lý {len(files)} file: "
        f"thêm {stats['added']} chunk mới, "
        f"bỏ qua {stats['skipped']} trùng lặp, "
        f"{stats['failed']} thất bại."
    )
    logger.info(message)

    return IngestResult(
        added=stats["added"],
        skipped=stats["skipped"],
        failed=stats["failed"],
        message=message,
    )


class SyncSingleUrlRequest(BaseModel):
    """Schema request cho dong bo 1 URL."""
    url: str

class IngestLocalRequest(BaseModel):
    """Schema request cho nap du lieu tu file cuc bo."""
    rebuild: bool = True

@router.post("/admin/sync/seed-urls")
async def sync_seed_urls():
    """
    Dong bo tat ca seed URLs tu website chinh thuc.
    Luu cac ban ghi JSON va MD cuc bo, va ghi nhan manifest.
    """
    logger.info("Yeu cau dong bo tat ca seed URLs tu admin")
    try:
        summary = website_sync_service.sync_seed_urls()
        return summary
    except Exception as e:
        logger.error("Loi khi dong bo seed URLs: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Loi dong bo seed URLs: {str(e)}")

@router.post("/admin/sync/url")
async def sync_url(request: SyncSingleUrlRequest):
    """
    Dong bo mot URL bat ky thuoc domain cho phep ve local.
    """
    logger.info("Yeu cau dong bo URL tu admin: %s", request.url)
    try:
        result = website_sync_service.sync_single_url(request.url)
        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Loi khi dong bo URL '%s': %s", request.url, str(e))
        raise HTTPException(status_code=500, detail=f"Loi dong bo URL: {str(e)}")

@router.get("/admin/sync/status")
async def sync_status():
    """
    Lay thong tin trang thai dong bo hien tai tu manifest va kich thuoc file.
    """
    try:
        return website_sync_service.get_sync_status()
    except Exception as e:
        logger.error("Loi khi lay status dong bo: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest/local", response_model=IngestResult)
async def ingest_local(request: IngestLocalRequest = IngestLocalRequest(rebuild=True)) -> IngestResult:
    """
    Nap tat ca du lieu da tai va curated FAQ cuc bo vao ChromaDB.
    Ho tro hai che do: Rebuild (mac dinh) va Incremental.
    """
    logger.info("Bat dau ingest du lieu local | rebuild: %s", request.rebuild)
    all_documents = []
    failed_count = 0
    skipped_count = 0

    # 1. Tai cac trang web local da dong bo
    try:
        web_pages = website_sync_service.load_local_web_pages()
        all_documents.extend(web_pages)
        logger.info("Da nap %d trang web local", len(web_pages))
    except Exception as e:
        logger.error("Loi khi doc web pages local: %s", str(e))
        failed_count += 1

    # 2. Tai curated FAQ va additional FAQ tu thu muc faq
    faq_dir = settings.faq_dir_path
    if faq_dir.exists():
        faq_count = 0
        for faq_file in faq_dir.glob("*.json"):
            try:
                with open(faq_file, "r", encoding="utf-8") as f:
                    faqs = json.load(f)
                    for entry in faqs:
                        all_documents.append({
                            "content": f"Câu hỏi thường gặp: {entry['question']}\nTrả lời: {entry['answer']}",
                            "source": entry.get("source_url") or f"data/raw/faq/{faq_file.name}",
                            "source_type": "curated_faq",
                            "title": entry.get("source_title") or "Câu hỏi thường gặp đã biên soạn",
                            "original_url": entry.get("source_url") or "",
                            "local_path": f"data/raw/faq/{faq_file.name}"
                        })
                    faq_count += len(faqs)
                logger.info("Da nap %d cau hoi tu '%s'", len(faqs), faq_file.name)
            except Exception as e:
                logger.error("Loi khi doc file FAQ '%s': %s", faq_file.name, str(e))
                failed_count += 1
        logger.info("Tong so cau hoi FAQ da nap: %d", faq_count)
    else:
        logger.warning("Khong tim thay thu muc FAQ de ingest")

    # 3. Tai file uploaded_files
    uploaded_dir = settings.uploaded_files_dir_path
    if uploaded_dir.exists():
        file_count = 0
        for file_path in uploaded_dir.glob("*"):
            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                try:
                    docs = load_file(str(file_path))
                    for d in docs:
                        d["source_type"] = "uploaded_file"
                        d["local_path"] = str(file_path.relative_to(settings.backend_root))
                    all_documents.extend(docs)
                    file_count += 1
                except Exception as e:
                    logger.error("Loi khi nap file upload '%s': %s", file_path.name, str(e))
                    failed_count += 1
        logger.info("Da nap %d file tai len tu uploaded_files", file_count)

    if not all_documents:
        return IngestResult(
            added=0,
            skipped=0,
            failed=failed_count,
            message="Không tìm thấy dữ liệu cục bộ nào để nạp. Hãy đồng bộ website trước.",
        )

    # 4. Phân tách tài liệu thành chunks
    chunks = split_documents(all_documents)

    # 5. Ingest vao ChromaDB
    stats = add_documents(chunks, rebuild=request.rebuild)
    stats["failed"] = stats.get("failed", 0) + failed_count

    mode_label = "Rebuild" if request.rebuild else "Incremental"
    message = (
        f"Nạp dữ liệu local ({mode_label}) hoàn tất: "
        f"thêm {stats['added']} chunk mới, "
        f"bỏ qua {stats['skipped']} trùng lặp, "
        f"{stats['failed']} thất bại."
    )
    logger.info(message)

    return IngestResult(
        added=stats["added"],
        skipped=stats["skipped"],
        failed=stats["failed"],
        message=message,
    )


@router.post("/ingest/rebuild", response_model=IngestResult)
async def rebuild_index() -> IngestResult:
    """
    Endpoint giu nguyen tinh tuong thich:
    Goi truc tiep ingest_local voi rebuild=True.
    """
    logger.info("Endpoint rebuild duoc goi (redirect den ingest_local)")
    return await ingest_local(IngestLocalRequest(rebuild=True))
