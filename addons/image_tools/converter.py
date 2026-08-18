"""
Format conversion between JPG, PNG, WebP, HEIC/HEIF, BMP, TIFF with alpha channel and matte handling.
"""

from typing import Optional, Tuple, Union
from PIL import Image, ImageColor

SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "BMP", "TIFF", "GIF"}


def normalize_image_mode(
    img: Image.Image,
    target_format: str,
    matte_color: Union[str, Tuple[int, int, int]] = "#FFFFFF",
) -> Image.Image:
    """
    Normalizes color mode for the target format:
    - If target is JPEG (no alpha support) and image has alpha, blend onto solid matte background.
    - If image is CMYK, convert to RGB.
    - If image is Palette (P), convert to RGBA (or RGB if target is JPEG).
    """
    target_fmt = target_format.upper().replace("JPG", "JPEG")
    curr_mode = img.mode

    # Convert CMYK to RGB
    if curr_mode == "CMYK":
        return img.convert("RGB")

    # If target is JPEG, it cannot have alpha
    if target_fmt == "JPEG":
        if curr_mode in ("RGBA", "LA") or (curr_mode == "P" and "transparency" in img.info):
            img_rgba = img.convert("RGBA")
            # Parse matte color
            if isinstance(matte_color, str):
                try:
                    rgb_matte = ImageColor.getrgb(matte_color)
                except Exception:
                    rgb_matte = (255, 255, 255)
            else:
                rgb_matte = matte_color[:3]

            background = Image.new("RGB", img_rgba.size, rgb_matte)
            background.paste(img_rgba, mask=img_rgba.split()[3])
            return background
        elif curr_mode != "RGB":
            return img.convert("RGB")
        return img

    # Target supports alpha (PNG, WebP, TIFF)
    if target_fmt in ("PNG", "WEBP", "TIFF"):
        if curr_mode == "P":
            return img.convert("RGBA" if "transparency" in img.info else "RGB")
        if curr_mode not in ("RGB", "RGBA", "L", "LA"):
            return img.convert("RGBA")
        return img

    return img


def get_mime_for_format(format_name: str) -> str:
    fmt = format_name.upper().replace("JPG", "JPEG")
    if fmt == "JPEG":
        return "image/jpeg"
    elif fmt == "PNG":
        return "image/png"
    elif fmt == "WEBP":
        return "image/webp"
    elif fmt == "BMP":
        return "image/bmp"
    elif fmt == "TIFF":
        return "image/tiff"
    elif fmt == "GIF":
        return "image/gif"
    return "application/octet-stream"


def get_extension_for_format(format_name: str) -> str:
    fmt = format_name.upper().replace("JPG", "JPEG")
    if fmt == "JPEG":
        return ".jpg"
    elif fmt == "PNG":
        return ".png"
    elif fmt == "WEBP":
        return ".webp"
    elif fmt == "BMP":
        return ".bmp"
    elif fmt == "TIFF":
        return ".tiff"
    elif fmt == "GIF":
        return ".gif"
    return f".{format_name.lower()}"
