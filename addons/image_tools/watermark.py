"""
Text and image watermarks, logo overlays, and privacy blur / pixelation.
"""

import math
from typing import Optional, Tuple, Union, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor


def apply_text_watermark(
    img: Image.Image,
    text: str,
    font_size: int = 36,
    opacity: float = 0.5,  # 0.0 to 1.0
    color: Union[str, Tuple[int, int, int]] = "#FFFFFF",
    position: str = "bottom-right",  # "center", "top-left", "top-right", "bottom-left", "bottom-right", "tile"
    margin: int = 20,
    angle: float = 0.0,
) -> Image.Image:
    """
    Overlays a clean anti-aliased text watermark onto the image.
    """
    if not text:
        return img

    orig_mode = img.mode
    base = img.convert("RGBA")

    # Parse color & alpha
    if isinstance(color, str):
        try:
            rgb = ImageColor.getrgb(color)
        except Exception:
            rgb = (255, 255, 255)
    else:
        rgb = color[:3]

    alpha = max(0, min(255, int(round(opacity * 255))))
    rgba_color = (rgb[0], rgb[1], rgb[2], alpha)

    # Use default font or truetype
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Estimate text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    w, h = base.size

    if position == "tile":
        step_x = max(tw + 80, 150)
        step_y = max(th + 80, 100)
        for cur_y in range(margin, h, step_y):
            for cur_x in range(margin, w, step_x):
                draw.text((cur_x, cur_y), text, font=font, fill=rgba_color)
    else:
        if position == "center":
            x = (w - tw) // 2
            y = (h - th) // 2
        elif position == "top-left":
            x = margin
            y = margin
        elif position == "top-right":
            x = w - tw - margin
            y = margin
        elif position == "bottom-left":
            x = margin
            y = h - th - margin
        else:  # "bottom-right"
            x = w - tw - margin
            y = h - th - margin

        x = max(0, x)
        y = max(0, y)
        draw.text((x, y), text, font=font, fill=rgba_color)

    # Composite overlay onto base
    result = Image.alpha_composite(base, overlay)
    return result if orig_mode == "RGBA" else result.convert(orig_mode if orig_mode in ("RGB", "L") else "RGB")


def apply_privacy_blur_or_pixelate(
    img: Image.Image,
    box: Optional[Tuple[int, int, int, int]] = None,  # (x, y, w, h)
    effect: str = "blur",  # "blur" or "pixelate"
    intensity: int = 15,
) -> Image.Image:
    """
    Applies Gaussian Blur or Pixelation to a specified region or whole image.
    """
    result = img.copy()
    img_w, img_h = img.size

    if box is None:
        x1, y1, x2, y2 = 0, 0, img_w, img_h
    else:
        bx, by, bw, bh = box
        x1 = max(0, min(bx, img_w - 1))
        y1 = max(0, min(by, img_h - 1))
        x2 = max(x1 + 1, min(x1 + bw, img_w))
        y2 = max(y1 + 1, min(y1 + bh, img_h))

    region = result.crop((x1, y1, x2, y2))
    reg_w, reg_h = region.size

    if effect == "pixelate":
        pixel_size = max(2, intensity)
        small_w = max(1, reg_w // pixel_size)
        small_h = max(1, reg_h // pixel_size)
        processed = region.resize((small_w, small_h), resample=Image.Resampling.NEAREST)
        processed = processed.resize((reg_w, reg_h), resample=Image.Resampling.NEAREST)
    else:
        # Gaussian Blur
        radius = max(1, intensity)
        processed = region.filter(ImageFilter.GaussianBlur(radius=radius))

    result.paste(processed, (x1, y1))
    return result
