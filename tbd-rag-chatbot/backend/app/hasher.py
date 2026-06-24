"""
Module tao hash xac dinh va ID on dinh cho tai lieu va chunk.

Muc dich:
- Tao chunk_id duy nhat va xac dinh (deterministic) dua tren noi dung
- Cung mot noi dung + nguon -> luon tao ra cung mot ID
- Cho phep ChromaDB phat hien va bo qua chunk trung lap khi ingest nhieu lan
- Khong phu thuoc vao thoi gian hay thu tu xu ly

Thuat toan: SHA-256 cua (source + chunk_index + 100 ky tu dau cua noi dung)
Lay 16 ky tu dau hex -> du ngan de luu tru, du dai de tranh xung dot
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


def generate_chunk_id(source: str, chunk_index: int, content: str) -> str:
    """
    Tao ID xac dinh duy nhat cho mot chunk.

    Cong thuc: sha256(source + "|" + str(chunk_index) + "|" + content[:100])[:16]

    Ly do chon cach nay:
    - source: dam bao ID khac nhau cho cung chunk_index tu cac nguon khac nhau
    - chunk_index: dam bao ID khac nhau cho cac chunk lien tiep cua cung tai lieu
    - content[:100]: dam bao ID phan anh noi dung thuc su (tranh xung dot khi tai lieu thay doi)
    - 16 ky tu hex: 2^64 kha nang, du ngan de luu tru

    Args:
        source: URL hoac duong dan file cua tai lieu goc
        chunk_index: Vi tri thu tu cua chunk trong tai lieu (0-based)
        content: Noi dung van ban cua chunk

    Returns:
        Chuoi hex 16 ky tu lam chunk ID
    """
    # Chuan hoa dau vao de dam bao tinh on dinh
    source_normalized = source.strip().lower()
    content_prefix = content.strip()[:100]

    # Tao chuoi dau vao duy nhat
    raw = f"{source_normalized}|{chunk_index}|{content_prefix}"

    # Tinh SHA-256 va lay 16 ky tu dau
    chunk_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return chunk_id


def generate_document_hash(source: str, content: str) -> str:
    """
    Tao hash dai dien cho toan bo tai lieu.
    Dung de kiem tra nhanh xem tai lieu co thay doi so voi lan ingest truoc khong.

    Args:
        source: URL hoac duong dan file
        content: Toan bo noi dung tai lieu

    Returns:
        Chuoi hex 32 ky tu (SHA-256 rut gon)
    """
    source_normalized = source.strip().lower()
    raw = f"{source_normalized}|{content.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
