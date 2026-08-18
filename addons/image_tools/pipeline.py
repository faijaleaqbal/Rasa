"""
Modular Image Processing Pipeline:
upload -> validate -> decode -> crop/rotate/flip -> resize -> enhance -> watermark -> compress/convert -> metadata/DPI -> output validation
"""

import io
import logging
from typing import Optional, Dict, Any, Tuple, Union
from PIL import Image, ImageOps

from .validator import validate_image_bytes, ImageValidationResult
from .cropper import crop_image, rotate_and_flip_image
from .resizer import resize_image
from .converter import normalize_image_mode, get_mime_for_format, get_extension_for_format
from .compressor import compress_to_target_size, compress_by_quality, CompressionResult
from .enhancement import enhance_image
from .metadata_dpi import extract_exif_metadata, get_image_dpi
from .watermark import apply_text_watermark, apply_privacy_blur_or_pixelate
from .presets import preset_registry
from .security import ephemeral_store

logger = logging.getLogger(__name__)


def process_image_pipeline(
    image_bytes: bytes,
    filename: str = "image.jpg",
    # Presets
    preset_id: Optional[str] = None,
    # Crop & Transform
    crop_x: Optional[int] = None,
    crop_y: Optional[int] = None,
    crop_width: Optional[int] = None,
    crop_height: Optional[int] = None,
    crop_aspect_ratio: Optional[str] = None,
    crop_shape: str = "rect",  # "rect", "square", "circle"
    rotation_angle: float = 0.0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    # Resize
    target_width: Optional[float] = None,
    target_height: Optional[float] = None,
    unit: str = "px",
    maintain_aspect: bool = True,
    resample_filter: str = "lanczos",
    scale_mode: str = "fit",
    # DPI
    dpi: Optional[float] = None,
    # Enhancement
    auto_contrast: bool = False,
    brightness: float = 1.0,
    contrast: float = 1.0,
    sharpness: float = 1.0,
    color_balance: float = 1.0,
    denoise: bool = False,
    upscale_factor: float = 1.0,
    # Watermark & Redact
    watermark_text: Optional[str] = None,
    watermark_opacity: float = 0.5,
    watermark_position: str = "bottom-right",
    privacy_blur_box: Optional[Tuple[int, int, int, int]] = None,
    privacy_effect: str = "blur",  # "blur" or "pixelate"
    # Format & Compression
    output_format: Optional[str] = None,
    quality: Optional[int] = None,
    target_size_kb: Optional[float] = None,
    matte_color: str = "#FFFFFF",
    # Metadata
    strip_metadata: bool = True,
) -> Dict[str, Any]:
    """
    Executes the comprehensive image pipeline and returns full metadata, metrics, and ephemeral download token.
    """
    # 1. Validate Upload
    val_res = validate_image_bytes(image_bytes)
    if not val_res.is_valid:
        return {
            "success": False,
            "error": val_res.error or "Invalid image file.",
            "metrics": val_res.to_dict(),
        }

    original_size_bytes = len(image_bytes)

    # Apply preset overrides if specified
    if preset_id:
        p = preset_registry.get(preset_id)
        if p:
            if target_width is None and target_height is None:
                target_width = float(p.width)
                target_height = float(p.height)
                unit = p.unit
                maintain_aspect = p.maintain_aspect
            if dpi is None and p.dpi:
                dpi = float(p.dpi)
            if output_format is None and p.format:
                output_format = p.format
            if target_size_kb is None and p.max_size_kb:
                target_size_kb = float(p.max_size_kb)
            if crop_aspect_ratio is None and p.aspect_ratio:
                crop_aspect_ratio = p.aspect_ratio

    # Determine output format
    if output_format:
        fmt = output_format.upper().replace("JPG", "JPEG")
    else:
        fmt = val_res.format_name if val_res.format_name in ("JPEG", "PNG", "WEBP") else "JPEG"

    # 2. Decode safely with EXIF orientation correction
    try:
        stream = io.BytesIO(image_bytes)
        img = Image.open(stream)
        # Transpose according to EXIF orientation
        img = ImageOps.exif_transpose(img) or img
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to decode image data: {str(e)}",
        }

    orig_w, orig_h = img.size
    exif_info = extract_exif_metadata(img)
    orig_dpi = val_res.dpi

    # Target DPI
    target_dpi_tuple = (float(dpi), float(dpi)) if dpi is not None else orig_dpi

    # 3. Crop, Rotate & Flip
    if rotation_angle != 0.0 or flip_horizontal or flip_vertical:
        img = rotate_and_flip_image(
            img,
            rotation_angle=rotation_angle,
            flip_horizontal=flip_horizontal,
            flip_vertical=flip_vertical,
        )

    if (
        crop_x is not None
        or crop_y is not None
        or crop_width is not None
        or crop_height is not None
        or crop_aspect_ratio is not None
        or crop_shape in ("square", "circle")
    ):
        img = crop_image(
            img,
            x=crop_x,
            y=crop_y,
            width=crop_width,
            height=crop_height,
            aspect_ratio=crop_aspect_ratio,
            shape=crop_shape,
        )

    # 4. Resize
    if target_width is not None or target_height is not None:
        img = resize_image(
            img,
            target_width=target_width,
            target_height=target_height,
            unit=unit,
            dpi=target_dpi_tuple[0],
            maintain_aspect=maintain_aspect,
            resample_filter=resample_filter,
            scale_mode=scale_mode,
        )

    # 5. Enhancement
    if (
        auto_contrast
        or brightness != 1.0
        or contrast != 1.0
        or sharpness != 1.0
        or color_balance != 1.0
        or denoise
        or upscale_factor > 1.0
    ):
        img = enhance_image(
            img,
            auto_contrast=auto_contrast,
            brightness=brightness,
            contrast=contrast,
            sharpness=sharpness,
            color_balance=color_balance,
            denoise=denoise,
            upscale_factor=upscale_factor,
        )

    # 6. Watermark & Privacy Redaction
    if privacy_blur_box is not None:
        img = apply_privacy_blur_or_pixelate(img, box=privacy_blur_box, effect=privacy_effect)

    if watermark_text:
        img = apply_text_watermark(
            img,
            text=watermark_text,
            opacity=watermark_opacity,
            position=watermark_position,
        )

    # 7. Compression & Format Encoding
    comp_res: CompressionResult
    target_bytes = int(target_size_kb * 1024) if target_size_kb is not None and target_size_kb > 0 else None

    if target_bytes is not None:
        comp_res = compress_to_target_size(
            img=img,
            target_size_bytes=target_bytes,
            original_size_bytes=original_size_bytes,
            format_name=fmt,
            dpi=target_dpi_tuple,
        )
    else:
        use_quality = quality if (quality is not None and 1 <= quality <= 100) else 85
        comp_res = compress_by_quality(
            img=img,
            original_size_bytes=original_size_bytes,
            quality=use_quality,
            format_name=fmt,
            dpi=target_dpi_tuple,
        )

    # 8. Output Validation
    out_val = validate_image_bytes(comp_res.data)
    if not out_val.is_valid:
        return {
            "success": False,
            "error": f"Output validation failed: {out_val.error}",
        }

    # 9. Ephemeral Tokenized Storage for Download
    base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    ext = get_extension_for_format(fmt)
    output_filename = f"{base_name}_alya_processed{ext}"
    mime = get_mime_for_format(fmt)
    download_token = ephemeral_store.put(comp_res.data, output_filename, mime)

    return {
        "success": True,
        "token": download_token,
        "filename": output_filename,
        "mime_type": mime,
        "metrics": {
            "original_size_bytes": original_size_bytes,
            "original_size_kb": round(original_size_bytes / 1024, 2),
            "original_size_mb": round(original_size_bytes / (1024 * 1024), 2),
            "final_size_bytes": comp_res.final_size_bytes,
            "final_size_kb": round(comp_res.final_size_bytes / 1024, 2),
            "final_size_mb": round(comp_res.final_size_bytes / (1024 * 1024), 2),
            "percentage_reduction": comp_res.percentage_reduction,
            "original_dimensions": [orig_w, orig_h],
            "final_dimensions": [comp_res.final_width, comp_res.final_height],
            "original_format": val_res.format_name,
            "output_format": comp_res.format_name,
            "dpi": [round(target_dpi_tuple[0], 1), round(target_dpi_tuple[1], 1)],
            "quality_used": comp_res.quality_used,
            "warning": comp_res.warning,
        },
        "exif": exif_info if not strip_metadata else None,
    }
