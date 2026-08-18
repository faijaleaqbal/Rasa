"""
Production-hardened asynchronous REST API Server for Alya Image Tools using aiohttp.
Features bounded concurrency, token-bucket rate limiting, structured observability,
request ID tracking, and strict error masking.
"""

import io
import time
import uuid
import json
import asyncio
import logging
from aiohttp import web
from typing import Dict, Any

from .validator import validate_image_bytes
from .pipeline import process_image_pipeline
from .batch import process_batch_pipeline
from .presets import preset_registry
from .security import ephemeral_store, rate_limiter
from .metadata_dpi import extract_exif_metadata, calculate_physical_dimensions
from PIL import Image

logger = logging.getLogger(__name__)

# Bounded Concurrency Semaphore for CPU-heavy processing
PROCESSING_SEMAPHORE = asyncio.Semaphore(12)


@web.middleware
async def cors_and_security_middleware(request: web.Request, handler):
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request["req_id"] = req_id
    start_time = time.time()

    # Handle preflight OPTIONS
    if request.method == "OPTIONS":
        response = web.Response(status=204)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-Request-ID"
        response.headers["X-Request-ID"] = req_id
        return response

    client_ip = request.remote or "127.0.0.1"

    # Rate-limiting check (exempt downloads from harsh limits)
    if not request.path.startswith("/api/image/download"):
        if not rate_limiter.allow_request(client_ip):
            logger.warning(f"[{req_id}] Rate limit exceeded for IP {client_ip}")
            return web.json_response(
                {"error": "Too many requests. Please slow down.", "success": False, "request_id": req_id},
                status=429,
                headers={"Access-Control-Allow-Origin": "*", "X-Request-ID": req_id}
            )

    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex
    except Exception as e:
        logger.error(f"[{req_id}] Unhandled error handling {request.path}: {e}", exc_info=True)
        response = web.json_response(
            {"error": "An internal error occurred while processing the image.", "success": False, "request_id": req_id},
            status=500
        )

    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)

    return response


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "healthy",
        "service": "Alya Image Tools Processing Engine",
        "version": "3.1.0",
        "presets_count": len(preset_registry.list_all()),
        "ephemeral_items": len(ephemeral_store._items),
    })


async def handle_get_presets(request: web.Request) -> web.Response:
    return web.json_response({
        "presets": preset_registry.list_all(),
        "categories": preset_registry.list_by_category(),
    })


async def handle_extract_metadata(request: web.Request) -> web.Response:
    req_id = request.get("req_id", "unknown")
    reader = await request.multipart()
    file_bytes = None
    filename = "uploaded_image"

    while True:
        field = await reader.next()
        if field is None:
            break
        if field.name in ("file", "image"):
            filename = field.filename or "image.jpg"
            file_bytes = await field.read()
            break

    if not file_bytes:
        return web.json_response({"success": False, "error": "No image file provided in request.", "request_id": req_id}, status=400)

    val_res = validate_image_bytes(file_bytes)
    if not val_res.is_valid:
        return web.json_response({"success": False, "error": val_res.error, "request_id": req_id}, status=400)

    try:
        stream = io.BytesIO(file_bytes)
        with Image.open(stream) as img:
            exif = extract_exif_metadata(img)
            dpi_val = val_res.dpi[0] if val_res.dpi else 72.0
            print_dims = calculate_physical_dimensions(val_res.width, val_res.height, dpi_val)

            return web.json_response({
                "success": True,
                "filename": filename,
                "basic": val_res.to_dict(),
                "print_dimensions": print_dims,
                "exif": exif,
                "request_id": req_id,
            })
    except Exception as e:
        logger.error(f"[{req_id}] Metadata extraction failure: {e}")
        return web.json_response({"success": False, "error": "Failed to parse image metadata.", "request_id": req_id}, status=500)


async def handle_process_image(request: web.Request) -> web.Response:
    req_id = request.get("req_id", "unknown")
    reader = await request.multipart()
    file_bytes = None
    filename = "image.jpg"
    options: Dict[str, Any] = {}

    while True:
        field = await reader.next()
        if field is None:
            break

        if field.name in ("file", "image"):
            filename = field.filename or "image.jpg"
            file_bytes = await field.read()
        elif field.name == "options":
            opt_text = await field.text()
            try:
                options = json.loads(opt_text)
            except Exception:
                options = {}
        else:
            val = await field.text()
            try:
                if val.lower() == "true":
                    options[field.name] = True
                elif val.lower() == "false":
                    options[field.name] = False
                elif val.isdigit():
                    options[field.name] = int(val)
                else:
                    try:
                        options[field.name] = float(val)
                    except ValueError:
                        options[field.name] = val
            except Exception:
                options[field.name] = val

    if not file_bytes:
        return web.json_response({"success": False, "error": "No image file provided in upload.", "request_id": req_id}, status=400)

    # Process through pipeline within concurrency semaphore
    async with PROCESSING_SEMAPHORE:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: process_image_pipeline(image_bytes=file_bytes, filename=filename, **options)
        )

    if not result.get("success"):
        result["request_id"] = req_id
        return web.json_response(result, status=400)

    token = result["token"]
    result["request_id"] = req_id
    result["download_url"] = f"/api/image/download/{token}"
    result["preview_url"] = f"/api/image/preview/{token}"

    m = result.get("metrics", {})
    logger.info(
        f"[{req_id}] Processed {filename} -> {result.get('filename')} | "
        f"In: {m.get('original_size_kb')} KB ({m.get('original_dimensions')}) | "
        f"Out: {m.get('final_size_kb')} KB ({m.get('final_dimensions')}) | "
        f"Reduction: {m.get('percentage_reduction')}%"
    )

    return web.json_response(result)


