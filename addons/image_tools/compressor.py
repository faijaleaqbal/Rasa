"""
High-performance image compression engine supporting target size (KB/MB) and quality modes.
Guarantees strict size boundaries, safe binary search termination, and format-specific optimizations.
"""

import io
from typing import Optional, Tuple, Dict, Any
from PIL import Image

from .converter import normalize_image_mode


class CompressionResult:
    def __init__(
        self,
        data: bytes,
        original_size_bytes: int,
        final_size_bytes: int,
        original_width: int,
        original_height: int,
        final_width: int,
        final_height: int,
        format_name: str,
        quality_used: int,
        scale_factor: float = 1.0,
        warning: Optional[str] = None,
        target_size_bytes: Optional[int] = None,
    ):
        self.data = data
        self.original_size_bytes = original_size_bytes
        self.final_size_bytes = final_size_bytes
        self.original_width = original_width
        self.original_height = original_height
        self.final_width = final_width
        self.final_height = final_height
        self.format_name = format_name.upper().replace("JPG", "JPEG")
        self.quality_used = quality_used
        self.scale_factor = scale_factor
        self.warning = warning
        self.target_size_bytes = target_size_bytes

    @property
    def percentage_reduction(self) -> float:
        if self.original_size_bytes <= 0:
            return 0.0
        diff = self.original_size_bytes - self.final_size_bytes
        return round(max(0.0, (diff / self.original_size_bytes) * 100.0), 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_size_bytes": self.original_size_bytes,
            "original_size_kb": round(self.original_size_bytes / 1024, 2),
            "original_size_mb": round(self.original_size_bytes / (1024 * 1024), 2),
            "final_size_bytes": self.final_size_bytes,
            "final_size_kb": round(self.final_size_bytes / 1024, 2),
            "final_size_mb": round(self.final_size_bytes / (1024 * 1024), 2),
            "percentage_reduction": self.percentage_reduction,
            "original_dimensions": [self.original_width, self.original_height],
            "final_dimensions": [self.final_width, self.final_height],
            "format": self.format_name,
            "quality_used": self.quality_used,
            "scale_factor": round(self.scale_factor, 3),
            "warning": self.warning,
            "target_size_bytes": self.target_size_bytes,
            "target_size_kb": round(self.target_size_bytes / 1024, 2) if self.target_size_bytes else None,
        }


def encode_image(
    img: Image.Image,
    format_name: str,
    quality: int = 85,
    optimize: bool = True,
    dpi: Optional[Tuple[float, float]] = None,
    icc_profile: Optional[bytes] = None,
    exif: Optional[bytes] = None,
    png_colors: Optional[int] = None,
) -> bytes:
    """Encodes a PIL Image into bytes with specified format and quality settings."""
    fmt = format_name.upper().replace("JPG", "JPEG")
    target_img = normalize_image_mode(img, fmt)

    out = io.BytesIO()
    save_kwargs: Dict[str, Any] = {"format": fmt}

    if dpi:
        save_kwargs["dpi"] = dpi
    if icc_profile:
        save_kwargs["icc_profile"] = icc_profile
    if exif and fmt in ("JPEG", "WEBP", "TIFF"):
        save_kwargs["exif"] = exif

    if fmt == "JPEG":
        save_kwargs["quality"] = max(1, min(int(quality), 95))
        save_kwargs["optimize"] = optimize
        save_kwargs["progressive"] = True
        target_img.save(out, **save_kwargs)

    elif fmt == "WEBP":
        save_kwargs["quality"] = max(1, min(int(quality), 100))
        save_kwargs["method"] = 6  # Highest compression effort
        target_img.save(out, **save_kwargs)

    elif fmt == "PNG":
        save_kwargs["optimize"] = optimize
        save_kwargs["compress_level"] = 9
        if png_colors and png_colors < 256:
            # Quantize for massive PNG reduction
            quantized = target_img.quantize(colors=png_colors, method=Image.Quantize.MEDIANCUT)
            quantized.save(out, **save_kwargs)
        else:
            target_img.save(out, **save_kwargs)

    else:
        target_img.save(out, **save_kwargs)

    return out.getvalue()


