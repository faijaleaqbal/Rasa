"""
High-quality image resizing with unit conversions (px, cm, mm, in) and aspect-ratio preservation.
"""

from typing import Optional, Tuple, Union
from PIL import Image

RESAMPLING_FILTERS = {
    "lanczos": Image.Resampling.LANCZOS,
    "bicubic": Image.Resampling.BICUBIC,
    "bilinear": Image.Resampling.BILINEAR,
    "box": Image.Resampling.BOX,
    "nearest": Image.Resampling.NEAREST,
}


def unit_to_pixels(val: float, unit: str, dpi: float = 300.0) -> int:
    """
    Converts dimensions in pixels, cm, mm, or inches to integer pixels based on DPI.
    """
    unit_clean = unit.lower().strip()
    if unit_clean in ("px", "pixel", "pixels"):
        return int(round(val))
    elif unit_clean in ("in", "inch", "inches"):
        return int(round(val * dpi))
    elif unit_clean in ("cm", "centimeter", "centimeters"):
        # 1 inch = 2.54 cm
        return int(round((val / 2.54) * dpi))
    elif unit_clean in ("mm", "millimeter", "millimeters"):
        # 1 inch = 25.4 mm
        return int(round((val / 25.4) * dpi))
    else:
        return int(round(val))


def resize_image(
    img: Image.Image,
    target_width: Optional[float] = None,
    target_height: Optional[float] = None,
    unit: str = "px",
    dpi: float = 300.0,
    maintain_aspect: bool = True,
    resample_filter: str = "lanczos",
    scale_mode: str = "fit",  # "fit", "stretch", "cover"
) -> Image.Image:
    """
    Resizes image to target dimensions.
    """
    orig_w, orig_h = img.size
    filter_enum = RESAMPLING_FILTERS.get(resample_filter.lower(), Image.Resampling.LANCZOS)

    # Convert targets to pixels if specified
    req_w_px = unit_to_pixels(target_width, unit, dpi) if target_width is not None and target_width > 0 else None
    req_h_px = unit_to_pixels(target_height, unit, dpi) if target_height is not None and target_height > 0 else None

    if req_w_px is None and req_h_px is None:
        return img.copy()

    if maintain_aspect:
        if req_w_px is not None and req_h_px is not None:
            if scale_mode == "stretch":
                final_w, final_h = req_w_px, req_h_px
            elif scale_mode == "cover":
                # Cover target box and crop excess
                scale = max(req_w_px / orig_w, req_h_px / orig_h)
                temp_w = int(round(orig_w * scale))
                temp_h = int(round(orig_h * scale))
                resized = img.resize((temp_w, temp_h), resample=filter_enum)
                left = (temp_w - req_w_px) // 2
                top = (temp_h - req_h_px) // 2
                return resized.crop((left, top, left + req_w_px, top + req_h_px))
            else:
                # Default "fit" / contain
                scale = min(req_w_px / orig_w, req_h_px / orig_h)
                final_w = max(1, int(round(orig_w * scale)))
                final_h = max(1, int(round(orig_h * scale)))
        elif req_w_px is not None:
            ratio = orig_h / orig_w
            final_w = req_w_px
            final_h = max(1, int(round(req_w_px * ratio)))
        else:  # req_h_px is not None
            ratio = orig_w / orig_h
            final_h = req_h_px
            final_w = max(1, int(round(req_h_px * ratio)))
    else:
        final_w = req_w_px if req_w_px is not None else orig_w
        final_h = req_h_px if req_h_px is not None else orig_h

    # Ensure minimum 1x1 dimensions
    final_w = max(1, final_w)
    final_h = max(1, final_h)

    # Perform high quality resampling
    return img.resize((final_w, final_h), resample=filter_enum)
