"""
Algorithmic image enhancement: auto-contrast, unsharp masking, sharpening, denoise, and upscaling.
"""

from typing import Optional
from PIL import Image, ImageEnhance, ImageOps, ImageFilter


def enhance_image(
    img: Image.Image,
    auto_contrast: bool = False,
    auto_contrast_cutoff: float = 0.5,
    brightness: float = 1.0,  # 1.0 = normal, 1.2 = +20%
    contrast: float = 1.0,
    sharpness: float = 1.0,
    color_balance: float = 1.0,
    denoise: bool = False,
    denoise_radius: int = 1,
    upscale_factor: float = 1.0,  # 1.0 = normal, 2.0 = 2x
) -> Image.Image:
    """
    Applies non-destructive algorithmic enhancements to image.
    Preserves alpha channel if present.
    """
    has_alpha = img.mode in ("RGBA", "LA")
    alpha_channel = None

    if has_alpha:
        alpha_channel = img.split()[-1]
        working_img = img.convert("RGB" if img.mode == "RGBA" else "L")
    else:
        working_img = img.copy()

    # 1. Upscale if requested
    if upscale_factor > 1.0:
        w, h = working_img.size
        new_w = max(1, int(round(w * upscale_factor)))
        new_h = max(1, int(round(h * upscale_factor)))
        working_img = working_img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
        # Apply subtle unsharp mask to restore edge crispness after upscale
        working_img = working_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=3))
        if alpha_channel:
            alpha_channel = alpha_channel.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

    # 2. Denoise (Median filter)
    if denoise:
        working_img = working_img.filter(ImageFilter.MedianFilter(size=max(3, denoise_radius * 2 + 1)))

    # 3. Auto Contrast
    if auto_contrast:
        if working_img.mode in ("RGB", "L"):
            working_img = ImageOps.autocontrast(working_img, cutoff=auto_contrast_cutoff)

    # 4. Brightness
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(working_img)
        working_img = enhancer.enhance(brightness)

    # 5. Contrast
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(working_img)
        working_img = enhancer.enhance(contrast)

    # 6. Color Saturation (only for RGB/RGBA)
    if color_balance != 1.0 and working_img.mode == "RGB":
        enhancer = ImageEnhance.Color(working_img)
        working_img = enhancer.enhance(color_balance)

    # 7. Sharpness
    if sharpness != 1.0:
        enhancer = ImageEnhance.Sharpness(working_img)
        working_img = enhancer.enhance(sharpness)

    # Recombine alpha if present
    if alpha_channel and has_alpha:
        working_img = working_img.convert("RGBA")
        working_img.putalpha(alpha_channel)

    return working_img
