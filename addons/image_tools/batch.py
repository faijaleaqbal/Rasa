"""
Bulk batch processor for multiple images with ZIP archive packaging, payload limits, and per-file error isolation.
"""

import io
import os
import zipfile
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple

from .pipeline import process_image_pipeline
from .security import ephemeral_store

logger = logging.getLogger(__name__)

MAX_BATCH_FILES = 50
MAX_BATCH_TOTAL_BYTES = 100 * 1024 * 1024  # 100 MB


def sanitize_zip_entry_name(name: str) -> str:
    """Sanitizes filename inside ZIP to prevent directory traversal / Zip Slip attacks."""
    base = os.path.basename(name).replace("/", "_").replace("\\", "_")
    clean = "".join(c for c in base if c.isalnum() or c in "._- ")
    return clean.strip() or "image_output.jpg"


def process_single_batch_item(item_data: Tuple[bytes, str, Dict[str, Any]]) -> Dict[str, Any]:
    file_bytes, filename, options = item_data
    clean_filename = sanitize_zip_entry_name(filename)
    try:
        res = process_image_pipeline(
            image_bytes=file_bytes,
            filename=clean_filename,
            **options
        )
        res["source_filename"] = clean_filename
        return res
    except Exception as e:
        logger.error(f"Error in batch item {clean_filename}: {e}", exc_info=True)
        return {
            "success": False,
            "source_filename": clean_filename,
            "error": "Failed to process image.",
        }


def process_batch_pipeline(
    items: List[Tuple[bytes, str]],  # [(data, filename), ...]
    options: Dict[str, Any],
    max_workers: int = 4,
) -> Dict[str, Any]:
    """
    Executes parallel batch processing over multiple images and compiles a ZIP archive.
    Enforces maximum batch count (50 files) and total upload payload limits (100 MB).
    """
    if not items:
        return {
            "success": False,
            "error": "No files provided for batch processing.",
            "total": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "zip_token": None,
        }

    if len(items) > MAX_BATCH_FILES:
        return {
            "success": False,
            "error": f"Batch limit exceeded: Maximum {MAX_BATCH_FILES} files allowed per batch (received {len(items)}).",
            "total": len(items),
            "successful": 0,
            "failed": len(items),
            "results": [],
            "zip_token": None,
        }

    total_bytes = sum(len(data) for data, _ in items)
    if total_bytes > MAX_BATCH_TOTAL_BYTES:
        max_mb = MAX_BATCH_TOTAL_BYTES / (1024 * 1024)
        received_mb = round(total_bytes / (1024 * 1024), 2)
        return {
            "success": False,
            "error": f"Batch size limit exceeded: Maximum {max_mb:.0f} MB total allowed (received {received_mb} MB).",
            "total": len(items),
            "successful": 0,
            "failed": len(items),
            "results": [],
            "zip_token": None,
        }

    task_items = [(data, name, options) for data, name in items]
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(process_single_batch_item, task_items):
            results.append(result)

    successful_results = [r for r in results if r.get("success")]
    failed_count = len(results) - len(successful_results)

    # Package successful files into ZIP
    zip_token = None
    if successful_results:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            used_names = set()
            for r in successful_results:
                token = r.get("token")
                if not token:
                    continue
                store_item = ephemeral_store.get(token)
                if store_item:
                    name = sanitize_zip_entry_name(store_item.filename)
                    # Handle duplicate filenames inside zip
                    if name in used_names:
                        parts = name.rsplit(".", 1)
                        name = f"{parts[0]}_{token[:6]}.{parts[1]}" if len(parts) > 1 else f"{name}_{token[:6]}"
                    used_names.add(name)
                    zip_file.writestr(name, store_item.data)

        zip_bytes = zip_buffer.getvalue()
        zip_token = ephemeral_store.put(zip_bytes, "alya_processed_images.zip", "application/zip")

    return {
        "success": len(successful_results) > 0,
        "total": len(items),
        "successful": len(successful_results),
        "failed": failed_count,
        "results": results,
        "zip_token": zip_token,
    }