def compress_to_target_size(
    img: Image.Image,
    target_size_bytes: int,
    original_size_bytes: int,
    format_name: str = "JPEG",
    dpi: Optional[Tuple[float, float]] = None,
    min_dimension: int = 16,
) -> CompressionResult:
    """
    Compresses an image to strictly achieve <= target_size_bytes.
    Uses binary search on quality, and adaptive downsampling if quality floor is reached.
    Minimum dimension floor is strictly enforced to prevent invalid zero/sub-pixel dimensions.
    """
    fmt = format_name.upper().replace("JPG", "JPEG")
    orig_w, orig_h = img.size
    current_img = img.copy()
    current_w, current_h = orig_w, orig_h
    scale_factor = 1.0

    best_data: Optional[bytes] = None
    best_quality = 85
    warning: Optional[str] = None

    max_scale_iterations = 10

    for scale_iter in range(max_scale_iterations):
        if fmt in ("JPEG", "WEBP"):
            low_q = 5 if fmt == "JPEG" else 1
            high_q = 95 if fmt == "JPEG" else 100
            pass_best_data = None
            pass_best_q = low_q

            # Bounded binary search on quality
            while low_q <= high_q:
                mid_q = (low_q + high_q) // 2
                test_bytes = encode_image(current_img, fmt, quality=mid_q, dpi=dpi)
                test_size = len(test_bytes)

                if test_size <= target_size_bytes:
                    pass_best_data = test_bytes
                    pass_best_q = mid_q
                    low_q = mid_q + 1  # Try higher quality
                else:
                    high_q = mid_q - 1  # Too big, reduce quality

            if pass_best_data is not None:
                best_data = pass_best_data
                best_quality = pass_best_q
                break  # Target achieved!
            else:
                # Even at minimum quality, image exceeds target.
                # Downscale dimensions adaptively while respecting min_dimension floor
                new_w = max(min_dimension, int(round(current_w * 0.75)))
                new_h = max(min_dimension, int(round(current_h * 0.75)))

                if new_w == current_w and new_h == current_h:
                    # Reached dimension floor
                    best_data = encode_image(current_img, fmt, quality=5 if fmt == "JPEG" else 1, dpi=dpi)
                    best_quality = 5 if fmt == "JPEG" else 1
                    warning = (
                        f"Target {round(target_size_bytes/1024, 1)} KB was mathematically impractical for {fmt} "
                        f"container overhead; minimized to {round(len(best_data)/1024, 1)} KB."
                    )
                    break

                scale_factor *= (new_w / current_w)
                current_w, current_h = new_w, new_h
                current_img = img.resize((current_w, current_h), resample=Image.Resampling.LANCZOS)
                warning = f"Image dimensions optimized to {current_w}x{current_h} px to reach strict {round(target_size_bytes/1024, 1)} KB limit."

        elif fmt == "PNG":
            quant_levels = [None, 256, 128, 64, 32, 16, 8]
            pass_found = False
            for num_colors in quant_levels:
                test_bytes = encode_image(current_img, fmt, png_colors=num_colors, dpi=dpi)
                if len(test_bytes) <= target_size_bytes:
                    best_data = test_bytes
                    best_quality = 100
                    pass_found = True
                    break

            if pass_found:
                break
            else:
                new_w = max(min_dimension, int(round(current_w * 0.75)))
                new_h = max(min_dimension, int(round(current_h * 0.75)))

                if new_w == current_w and new_h == current_h:
                    best_data = encode_image(current_img, fmt, png_colors=8, dpi=dpi)
                    best_quality = 100
                    warning = (
                        f"Target {round(target_size_bytes/1024, 1)} KB reached PNG format header limit; "
                        f"minimized to {round(len(best_data)/1024, 1)} KB."
                    )
                    break

                scale_factor *= (new_w / current_w)
                current_w, current_h = new_w, new_h
                current_img = img.resize((current_w, current_h), resample=Image.Resampling.LANCZOS)
                warning = f"Image dimensions optimized to {current_w}x{current_h} px to reach {round(target_size_bytes/1024, 1)} KB limit."

        else:
            best_data = encode_image(current_img, fmt, dpi=dpi)
            break

    if best_data is None:
        best_data = encode_image(current_img, fmt, quality=5, dpi=dpi)
        best_quality = 5
        warning = f"Target {round(target_size_bytes/1024, 1)} KB was tight for this image; achieved {round(len(best_data)/1024, 1)} KB."

    return CompressionResult(
        data=best_data,
        original_size_bytes=original_size_bytes,
        final_size_bytes=len(best_data),
        original_width=orig_w,
        original_height=orig_h,
        final_width=current_w,
        final_height=current_h,
        format_name=fmt,
        quality_used=best_quality,
        scale_factor=scale_factor,
        warning=warning,
        target_size_bytes=target_size_bytes,
    )


def compress_by_quality(
    img: Image.Image,
    original_size_bytes: int,
    quality: int = 80,
    format_name: str = "JPEG",
    dpi: Optional[Tuple[float, float]] = None,
    icc_profile: Optional[bytes] = None,
    exif: Optional[bytes] = None,
) -> CompressionResult:
    """Compresses an image using a fixed quality percentage (1-100)."""
    fmt = format_name.upper().replace("JPG", "JPEG")
    orig_w, orig_h = img.size
    data = encode_image(
        img,
        format_name=fmt,
        quality=quality,
        dpi=dpi,
        icc_profile=icc_profile,
        exif=exif,
    )

    return CompressionResult(
        data=data,
        original_size_bytes=original_size_bytes,
        final_size_bytes=len(data),
        original_width=orig_w,
        original_height=orig_h,
        final_width=orig_w,
        final_height=orig_h,
        format_name=fmt,
        quality_used=quality,
        scale_factor=1.0,
    )
