# -*- coding: utf-8 -*-
"""
Script nạp dữ liệu chính thức từ danh sách URL hạt giống (seed URLs).
Chạy độc lập từ thư mục backend:
python scripts/seed_official_data.py
"""

import sys
from pathlib import Path

# Đảm bảo console Windows hỗ trợ hiển thị tiếng Việt có dấu (UTF-8)
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
if sys.stderr and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Thêm thư mục gốc backend vào sys.path để import được app
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings, setup_logging
from app.seed_urls import SEED_URLS
from app.document_loader import load_url
from app.chunker import split_documents
from app.vector_store import add_documents, get_stats

def main():
    setup_logging()
    print("=" * 60)
    print("Bắt đầu nạp dữ liệu chính thức của Trường Đại học Thái Bình Dương")
    print("=" * 60)
    
    total_urls = len(SEED_URLS)
    successful_urls = 0
    failed_urls = 0
    all_documents = []
    
    for idx, url in enumerate(SEED_URLS, 1):
        print(f"[{idx}/{total_urls}] Đang tải dữ liệu từ URL: {url} ...")
        try:
            docs = load_url(url)
            if docs:
                all_documents.extend(docs)
                successful_urls += 1
                print(f"  -> Thành công: Tải được {len(docs)} tài liệu.")
            else:
                failed_urls += 1
                print(f"  -> Thất bại: Không lấy được nội dung hoặc URL không hợp lệ.")
        except Exception as e:
            failed_urls += 1
            print(f"  -> Lỗi: {str(e)}")
            
    print("-" * 60)
    if not all_documents:
        print("Không có tài liệu nào được tải thành công. Hủy bỏ nạp dữ liệu.")
        sys.exit(1)
        
    print(f"Đang phân tách {len(all_documents)} tài liệu thành các chunk...")
    chunks = split_documents(all_documents)
    print(f"Tạo được tổng cộng {len(chunks)} chunks.")
    
    print("Đang nạp các chunk vào ChromaDB (bỏ qua trùng lặp)...")
    stats = add_documents(chunks)
    
    # Lấy tổng số lượng chunk hiện tại trong ChromaDB
    db_stats = get_stats()
    total_db_count = db_stats.get("count", 0)
    
    print("=" * 60)
    print("TỔNG KẾT QUÁ TRÌNH NẠP DỮ LIỆU:")
    print(f"- Tổng số URL:             {total_urls}")
    print(f"- URL tải thành công:     {successful_urls}")
    print(f"- URL tải thất bại:       {failed_urls}")
    print(f"- Chunks mới thêm vào DB:  {stats['added']}")
    print(f"- Chunks trùng lặp bỏ qua: {stats['skipped']}")
    print(f"- Chunks thất bại:        {stats['failed']}")
    print(f"- Tổng số chunks trong DB: {total_db_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