async def handle_batch_process(request: web.Request) -> web.Response:
    req_id = request.get("req_id", "unknown")
    reader = await request.multipart()
    items = []
    options: Dict[str, Any] = {}

    while True:
        field = await reader.next()
        if field is None:
            break

        if field.name in ("files", "images", "file"):
            fn = field.filename or f"image_{len(items)+1}.jpg"
            fb = await field.read()
            if fb:
                items.append((fb, fn))
        elif field.name == "options":
            opt_text = await field.text()
            try:
                options = json.loads(opt_text)
            except Exception:
                options = {}
        else:
            val = await field.text()
            try:
                if val.lower() == "true":
                    options[field.name] = True
                elif val.lower() == "false":
                    options[field.name] = False
                elif val.isdigit():
                    options[field.name] = int(val)
                else:
                    try:
                        options[field.name] = float(val)
                    except ValueError:
                        options[field.name] = val
            except Exception:
                options[field.name] = val

    if not items:
        return web.json_response({"success": False, "error": "No files provided in batch upload.", "request_id": req_id}, status=400)

    async with PROCESSING_SEMAPHORE:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: process_batch_pipeline(items=items, options=options)
        )

    result["request_id"] = req_id

    # Attach URLs to individual items
    for item in result.get("results", []):
        if item.get("token"):
            t = item["token"]
            item["download_url"] = f"/api/image/download/{t}"
            item["preview_url"] = f"/api/image/preview/{t}"

    if result.get("zip_token"):
        zt = result["zip_token"]
        result["zip_download_url"] = f"/api/image/download-zip/{zt}"

    logger.info(f"[{req_id}] Batch processed {result.get('total')} items ({result.get('successful')} ok, {result.get('failed')} failed)")
    return web.json_response(result)


async def handle_download_file(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    item = ephemeral_store.get(token)
    if not item:
        return web.Response(text="Requested file not found or has expired.", status=404)

    headers = {
        "Content-Type": item.mime_type,
        "Content-Disposition": f'attachment; filename="{item.filename}"',
        "Content-Length": str(len(item.data)),
        "Cache-Control": "no-store, no-cache, must-revalidate",
    }
    return web.Response(body=item.data, headers=headers)


async def handle_preview_file(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    item = ephemeral_store.get(token)
    if not item:
        return web.Response(text="Requested preview image not found or has expired.", status=404)

    headers = {
        "Content-Type": item.mime_type,
        "Content-Disposition": f'inline; filename="{item.filename}"',
        "Content-Length": str(len(item.data)),
        "Cache-Control": "public, max-age=3600",
    }
    return web.Response(body=item.data, headers=headers)


async def handle_download_zip(request: web.Request) -> web.Response:
    token = request.match_info.get("token", "")
    item = ephemeral_store.get(token)
    if not item:
        return web.Response(text="Requested ZIP archive not found or has expired.", status=404)

    headers = {
        "Content-Type": "application/zip",
        "Content-Disposition": f'attachment; filename="{item.filename}"',
        "Content-Length": str(len(item.data)),
        "Cache-Control": "no-store, no-cache, must-revalidate",
    }
    return web.Response(body=item.data, headers=headers)


def create_image_tools_app() -> web.Application:
    """Initializes and returns the configured aiohttp web application."""
    app = web.Application(middlewares=[cors_and_security_middleware], client_max_size=60 * 1024 * 1024)

    app.router.add_get("/api/image/health", handle_health)
    app.router.add_get("/api/image/presets", handle_get_presets)
    app.router.add_post("/api/image/metadata", handle_extract_metadata)
    app.router.add_post("/api/image/process", handle_process_image)
    app.router.add_post("/api/image/batch", handle_batch_process)
    app.router.add_get("/api/image/download/{token}", handle_download_file)
    app.router.add_get("/api/image/preview/{token}", handle_preview_file)
    app.router.add_get("/api/image/download-zip/{token}", handle_download_zip)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    app = create_image_tools_app()
    web.run_app(app, host="0.0.0.0", port=5050)
