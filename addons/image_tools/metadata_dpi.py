"""
EXIF metadata extraction, stripping, and DPI inspection / modification.
"""

import io
from typing import Optional, Dict, Any, Tuple
from PIL import Image, ExifTags

try:
    import piexif
    PIEXIF_AVAILABLE = True
except Exception:
    PIEXIF_AVAILABLE = False


def extract_exif_metadata(img: Image.Image) -> Dict[str, Any]:
    """
    Extracts and humanizes EXIF data, GPS coordinates, camera specs, and color profiles.
    """
    result: Dict[str, Any] = {
        "has_exif": False,
        "camera": {},
        "exposure": {},
        "datetime": None,
        "software": None,
        "gps": None,
        "raw_tags": {},
    }

    try:
        exif = img.getexif()
        if not exif:
            return result

        result["has_exif"] = True

        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            # Format value safely
            if isinstance(value, bytes):
                try:
                    str_val = value.decode("utf-8", errors="ignore").strip("\x00")
                except Exception:
                    str_val = str(value)
            else:
                str_val = str(value)

            result["raw_tags"][tag_name] = str_val

            if tag_name == "Make":
                result["camera"]["make"] = str_val
            elif tag_name == "Model":
                result["camera"]["model"] = str_val
            elif tag_name == "Software":
                result["software"] = str_val
            elif tag_name == "DateTime":
                result["datetime"] = str_val
            elif tag_name == "ExposureTime":
                result["exposure"]["exposure_time"] = str_val
            elif tag_name == "FNumber":
                result["exposure"]["f_number"] = str_val
            elif tag_name == "ISOSpeedRatings":
                result["exposure"]["iso"] = str_val
            elif tag_name == "FocalLength":
                result["exposure"]["focal_length"] = str_val

        # Check for GPS IFD
        if hasattr(ExifTags, "IFD") and ExifTags.IFD.GPSInfo in exif:
            gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)
            if gps_info:
                gps_dict = {}
                for g_tag_id, g_val in gps_info.items():
                    g_name = ExifTags.GPSTAGS.get(g_tag_id, str(g_tag_id))
                    gps_dict[g_name] = str(g_val)
                result["gps"] = gps_dict

    except Exception:
        pass

    return result


def get_image_dpi(img: Image.Image) -> Tuple[float, float]:
    """Reads DPI from image info, defaulting to 72.0 DPI."""
    dpi_val = img.info.get("dpi", (72.0, 72.0))
    if isinstance(dpi_val, (tuple, list)) and len(dpi_val) >= 2:
        try:
            return (float(dpi_val[0]), float(dpi_val[1]))
        except Exception:
            return (72.0, 72.0)
    return (72.0, 72.0)


def calculate_physical_dimensions(width_px: int, height_px: int, dpi: float) -> Dict[str, Any]:
    """
    Computes physical print dimensions from pixel count and DPI.
    """
    safe_dpi = max(1.0, dpi)
    width_in = width_px / safe_dpi
    height_in = height_px / safe_dpi

    width_cm = width_in * 2.54
    height_cm = height_in * 2.54

    width_mm = width_cm * 10.0
    height_mm = height_cm * 10.0

    return {
        "dpi": safe_dpi,
        "width_px": width_px,
        "height_px": height_px,
        "inches": {"width": round(width_in, 2), "height": round(height_in, 2)},
        "cm": {"width": round(width_cm, 2), "height": round(height_cm, 2)},
        "mm": {"width": round(width_mm, 1), "height": round(height_mm, 1)},
    }
