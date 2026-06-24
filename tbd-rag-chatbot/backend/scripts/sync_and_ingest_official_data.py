# -*- coding: utf-8 -*-
"""
Script đồng bộ hóa dữ liệu từ Website chính thức của TBD, nạp curated FAQ,
sau đó phân tách thành các chunks và nạp đè (rebuild) vào cơ sở dữ liệu vector ChromaDB.
"""

import sys
import os
import json
from pathlib import Path

# Đưa thư mục backend vào sys.path để import được app
backend_path = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_path))

from app.config import initialize_directories, settings
from app.services.website_sync_service import website_sync_service
from app.chunker import split_documents
from app.vector_store import add_documents, get_collection
from app.document_loader import SUPPORTED_EXTENSIONS, load_file

def main():
    # Cấu hình UTF-8 cho stdout trên console Windows
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("==================================================")
    print("Bắt đầu đồng bộ và nạp dữ liệu TBD University...")
    print("==================================================")
    
    # 1. Khởi tạo các thư mục
    initialize_directories()
    
    # 2. Đồng bộ website seed URLs
    print("\n[Bước 1/4] Đồng bộ các trang web hạt giống chính thức...")
    sync_summary = website_sync_service.sync_seed_urls()
    print("Tổng số URL hạt giống:", sync_summary.get("total_urls"))
    print("Thành công:", sync_summary.get("successful_urls"))
    print("Thất bại:", sync_summary.get("failed_urls"))
    print("File snapshot:", sync_summary.get("snapshot_file"))
    
    # 3. Thu thập tài liệu từ nguồn cục bộ
    print("\n[Bước 2/4] Thu thập tài liệu từ các nguồn cục bộ...")
    all_documents = []
    
    # Đọc các trang web đã đồng bộ
    try:
        web_pages = website_sync_service.load_local_web_pages()
        all_documents.extend(web_pages)
        print(f"- Đã thu thập {len(web_pages)} trang web cục bộ.")
    except Exception as e:
        print(f"- Lỗi khi đọc trang web cục bộ: {str(e)}")
        
    # Đọc tất cả file curated FAQ trong thư mục FAQ
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
                print(f"- Đã thu thập {len(faqs)} câu hỏi FAQ từ '{faq_file.name}'.")
            except Exception as e:
                print(f"- Lỗi khi đọc tệp FAQ '{faq_file.name}': {str(e)}")
        print(f"- Tổng số câu hỏi FAQ đã thu thập: {faq_count}")
    else:
        print("- Cảnh báo: Không tìm thấy thư mục FAQ")
        
    # Đọc files upload
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
                    print(f"- Lỗi khi đọc tệp tin đã tải lên '{file_path.name}': {str(e)}")
        print(f"- Đã thu thập {file_count} tệp tin đã tải lên.")

    if not all_documents:
        print("\nKhông có tài liệu nào được thu thập. Quá trình nạp dừng lại.")
        return
        
    # 4. Phân tách tài liệu thành chunks
    print("\n[Bước 3/4] Phân tách tài liệu thành các phân mảnh (chunks)...")
    chunks = split_documents(all_documents)
    print(f"Tổng số phân mảnh tạo ra: {len(chunks)}")
    
    # 5. Nạp vào ChromaDB (Rebuild mode)
    print("\n[Bước 4/4] Nạp dữ liệu vào ChromaDB (chế độ tăng cường)...")
    stats = add_documents(chunks, rebuild=False)
    print("Kết quả nạp:")
    print("  - Đã thêm mới:", stats.get("added"))
    print("  - Đã bỏ qua (trùng):", stats.get("skipped"))
    print("  - Thất bại:", stats.get("failed"))
    
    # 6. Kiểm tra lại cơ sở dữ liệu
    col = get_collection()
    print("\n==================================================")
    print("Hoàn tất nạp dữ liệu!")
    print(f"Tổng số bản ghi trong ChromaDB hiện tại: {col.count()}")
    print("==================================================")

if __name__ == "__main__":
    main()
