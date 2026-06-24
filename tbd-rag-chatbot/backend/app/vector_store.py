# -*- coding: utf-8 -*-
"""
Module quản lý ChromaDB Vector Database.
Lưu trữ, truy xuất và quản lý các chunk văn bản đã được nhúng (embedded).

Theo lời khuyên 3 của đề bài: dùng PersistentClient thay vì Client() thông thường
để dữ liệu được lưu xuống ổ đĩa, không bị mất khi tắt chương trình.

Cấu hình ChromaDB:
- PersistentClient: lưu dữ liệu ra đĩa (thư mục chroma_db/)
- Cosine distance: phù hợp với Gemini embedding (vector đơn vị)
- Phòng chống trùng lặp: kiểm tra chunk_id trước khi insert
"""

import logging
from typing import Optional

# Thư viện Vector Database gọn nhẹ, chạy local không cần server
# pip install chromadb
import chromadb
from chromadb import Collection, PersistentClient

from app.config import settings
from app.gemini_client import embed_document, embed_query, embed_documents

logger = logging.getLogger(__name__)

# Biến singleton: chỉ tạo 1 client và 1 collection duy nhất
_chroma_client: Optional[PersistentClient] = None
_collection: Optional[Collection] = None


# =====================================================================
# KHỞI TẠO CHROMADB CLIENT VÀ COLLECTION
# =====================================================================

def get_client() -> PersistentClient:
    """
    Trả về ChromaDB PersistentClient đã khởi tạo.

    Theo lời khuyên 3 đề bài: dùng PersistentClient(path=...) để dữ liệu
    vector được lưu xuống ổ cứng, không bị mất khi tắt chương trình.
    Dữ liệu được lưu tại thư mục CHROMA_PERSIST_DIR trong file .env.
    """
    global _chroma_client
    if _chroma_client is None:
        # Tạo PersistentClient với đường dẫn lưu trữ cố định
        _chroma_client = chromadb.PersistentClient(path=str(settings.chroma_persist_path))
        logger.info("Đã kết nối ChromaDB tại: %s", str(settings.chroma_persist_path))
    return _chroma_client


def get_collection() -> Collection:
    """
    Trả về collection ChromaDB.
    Tạo mới nếu chưa tồn tại (dùng get_or_create_collection như đề bài).

    Collection lưu toàn bộ kiến thức về trường TBD.
    Cosine distance được chọn vì phù hợp với Gemini embedding.
    """
    global _collection
    if _collection is None:
        client = get_client()
        # get_or_create_collection: tạo mới hoặc lấy lại collection đã có
        # Đây chính là cách đề bài nâng cao hướng dẫn để không nạp lại dữ liệu
        _collection = client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            # Dùng cosine distance để đo độ tương đồng ngữ nghĩa
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Đã lấy collection '%s' (số lượng hiện tại: %d)",
            settings.COLLECTION_NAME,
            _collection.count(),
        )
    return _collection


# =====================================================================
# BƯỚC 4 (Đề bài): LƯU TRỮ VÀO VECTOR DATABASE (ChromaDB)
# =====================================================================

def add_documents(chunks: list[dict], rebuild: bool = False) -> dict:
    """
    Nhúng và thêm các chunk vào ChromaDB.

    Theo đề bài (Bước 4): tiến hành embed và lưu từng đoạn text vào DB.
    Cải tiến thêm: bỏ qua chunk đã tồn tại để tránh trùng lặp dữ liệu.

    Args:
        chunks: Danh sách chunk dict chứa content, metadata, chunk_id
        rebuild: Nếu True, xóa collection cũ và nạp lại từ đầu

    Returns:
        Dict thống kê: {"added": int, "skipped": int, "failed": int}
    """
    if not chunks:
        return {"added": 0, "skipped": 0, "failed": 0}

    # Nếu rebuild=True: xóa toàn bộ dữ liệu cũ và nạp lại
    if rebuild:
        logger.info("Chế độ Rebuild: Xóa toàn bộ collection trước khi nạp.")
        try:
            clear_collection()
        except Exception as e:
            logger.error("Lỗi khi xóa collection trong chế độ Rebuild: %s", str(e))

    collection = get_collection()
    stats = {"added": 0, "skipped": 0, "failed": 0}

    # Lấy danh sách chunk_id và content_hash đang có sẵn trong DB
    # Mục đích: phát hiện chunk đã nạp rồi để bỏ qua, không tốn API call
    existing_hashes: dict[str, str] = {}
    if not rebuild:
        try:
            existing_result = collection.get(include=["metadatas"])
            if existing_result and existing_result.get("ids"):
                for i, doc_id in enumerate(existing_result["ids"]):
                    meta = existing_result["metadatas"][i] if existing_result.get("metadatas") else None
                    existing_hashes[doc_id] = meta.get("content_hash", "") if meta else ""
        except Exception as e:
            logger.warning("Không thể lấy danh sách ID hiện có: %s", str(e))

    # Lọc ra các chunk mới chưa có hoặc đã thay đổi nội dung
    new_chunks = []
    for chunk in chunks:
        cid = chunk["chunk_id"]
        chash = chunk.get("content_hash", "")
        if not rebuild and cid in existing_hashes and existing_hashes[cid] == chash:
            # Chunk này đã có và nội dung chưa thay đổi → bỏ qua
            stats["skipped"] += 1
        else:
            new_chunks.append(chunk)

    if stats["skipped"] > 0:
        logger.info("Bỏ qua %d chunk trùng lặp đã có trong database", stats["skipped"])

    if not new_chunks:
        logger.info("Không có chunk mới nào cần nạp")
        return stats

    # Nhúng và thêm theo batch (mỗi batch 30 chunks)
    # Tránh gọi API quá nhiều lần và tránh lỗi payload quá lớn
    batch_size = 30
    for i in range(0, len(new_chunks), batch_size):
        batch = new_chunks[i:i + batch_size]
        try:
            # Nhúng toàn bộ text trong batch thành vector (batch embedding)
            texts = [c["content"] for c in batch]
            embeddings = embed_documents(texts)

            # Chuẩn bị dữ liệu để đưa vào ChromaDB
            ids = [c["chunk_id"] for c in batch]
            documents = [c["content"] for c in batch]
            metadatas = []

            for chunk in batch:
                # Metadata giúp truy vết nguồn gốc và lọc kết quả sau này
                metadata = {
                    "source": chunk.get("source", ""),
                    "source_type": chunk.get("source_type", "file"),
                    "title": chunk.get("title", ""),
                    "section": chunk.get("section", ""),
                    "ingested_at": chunk.get("ingested_at", ""),
                    "source_priority": int(chunk.get("source_priority", 3)),
                    "content_hash": chunk.get("content_hash", ""),
                    "local_path": chunk.get("local_path", "") or "",
                    "original_url": chunk.get("original_url", "") or "",
                }
                metadatas.append(metadata)

            # Upsert: thêm mới hoặc cập nhật nếu ID đã tồn tại
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            stats["added"] += len(batch)
            logger.info("Đã nạp thành công batch chunk %d → %d", i, i + len(batch))

        except Exception as e:
            logger.error(
                "Lỗi khi thêm batch chunk %d → %d: %s",
                i, i + min(batch_size, len(new_chunks) - i), str(e)
            )
            stats["failed"] += len(batch)

    logger.info(
        "Kết quả ingest: %d chunk mới, %d trùng lặp bỏ qua, %d thất bại",
        stats["added"],
        stats["skipped"],
        stats["failed"],
    )
    return stats


