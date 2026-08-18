"""
Safe image validation, magic bytes verification, and decompression-bomb protection.
"""

import io
import struct
from typing import Optional, Tuple, Dict, Any
from PIL import Image

# Register pillow-heif opener if available
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except Exception:
    HEIF_AVAILABLE = False

# Strict Decompression Bomb Guard (Max 100 MegaPixels / 100,000,000 pixels)
MAX_IMAGE_PIXELS = 100_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "GIF", "BMP", "TIFF", "HEIC", "HEIF", "AVIF"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/heic",
    "image/heif",
}


def detect_mime_from_magic(data: bytes) -> Optional[str]:
    """Detect actual MIME type from leading magic bytes."""
    if len(data) < 12:
        return None
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if data.startswith(b"BM"):
        return "image/bmp"
    if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
        return "image/tiff"
    # HEIC / HEIF / AVIF signatures in ftyp box (bytes 4-12)
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"heic", b"heix", b"heim", b"heis", b"mif1", b"msf1"):
            return "image/heic"
        if brand in (b"avif", b"avis"):
            return "image/avif"
    return None


class ImageValidationResult:
    def __init__(
        self,
        is_valid: bool,
        error: Optional[str] = None,
        format_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        width: int = 0,
        height: int = 0,
        file_size_bytes: int = 0,
        has_alpha: bool = False,
        dpi: Tuple[float, float] = (72.0, 72.0),
        mode: str = "",
    ):
        self.is_valid = is_valid
        self.error = error
        self.format_name = (format_name or "").upper()
        self.mime_type = mime_type or ""
        self.width = width
        self.height = height
        self.file_size_bytes = file_size_bytes
        self.has_alpha = has_alpha
        self.dpi = dpi
        self.mode = mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error": self.error,
            "format": self.format_name,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "file_size_bytes": self.file_size_bytes,
            "file_size_kb": round(self.file_size_bytes / 1024, 2),
            "file_size_mb": round(self.file_size_bytes / (1024 * 1024), 2),
            "has_alpha": self.has_alpha,
            "dpi_x": round(self.dpi[0], 1) if self.dpi else 72.0,
            "dpi_y": round(self.dpi[1], 1) if self.dpi else 72.0,
            "mode": self.mode,
        }


def validate_image_bytes(data: bytes, max_file_size: int = MAX_FILE_SIZE_BYTES) -> ImageValidationResult:
    """
    Strict validation of raw image bytes:
    - Check file size against limits
    - Check magic bytes
    - Attempt safe header decode with PIL without loading full payload into unconstrained RAM
    - Prevent decompression bomb / oversized image attack
    """
    if not data:
        return ImageValidationResult(is_valid=False, error="File is empty (0 bytes received).")

    size_bytes = len(data)
    if size_bytes > max_file_size:
        max_mb = max_file_size / (1024 * 1024)
        actual_mb = round(size_bytes / (1024 * 1024), 2)
        return ImageValidationResult(
            is_valid=False,
            error=f"File exceeds maximum allowed upload size of {max_mb:.0f} MB (received {actual_mb} MB).",
            file_size_bytes=size_bytes,
        )

    magic_mime = detect_mime_from_magic(data)

    try:
        stream = io.BytesIO(data)
        with Image.open(stream) as img:
            # Check dimensions against decompression bomb threshold
            w, h = img.size
            if w <= 0 or h <= 0:
                return ImageValidationResult(is_valid=False, error="Invalid image dimensions (0x0).")

            pixels = w * h
            if pixels > MAX_IMAGE_PIXELS:
                return ImageValidationResult(
                    is_valid=False,
                    error=f"Decompression bomb safety limit exceeded ({w}x{h} = {pixels:,} px > {MAX_IMAGE_PIXELS:,} px limit).",
                    width=w,
                    height=h,
                    file_size_bytes=size_bytes,
                )

            fmt = (img.format or "").upper()
            if not fmt:
                if magic_mime == "image/heic":
                    fmt = "HEIC"
                elif magic_mime == "image/jpeg":
                    fmt = "JPEG"
                elif magic_mime == "image/png":
                    fmt = "PNG"
                elif magic_mime == "image/webp":
                    fmt = "WEBP"
                else:
                    fmt = "UNKNOWN"

            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)

            # DPI extraction
            dpi_val = img.info.get("dpi", (72.0, 72.0))
            if not isinstance(dpi_val, (tuple, list)) or len(dpi_val) < 2:
                dpi_val = (72.0, 72.0)
            else:
                try:
                    dpi_val = (float(dpi_val[0]), float(dpi_val[1]))
                except Exception:
                    dpi_val = (72.0, 72.0)

            mime = magic_mime or f"image/{fmt.lower()}"

            return ImageValidationResult(
                is_valid=True,
                format_name=fmt,
                mime_type=mime,
                width=w,
                height=h,
                file_size_bytes=size_bytes,
                has_alpha=has_alpha,
                dpi=dpi_val,
                mode=img.mode,
            )

    except Image.DecompressionBombError as e:
        return ImageValidationResult(
            is_valid=False,
            error=f"Decompression bomb detected: image exceeds maximum pixel boundary ({e}).",
            file_size_bytes=size_bytes,
        )
    except Exception as e:
        return ImageValidationResult(
            is_valid=False,
            error=f"Malformed or unsupported image file: {str(e)}",
            file_size_bytes=size_bytes,
        )
