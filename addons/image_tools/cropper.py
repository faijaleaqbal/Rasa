"""
Modular image cropping, rotation, flip, and shape masking operations.
"""

from typing import Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageOps

def rotate_and_flip_image(
    img: Image.Image,
    rotation_angle: float = 0.0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    bg_color: Union[str, Tuple[int, int, int], Tuple[int, int, int, int]] = (255, 255, 255, 0),
) -> Image.Image:
    """
    Applies rotation and horizontal/vertical flipping.
    Handles arbitrary angles with expand=True.
    """
    res = img

    # 1. Flip
    if flip_horizontal:
        res = res.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if flip_vertical:
        res = res.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    # 2. Rotation
    angle = rotation_angle % 360.0
    if angle != 0.0:
        if angle == 90.0:
            res = res.transpose(Image.Transpose.ROTATE_270)  # PIL rotates counter-clockwise
        elif angle == 180.0:
            res = res.transpose(Image.Transpose.ROTATE_180)
        elif angle == 270.0:
            res = res.transpose(Image.Transpose.ROTATE_90)
        else:
            # Arbitrary rotation
            if res.mode != "RGBA":
                res = res.convert("RGBA")
            res = res.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)

    return res


def crop_image(
    img: Image.Image,
    x: Optional[int] = None,
    y: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    aspect_ratio: Optional[str] = None,
    shape: str = "rect",  # "rect", "square", "circle"
) -> Image.Image:
    """
    Crops an image according to specified coordinates, aspect ratio, or geometric shape.
    Coordinates are safely clamped to image bounds.
    """
    img_w, img_h = img.size

    # Handle aspect ratio auto-centering crop if no explicit box is given
    if aspect_ratio and (width is None or height is None or x is None or y is None):
        try:
            parts = aspect_ratio.split(":")
            target_ar = float(parts[0]) / float(parts[1])
            curr_ar = img_w / img_h

            if curr_ar > target_ar:
                # Image is wider than target: trim width
                new_w = int(round(img_h * target_ar))
                new_h = img_h
                x = max(0, (img_w - new_w) // 2)
                y = 0
                width = new_w
                height = new_h
            else:
                # Image is taller than target: trim height
                new_w = img_w
                new_h = int(round(img_w / target_ar))
                x = 0
                y = max(0, (img_h - new_h) // 2)
                width = new_w
                height = new_h
        except Exception:
            pass

    # If shape is square and no box specified, center square crop
    if shape == "square" and (width is None or height is None):
        side = min(img_w, img_h)
        x = (img_w - side) // 2
        y = (img_h - side) // 2
        width = side
        height = side

    # Safe box computation
    if x is None:
        x = 0
    if y is None:
        y = 0
    if width is None:
        width = img_w - x
    if height is None:
        height = img_h - y

    # Clamp coordinates
    x1 = max(0, min(int(x), img_w - 1))
    y1 = max(0, min(int(y), img_h - 1))
    x2 = max(x1 + 1, min(x1 + int(width), img_w))
    y2 = max(y1 + 1, min(y1 + int(height), img_h))

    cropped = img.crop((x1, y1, x2, y2))

    # Handle Circle Crop
    if shape == "circle":
        cropped = apply_circle_mask(cropped)

    return cropped


def apply_circle_mask(img: Image.Image) -> Image.Image:
    """
    Applies a smooth antialiased circular mask to the image.
    Outputs an RGBA image with transparent edges outside the circle.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    w, h = img.size
    size = min(w, h)

    # Center crop to square first if not square
    if w != h:
        x1 = (w - size) // 2
        y1 = (h - size) // 2
        img = img.crop((x1, y1, x1 + size, y1 + size))
        w = h = size

    # Use 4x supersampling for high quality antialiased edge
    scale = 4
    mask_size = size * scale
    mask = Image.new("L", (mask_size, mask_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, mask_size - 1, mask_size - 1), fill=255)
    mask = mask.resize((size, size), resample=Image.Resampling.LANCZOS)

    # Apply alpha mask
    output = img.copy()
    output.putalpha(mask)
    return output
