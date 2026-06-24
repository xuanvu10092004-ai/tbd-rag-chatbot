# -*- coding: utf-8 -*-
"""
Dịch vụ đồng bộ hóa nội dung website TBD về các file cục bộ (local-first RAG).
Lưu trữ định dạng JSON và Markdown để làm nguồn dữ liệu gốc (source of truth).
Cập nhật sync_manifest.json sau mỗi lần đồng bộ.
"""

import os
import re
import json
import logging
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path
import requests

from app.config import settings
from app.seed_urls import SEED_URLS
from app.document_loader import load_url, _is_allowed_url

logger = logging.getLogger(__name__)

def get_url_slug(url: str) -> str:
    """Tạo slug an toàn từ URL để làm tên file."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        slug = "index"
    else:
        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", path)
    if "tuyensinh" in parsed.netloc:
        slug = f"tuyensinh_{slug}"
    return slug

class WebsiteSyncService:
    """
    Dịch vụ quản lý việc tải và lưu trữ dữ liệu website cục bộ dạng JSON/MD.
    Duy trì sync_manifest.json làm nhật ký đồng bộ.
    """

    def __init__(self):
        # Đảm bảo các thư mục dữ liệu tồn tại
        settings.web_pages_dir_path.mkdir(parents=True, exist_ok=True)
        settings.processed_dir_path.mkdir(parents=True, exist_ok=True)
        settings.snapshots_dir_path.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> dict[str, dict]:
        """Đọc file manifest từ đĩa. Trả về dict {url: record}."""
        path = settings.sync_manifest_path
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Đảm bảo trả về định dạng dict
                if isinstance(data, list):
                    return {item["url"]: item for item in data}
                return data
        except Exception as e:
            logger.error("Không thể đọc sync_manifest.json: %s. Trả về rỗng.", str(e))
            return {}

    def _save_manifest(self, manifest: dict[str, dict]) -> None:
        """Ghi manifest xuống đĩa dưới dạng list JSON."""
        path = settings.sync_manifest_path
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(list(manifest.values()), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Không thể ghi sync_manifest.json: %s", str(e))

    def sync_single_url(self, url: str) -> dict:
        """
        Đồng bộ hóa 1 URL đơn lẻ về dữ liệu cục bộ.
        """
        url = url.strip()
        if not _is_allowed_url(url):
            error_msg = f"URL ngoài tên miền được phép: {url}"
            logger.warning(error_msg)
            return {"url": url, "status": "failed", "error": error_msg}

        manifest = self._load_manifest()
        record = {
            "url": url,
            "title": "",
            "status": "failed",
            "local_json": None,
            "local_markdown": None,
            "last_fetched_at": None,
            "content_hash": None,
            "error": None
        }

        try:
            logger.info("Đang đồng bộ URL đơn lẻ: %s", url)
            
            # Sử dụng document_loader.load_url để fetch trang web và định dạng bảng biểu/tiêu đề
            docs = load_url(url)
            if not docs:
                raise ValueError("Không thể tải trang hoặc nội dung trang rỗng/quá ngắn")

            doc = docs[0]
            title = doc["title"]
            content = doc["content"]
            
            # Tính mã băm nội dung để so khớp thay đổi
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            slug = get_url_slug(url)
            
            # Đường dẫn lưu file
            json_filename = f"{slug}.json"
            md_filename = f"{slug}.md"
            
            json_path = settings.web_pages_dir_path / json_filename
            md_path = settings.web_pages_dir_path / md_filename
            
            fetched_at = datetime.now(timezone.utc).isoformat()
            
            # 1. Trích xuất headings, tables và links để lưu vào JSON cấu trúc
            # Chạy BeautifulSoup lần nữa để phân tách các thành phần chuyên biệt cho JSON
            from bs4 import BeautifulSoup
            # Chúng ta fetch lại để lấy DOM sạch trước khi trích xuất
            headers = {
                "User-Agent": "TBD-RAG-Bot/1.0",
                "Accept-Language": "vi,en;q=0.9",
            }
            response = requests.get(url, headers=headers, timeout=settings.URL_REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Xóa tags rác
            for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                tag.decompose()
                
            main_content = (
                soup.find("main") or soup.find("article") or soup.find("body") or soup
            )
            
            headings = [h.get_text(strip=True) for h in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]) if h.get_text(strip=True)]
            
            tables = []
            for idx, table in enumerate(main_content.find_all("table")):
                caption_tag = table.find("caption")
                caption = caption_tag.get_text(strip=True) if caption_tag else f"Bảng {idx+1}"
                rows = []
                for row in table.find_all("tr"):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if cells:
                        rows.append(cells)
                tables.append({"caption": caption, "rows": rows})
                
            links = []
            for a in main_content.find_all("a", href=True):
                a_text = a.get_text(strip=True)
                a_href = a["href"].strip()
                # Chỉ lưu liên kết hợp lệ
                if a_text and a_href.startswith(("http", "/")):
                    # Chuyển đổi tương đối thành tuyệt đối nếu cần
                    if a_href.startswith("/"):
                        parsed_base = urlparse(url)
                        a_href = f"{parsed_base.scheme}://{parsed_base.netloc}{a_href}"
                    links.append({"text": a_text, "url": a_href})
            
            # 2. Tạo và lưu file JSON cục bộ
            page_data = {
                "title": title,
                "url": url,
                "source_type": "official_website",
                "fetched_at": fetched_at,
                "content_text": content,
                "headings": headings,
                "tables": tables,
                "links": links,
                "content_hash": content_hash
            }
            
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)
                
            # 3. Tạo và lưu file Markdown cục bộ (debug/readable)
            markdown_content = f"# {title}\n\n"
            markdown_content += f"Source: {url}\n"
            markdown_content += f"Fetched at: {fetched_at}\n\n"
            markdown_content += content
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            # Cập nhật record manifest
            record.update({
                "title": title,
                "status": "success",
                "local_json": str(json_path.relative_to(settings.backend_root)),
                "local_markdown": str(md_path.relative_to(settings.backend_root)),
                "last_fetched_at": fetched_at,
                "content_hash": content_hash,
                "error": None
            })
            logger.info("Đã đồng bộ thành công URL: %s -> %s", url, json_filename)
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Lỗi khi đồng bộ URL %s: %s", url, error_msg)
            record.update({
                "status": "failed",
                "error": error_msg
            })
            
        manifest[url] = record
        self._save_manifest(manifest)
        return record

    def sync_seed_urls(self) -> dict:
        """
        Đồng bộ hóa toàn bộ danh sách SEED_URLS hạt giống.
        Tạo một file snapshot gộp lưu trong snapshots/.
        """
        logger.info("Bắt đầu đồng bộ danh sách SEED_URLS hạt giống...")
        total_urls = len(SEED_URLS)
        successful_urls = 0
        failed_urls = 0
        results = []
        
        for url in SEED_URLS:
            res = self.sync_single_url(url)
            results.append(res)
            if res["status"] == "success":
                successful_urls += 1
            else:
                failed_urls += 1
                
        # Tạo snapshot gộp toàn bộ trang thành công
        snapshot_data = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_pages": successful_urls,
            "pages": []
        }
        
        # Load lại tất cả JSON thành công để cho vào snapshot
        for res in results:
            if res["status"] == "success" and res["local_json"]:
                try:
                    json_abs_path = settings.backend_root / res["local_json"]
                    with open(json_abs_path, "r", encoding="utf-8") as f:
                        page_data = json.load(f)
                        snapshot_data["pages"].append(page_data)
                except Exception as e:
                    logger.error("Không thể đọc file để tạo snapshot: %s", str(e))
                    
        # Lưu file snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"tbd_website_snapshot_{timestamp}.json"
        snapshot_path = settings.snapshots_dir_path / snapshot_filename
        
        try:
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
            logger.info("Đã tạo file snapshot website: %s", snapshot_filename)
        except Exception as e:
            logger.error("Lỗi khi ghi file snapshot website: %s", str(e))
            
        summary = {
            "total_urls": total_urls,
            "successful_urls": successful_urls,
            "failed_urls": failed_urls,
            "snapshot_file": str(snapshot_path.relative_to(settings.backend_root)) if successful_urls > 0 else None
        }
        logger.info("Đồng bộ seed URLs hoàn tất: %s", summary)
        return summary

    def load_local_web_pages(self) -> list[dict]:
        """
        Đọc tất cả các file JSON cục bộ từ web_pages.
        Trả về danh sách tài liệu phục vụ RAG.
        """
        documents = []
        path = settings.web_pages_dir_path
        
        if not path.exists():
            return []
            
        for file_path in path.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    page_data = json.load(f)
                    # Chuyển đổi sang format document cho chunker
                    documents.append({
                        "content": page_data["content_text"],
                        "source": page_data["url"],
                        "source_type": "official_website",
                        "title": page_data["title"],
                        "fetched_at": page_data["fetched_at"],
                        "content_hash": page_data["content_hash"],
                        "local_path": str(file_path.relative_to(settings.backend_root))
                    })
            except Exception as e:
                logger.error("Lỗi khi đọc file JSON cục bộ '%s': %s", file_path.name, str(e))
                
        return documents

    def get_sync_status(self) -> dict:
        """
        Trả về thông tin trạng thái đồng bộ hóa hiện tại của hệ thống.
        """
        manifest = self._load_manifest()
        
        total_pages = 0
        total_size = 0
        last_sync = None
        failed_urls = []
        
        for url, record in manifest.items():
            if record["status"] == "success":
                total_pages += 1
                # Tính kích thước file JSON
                if record["local_json"]:
                    json_abs_path = settings.backend_root / record["local_json"]
                    if json_abs_path.exists():
                        total_size += json_abs_path.stat().st_size
                
                # Tìm thời điểm đồng bộ gần nhất
                if record["last_fetched_at"]:
                    dt = record["last_fetched_at"]
                    if not last_sync or dt > last_sync:
                        last_sync = dt
            else:
                failed_urls.append({"url": url, "error": record.get("error", "Lỗi không xác định")})
                
        return {
            "total_pages": total_pages,
            "last_sync_time": last_sync,
            "total_content_size_bytes": total_size,
            "failed_urls": failed_urls,
            "total_monitored_urls": len(manifest)
        }

# Singleton instance
website_sync_service = WebsiteSyncService()
