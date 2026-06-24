# -*- coding: utf-8 -*-
"""
Cấu hình trung tâm của ứng dụng TBD RAG Chatbot.
Sử dụng pydantic-settings để tự động đọc biến môi trường từ file .env.
Validate giá trị bắt buộc ngay khi khởi động ứng dụng.
"""

import logging
import logging.handlers
import os
from pathlib import Path

# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Cau hinh ung dung duoc doc tu file .env.
    Tat ca gia tri co the ghi de qua bien moi truong he thong.
    """

    # --- Gemini API ---
    # Khoa API bat buoc - phai duoc cau hinh truoc khi chay
    GEMINI_API_KEY: str = ""

    # Model ID cho viec sinh cau tra loi
    GEMINI_MODEL_ID: str = "gemini-2.5-flash"

    # Model ID cho viec nhung van ban (embedding)
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"

    # --- ChromaDB ---
    # Thu muc luu tru persistent cho ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Ten collection luu tru kien thuc truong TBD
    COLLECTION_NAME: str = "tbd_knowledge_base"

    # --- Local-first data paths ---
    DATA_DIR: str = "data"
    RAW_DIR: str = "data/raw"
    WEB_PAGES_DIR: str = "data/raw/web_pages"
    FAQ_DIR: str = "data/raw/faq"
    UPLOADED_FILES_DIR: str = "data/raw/uploaded_files"
    PROCESSED_DIR: str = "data/processed"
    SNAPSHOTS_DIR: str = "data/snapshots"
    FAQ_FILE_PATH: str = "data/raw/faq/curated_faq.json"
    SYNC_MANIFEST_PATH: str = "data/processed/sync_manifest.json"

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def chroma_persist_path(self) -> Path:
        p = Path(self.CHROMA_PERSIST_DIR)
        if not p.is_absolute():
            return self.backend_root / p
        return p

    @property
    def data_dir_path(self) -> Path:
        return self.backend_root / self.DATA_DIR

    @property
    def raw_dir_path(self) -> Path:
        return self.backend_root / self.RAW_DIR

    @property
    def web_pages_dir_path(self) -> Path:
        return self.backend_root / self.WEB_PAGES_DIR

    @property
    def faq_dir_path(self) -> Path:
        return self.backend_root / self.FAQ_DIR

    @property
    def uploaded_files_dir_path(self) -> Path:
        return self.backend_root / self.UPLOADED_FILES_DIR

    @property
    def processed_dir_path(self) -> Path:
        return self.backend_root / self.PROCESSED_DIR

    @property
    def snapshots_dir_path(self) -> Path:
        return self.backend_root / self.SNAPSHOTS_DIR

    @property
    def faq_file_path(self) -> Path:
        return self.backend_root / self.FAQ_FILE_PATH

    @property
    def sync_manifest_path(self) -> Path:
        return self.backend_root / self.SYNC_MANIFEST_PATH

    # --- Ingest URL ---
    # So trang toi da duoc phep ingest trong mot lan goi API
    MAX_PAGES_PER_INGESTION: int = 20

    # Thoi gian cho toi da khi fetch mot URL (don vi: giay)
    URL_REQUEST_TIMEOUT: int = 10

    # --- Chunking ---
    # Kich thuoc chunk muc tieu (don vi: ky tu)
    CHUNK_SIZE: int = 800

    # Do chong cheo giua cac chunk lien tiep (don vi: ky tu)
    CHUNK_OVERLAP: int = 150

    # --- Retrieval ---
    # So luong chunk truy xuat toi da cho moi cau hoi
    TOP_K_RESULTS: int = 4

    # Nguong cosine distance de xac dinh chunk co lien quan
    # Gia tri nho hon = lien quan hon (0 = giong het, 1 = khac hoan toan)
    # Gia tri mac dinh 0.65 la khoi diem - can dieu chinh sau khi test voi du lieu TBD
    RELEVANCE_DISTANCE_THRESHOLD: float = 0.65

    # --- Lich su hoi thoai ---
    # So tin nhan toi da duoc giu lai trong mot conversation (khuyen nghi 8-12)
    MAX_HISTORY_MESSAGES: int = 10

    # --- CORS ---
    # Origin duoc phep goi backend (frontend URL)
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Cau hinh doc file .env tu cung thu muc voi file nay (backend/)
    # Dung duong dan tuyet doi de tranh loi phu thuoc vao thu muc hien tai (CWD)
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


def validate_settings(settings: Settings) -> None:
    """
    Kiem tra cac gia tri bat buoc ngay khi khoi dong.
    Raise RuntimeError neu thieu API key de tranh loi kho debug sau nay.
    """
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY chưa được cấu hình. "
            "Hãy sao chép file .env.example thành .env và điền GEMINI_API_KEY của bạn."
        )


def initialize_directories() -> None:
    """
    Tạo các thư mục dữ liệu cần thiết nếu chúng chưa tồn tại.
    """
    dirs = [
        settings.data_dir_path,
        settings.raw_dir_path,
        settings.web_pages_dir_path,
        settings.faq_dir_path,
        settings.uploaded_files_dir_path,
        settings.processed_dir_path,
        settings.snapshots_dir_path,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        logger.info("Khởi tạo thư mục dữ liệu cục bộ: %s", d)


def setup_logging(log_dir: str = "logs") -> None:
    """
    Cau hinh he thong logging:
    - Xuat ra console (stdout) voi dinh dang co mau
    - Xuat ra file log rotating (toi da 5MB moi file, giu 3 file)
    - Log level: INFO (ghi lai moi su kien quan trong)
    """
    # Tao thu muc logs neu chua ton tai
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Xoa handlers cu neu co (tranh duplicate log khi reload)
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Handler xuat ra console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # Handler xuat ra file rotating
    log_file = os.path.join(log_dir, "tbd_rag.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB moi file
        backupCount=3,              # giu toi da 3 file cu
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(file_handler)

    # Giam log nhieu tu cac thu vien ngoai
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Singleton settings - duoc import boi cac module khac
settings = Settings()