# =====================================================================
# BƯỚC 5 (Đề bài): TRUY XUẤT THÔNG TIN LIÊN QUAN (Retrieval)
# =====================================================================

def query_similar(question_text: str, n_results: int = None) -> list[dict]:
    """
    Tìm kiếm các chunk có ngữ nghĩa gần giống nhất với câu hỏi.

    Theo đề bài (Bước 5): chuyển câu hỏi thành vector, tìm trong ChromaDB
    những đoạn văn bản có "ngữ nghĩa" gần giống nhất.

    Khác đề bài cơ bản: dùng embed_query (RETRIEVAL_QUERY) thay vì
    cùng hàm embed với tài liệu, giúp tăng độ chính xác retrieval.

    Args:
        question_text: Câu hỏi của người dùng
        n_results: Số lượng chunk muốn lấy (mặc định TOP_K_RESULTS = 4)

    Returns:
        Danh sách dict chứa: content, metadata, distance (khoảng cách cosine)
    """
    if n_results is None:
        n_results = settings.TOP_K_RESULTS

    collection = get_collection()

    # Kiểm tra database có dữ liệu chưa, tránh lỗi khi query rỗng
    count = collection.count()
    if count == 0:
        logger.warning("Vector database đang trống - chưa có dữ liệu nào được nạp")
        return []

    try:
        # Bước 5.1: Biến câu hỏi của user thành vector (dùng RETRIEVAL_QUERY)
        query_embedding = embed_query(question_text)

        # Bước 5.2: Tìm kiếm trong ChromaDB - lấy n_results chunk gần nhất
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, count),  # Không query nhiều hơn số lượng có
            include=["documents", "metadatas", "distances"],
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        # Định dạng kết quả về cấu trúc thống nhất
        chunks = []
        for i, doc_id in enumerate(results["ids"][0]):
            chunks.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],  # Khoảng cách cosine (0=giống nhất)
                "chunk_id": doc_id,
            })

        return chunks

    except Exception as e:
        logger.error("Lỗi khi truy xuất ChromaDB: %s", str(e))
        return []


# =====================================================================
# CÁC HÀM TIỆN ÍCH QUẢN LÝ DATABASE
# =====================================================================

def clear_collection() -> None:
    """
    Xóa toàn bộ dữ liệu trong collection và khởi tạo lại collection mới.
    Dùng khi thực hiện rebuild index.
    """
    global _collection
    client = get_client()

    try:
        # Xóa collection cũ
        client.delete_collection(name=settings.COLLECTION_NAME)
        logger.info("Đã xóa collection '%s'", settings.COLLECTION_NAME)
    except Exception:
        pass  # Nếu collection chưa tồn tại, không sao

    # Tạo lại collection mới với cosine distance
    _collection = client.create_collection(
        name=settings.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("Đã tạo lại collection '%s'", settings.COLLECTION_NAME)


def get_stats() -> dict:
    """
    Lấy thống kê cơ bản của vector database (dùng cho health check).

    Returns:
        Dict chứa: count (số chunk), collection_name
    """
    try:
        collection = get_collection()
        return {
            "count": collection.count(),
            "collection_name": settings.COLLECTION_NAME,
        }
    except Exception as e:
        logger.error("Lỗi khi lấy thống kê ChromaDB: %s", str(e))
        return {"count": 0, "collection_name": settings.COLLECTION_NAME}
