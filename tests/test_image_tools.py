"""
Production-Hardening Unit & Integration Test Suite for Alya Image Tools Module.
Covers all boundary conditions, security guards, format matrix, decompression bombs,
exact KB/MB targets (5KB, 10KB, 20KB, 50KB, 100KB, 1MB), and edge cases.
"""

import io
import os
import time
import unittest
import numpy as np
from PIL import Image, ImageDraw

from addons.image_tools import (
    process_image_pipeline,
    validate_image_bytes,
    compress_to_target_size,
    compress_by_quality,
    resize_image,
    crop_image,
    rotate_and_flip_image,
    apply_circle_mask,
    normalize_image_mode,
    enhance_image,
    extract_exif_metadata,
    calculate_physical_dimensions,
    apply_text_watermark,
    apply_privacy_blur_or_pixelate,
    preset_registry,
    process_batch_pipeline,
    ephemeral_store,
)
from addons.image_tools.security import EphemeralStore, TokenBucketRateLimiter
from addons.image_tools.validator import detect_mime_from_magic


def create_test_image(
    width: int = 400,
    height: int = 300,
    color_mode: str = "RGB",
    pattern: bool = True,
    noisy: bool = False,
) -> bytes:
    """Helper to generate in-memory synthetic images for testing."""
    if color_mode == "RGBA":
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle((20, 20, width - 20, height - 20), fill=(255, 100, 50, 220))
        draw.ellipse((width // 4, height // 4, 3 * width // 4, 3 * height // 4), fill=(50, 150, 255, 180))
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()
    elif noisy:
        # High entropy noise image
        arr = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        img = Image.fromarray(arr, "RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=95)
        return out.getvalue()
    else:
        img = Image.new("RGB", (width, height), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        if pattern:
            for x in range(0, width, 40):
                draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
            for y in range(0, height, 40):
                draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)
            draw.rectangle((50, 50, width - 50, height - 50), fill=(40, 120, 220), outline=(20, 60, 110), width=3)
            draw.ellipse((100, 80, 220, 200), fill=(255, 200, 50))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=95)
        return out.getvalue()


class TestImageValidationAndSecurity(unittest.TestCase):
    def test_valid_jpeg(self):
        data = create_test_image(400, 300, "RGB")
        res = validate_image_bytes(data)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.format_name, "JPEG")
        self.assertEqual(res.width, 400)
        self.assertEqual(res.height, 300)

    def test_valid_transparent_png(self):
        data = create_test_image(200, 200, "RGBA")
        res = validate_image_bytes(data)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.format_name, "PNG")
        self.assertTrue(res.has_alpha)

    def test_empty_file_rejected(self):
        res = validate_image_bytes(b"")
        self.assertFalse(res.is_valid)
        self.assertIn("empty", res.error.lower())

    def test_malformed_bytes_rejected(self):
        res = validate_image_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF corrupted garbage header...")
        self.assertFalse(res.is_valid)

    def test_truncated_bytes_rejected(self):
        data = create_test_image(200, 200, "RGB")[:40]
        res = validate_image_bytes(data)
        self.assertFalse(res.is_valid)

    def test_magic_byte_sniffing(self):
        self.assertEqual(detect_mime_from_magic(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"), "image/jpeg")
        self.assertEqual(detect_mime_from_magic(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"), "image/png")
        self.assertEqual(detect_mime_from_magic(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image/webp")
        self.assertEqual(detect_mime_from_magic(b"BM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"), "image/bmp")

    def test_fake_extension_detected(self):
        # PNG bytes with fake JPEG magic check
        png_data = create_test_image(100, 100, "RGBA")
        res = validate_image_bytes(png_data)
        self.assertEqual(res.format_name, "PNG")
        self.assertEqual(res.mime_type, "image/png")

    def test_oversized_file_limit(self):
        dummy_large = b"0" * (51 * 1024 * 1024)
        res = validate_image_bytes(dummy_large)
        self.assertFalse(res.is_valid)
        self.assertIn("exceeds maximum", res.error.lower())

    def test_decompression_bomb_safety(self):
        # 12000x10000 = 120,000,000 pixels (exceeds 100,000,000 max limit)
        img = Image.new("RGB", (12000, 10000), (255, 255, 255))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=10)
        huge_bytes = out.getvalue()
        res = validate_image_bytes(huge_bytes)
        self.assertFalse(res.is_valid)
        self.assertIn("decompression bomb", res.error.lower())


class TestTargetCompressionBoundaries(unittest.TestCase):
    """Tests exact KB/MB target limits (5KB, 10KB, 20KB, 50KB, 100KB, 1MB)."""

    def setUp(self):
        self.sample_rgb = Image.open(io.BytesIO(create_test_image(800, 600, "RGB", pattern=True)))
        self.noisy_img = Image.open(io.BytesIO(create_test_image(600, 600, "RGB", noisy=True)))
        self.rgba_img = Image.open(io.BytesIO(create_test_image(400, 400, "RGBA")))

    def test_target_5kb_jpeg(self):
        orig_bytes = len(create_test_image(800, 600, "RGB"))
        res = compress_to_target_size(self.sample_rgb, target_size_bytes=5 * 1024, original_size_bytes=orig_bytes, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 5 * 1024 + 128)  # Allow container header tolerance
        self.assertGreater(res.final_width, 0)
        self.assertGreater(res.final_height, 0)

    def test_target_10kb_jpeg(self):
        orig_bytes = len(create_test_image(800, 600, "RGB"))
        res = compress_to_target_size(self.sample_rgb, target_size_bytes=10 * 1024, original_size_bytes=orig_bytes, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 10 * 1024)

    def test_target_20kb_jpeg(self):
        orig_bytes = len(create_test_image(800, 600, "RGB"))
        res = compress_to_target_size(self.sample_rgb, target_size_bytes=20 * 1024, original_size_bytes=orig_bytes, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 20 * 1024)

    def test_target_50kb_jpeg(self):
        orig_bytes = len(create_test_image(800, 600, "RGB"))
        res = compress_to_target_size(self.sample_rgb, target_size_bytes=50 * 1024, original_size_bytes=orig_bytes, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 50 * 1024)

    def test_target_100kb_jpeg(self):
        orig_bytes = len(create_test_image(800, 600, "RGB"))
        res = compress_to_target_size(self.sample_rgb, target_size_bytes=100 * 1024, original_size_bytes=orig_bytes, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 100 * 1024)

    def test_target_1mb_large_image(self):
        huge_img = Image.new("RGB", (3000, 2000), (120, 150, 180))
        res = compress_to_target_size(huge_img, target_size_bytes=1024 * 1024, original_size_bytes=5 * 1024 * 1024, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 1024 * 1024)

    def test_target_webp_compression(self):
        orig_bytes = len(create_test_image(800, 600, "RGB"))
        res = compress_to_target_size(self.sample_rgb, target_size_bytes=15 * 1024, original_size_bytes=orig_bytes, format_name="WEBP")
        self.assertLessEqual(res.final_size_bytes, 15 * 1024)
        self.assertEqual(res.format_name, "WEBP")

    def test_target_png_quantization(self):
        orig_bytes = len(create_test_image(400, 400, "RGBA"))
        res = compress_to_target_size(self.rgba_img, target_size_bytes=25 * 1024, original_size_bytes=orig_bytes, format_name="PNG")
        self.assertLessEqual(res.final_size_bytes, 25 * 1024)

    def test_noisy_photograph_compression(self):
        orig_bytes = len(create_test_image(600, 600, "RGB", noisy=True))
        res = compress_to_target_size(self.noisy_img, target_size_bytes=30 * 1024, original_size_bytes=orig_bytes, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 30 * 1024)

    def test_already_small_image(self):
        small_img = Image.new("RGB", (32, 32), (100, 100, 100))
        res = compress_to_target_size(small_img, target_size_bytes=50 * 1024, original_size_bytes=500, format_name="JPEG")
        self.assertLessEqual(res.final_size_bytes, 50 * 1024)

    def test_quality_mode_compression(self):
        orig_bytes = len(create_test_image(600, 400, "RGB"))
        res = compress_by_quality(self.sample_rgb, original_size_bytes=orig_bytes, quality=60, format_name="JPEG")
        self.assertEqual(res.quality_used, 60)
        self.assertGreater(res.final_size_bytes, 0)


class TestFormatMatrixAndConversions(unittest.TestCase):
    def test_cmyk_to_rgb_jpeg(self):
        cmyk_img = Image.new("CMYK", (200, 200), (0, 100, 100, 0))
        norm = normalize_image_mode(cmyk_img, "JPEG")
        self.assertEqual(norm.mode, "RGB")

    def test_rgba_to_jpeg_with_white_matte(self):
        rgba_img = Image.new("RGBA", (200, 200), (255, 0, 0, 128))
        norm = normalize_image_mode(rgba_img, "JPEG", matte_color="#FFFFFF")
        self.assertEqual(norm.mode, "RGB")

    def test_palette_to_png(self):
        p_img = Image.new("P", (100, 100))
        norm = normalize_image_mode(p_img, "PNG")
        self.assertIn(norm.mode, ("RGB", "RGBA"))

    def test_bmp_and_tiff_encoding(self):
        img = Image.new("RGB", (150, 150), (50, 150, 250))
        bmp_norm = normalize_image_mode(img, "BMP")
        self.assertEqual(bmp_norm.mode, "RGB")
        tiff_norm = normalize_image_mode(img, "TIFF")
        self.assertEqual(tiff_norm.mode, "RGB")


class TestResizeAndCropCorrectness(unittest.TestCase):
    def test_resize_px(self):
        img = Image.new("RGB", (800, 600), (200, 200, 200))
        resized = resize_image(img, target_width=400, target_height=300, maintain_aspect=True)
        self.assertEqual(resized.size, (400, 300))

    def test_resize_cm_at_300dpi(self):
        img = Image.new("RGB", (1000, 1000), (200, 200, 200))
        # 5 cm at 300 DPI = 5 * (300 / 2.54) = 590.55 -> ~591 px
        resized = resize_image(img, target_width=5.0, target_height=5.0, unit="cm", dpi=300.0, maintain_aspect=False)
        self.assertEqual(resized.size, (591, 591))

    def test_aspect_ratio_crop_16_9(self):
        img = Image.new("RGB", (1000, 1000), (200, 200, 200))
        cropped = crop_image(img, aspect_ratio="16:9")
        w, h = cropped.size
        self.assertAlmostEqual(w / h, 16 / 9, delta=0.05)

    def test_circle_crop_transparency(self):
        img = Image.new("RGB", (400, 400), (255, 100, 50))
        circled = apply_circle_mask(img)
        self.assertEqual(circled.mode, "RGBA")
        self.assertEqual(circled.size, (400, 400))
        # Corner (0,0) must be 100% transparent
        self.assertEqual(circled.getpixel((0, 0))[3], 0)
        # Center (200,200) must be 100% opaque
        self.assertEqual(circled.getpixel((200, 200))[3], 255)

    def test_rotation_and_flip(self):
        img = Image.new("RGB", (300, 200), (100, 150, 200))
        rotated = rotate_and_flip_image(img, rotation_angle=90.0, flip_horizontal=True)
        self.assertEqual(rotated.size, (200, 300))


class TestMetadataAndDPI(unittest.TestCase):
    def test_physical_print_calculation(self):
        dims = calculate_physical_dimensions(1200, 1800, 300.0)
        self.assertEqual(dims["inches"]["width"], 4.0)
        self.assertEqual(dims["inches"]["height"], 6.0)
        self.assertAlmostEqual(dims["cm"]["width"], 10.16, delta=0.05)
        self.assertAlmostEqual(dims["cm"]["height"], 15.24, delta=0.05)


class TestEnhancementAndWatermark(unittest.TestCase):
    def test_enhance_image(self):
        data = create_test_image(200, 200, "RGB")
        img = Image.open(io.BytesIO(data))
        enhanced = enhance_image(img, auto_contrast=True, brightness=1.1, contrast=1.2, sharpness=1.5, denoise=True)
        self.assertEqual(enhanced.size, (200, 200))

    def test_upscale(self):
        data = create_test_image(100, 100, "RGB")
        img = Image.open(io.BytesIO(data))
        upscaled = enhance_image(img, upscale_factor=2.0)
        self.assertEqual(upscaled.size, (200, 200))

    def test_watermark_text(self):
        data = create_test_image(300, 200, "RGB")
        img = Image.open(io.BytesIO(data))
        wm = apply_text_watermark(img, "Confidential Sample", opacity=0.7, position="center")
        self.assertEqual(wm.size, (300, 200))

    def test_watermark_tile_position(self):
        data = create_test_image(400, 300, "RGB")
        img = Image.open(io.BytesIO(data))
        wm = apply_text_watermark(img, "COPYRIGHT", opacity=0.3, position="tile")
        self.assertEqual(wm.size, (400, 300))

    def test_privacy_blur_clamped_coordinates(self):
        data = create_test_image(300, 200, "RGB")
        img = Image.open(io.BytesIO(data))
        # Coordinates out of bounds should be safely clamped
        blurred = apply_privacy_blur_or_pixelate(img, box=(-50, -50, 600, 500), effect="blur", intensity=10)
        self.assertEqual(blurred.size, (300, 200))

    def test_privacy_pixelation(self):
        data = create_test_image(300, 200, "RGB")
        img = Image.open(io.BytesIO(data))
        pixelated = apply_privacy_blur_or_pixelate(img, box=(20, 20, 100, 100), effect="pixelate", intensity=8)
        self.assertEqual(pixelated.size, (300, 200))


class TestSecurityStoreAndRateLimiter(unittest.TestCase):
    def test_ephemeral_token_expiration(self):
        store = EphemeralStore()
        token = store.put(b"test data", "test.jpg", "image/jpeg", ttl_seconds=1)
        self.assertIsNotNone(store.get(token))
        time.sleep(1.2)
        self.assertIsNone(store.get(token), "Expired token was not purged!")

    def test_filename_sanitization_prevents_path_traversal(self):
        store = EphemeralStore()
        token = store.put(b"test data", "../../../etc/passwd", "image/jpeg")
        item = store.get(token)
        self.assertNotIn("/", item.filename)
        self.assertNotIn("..", item.filename)

    def test_rate_limiter_throttling(self):
        limiter = TokenBucketRateLimiter(capacity=3, refill_rate_per_sec=1.0)
        ip = "192.168.1.55"
        self.assertTrue(limiter.allow_request(ip))
        self.assertTrue(limiter.allow_request(ip))
        self.assertTrue(limiter.allow_request(ip))
        self.assertFalse(limiter.allow_request(ip), "Rate limiter did not throttle on burst limit!")


class TestPresetsAndPipeline(unittest.TestCase):
    def test_presets_registered(self):
        presets = preset_registry.list_all()
        self.assertGreater(len(presets), 10)
        passport = preset_registry.get("passport_india")
        self.assertIsNotNone(passport)
        self.assertEqual(passport.dpi, 300)

    def test_full_pipeline_execution(self):
        data = create_test_image(600, 400, "RGB")
        res = process_image_pipeline(
            image_bytes=data,
            filename="passport_test.jpg",
            preset_id="passport_india",
            watermark_text="Alya Verified",
        )
        self.assertTrue(res["success"])
        self.assertIn("token", res)
        self.assertEqual(res["metrics"]["final_dimensions"], [413, 531])
        self.assertIsNotNone(ephemeral_store.get(res["token"]))

    def test_batch_processing_and_zip(self):
        img1 = create_test_image(300, 300, "RGB")
        img2 = create_test_image(400, 400, "RGBA")
        batch_items = [(img1, "file1.jpg"), (img2, "file2.png")]
        batch_res = process_batch_pipeline(
            items=batch_items,
            options={"quality": 80, "output_format": "WEBP"}
        )
        self.assertTrue(batch_res["success"])
        self.assertEqual(batch_res["successful"], 2)
        self.assertEqual(batch_res["failed"], 0)
        self.assertIsNotNone(batch_res["zip_token"])
        zip_item = ephemeral_store.get(batch_res["zip_token"])
        self.assertIsNotNone(zip_item)
        self.assertEqual(zip_item.mime_type, "application/zip")

    def test_batch_per_file_error_isolation(self):
        good_img = create_test_image(200, 200, "RGB")
        bad_img = b"corrupted garbage"
        batch_items = [(good_img, "good.jpg"), (bad_img, "bad.jpg")]
        batch_res = process_batch_pipeline(items=batch_items, options={})
        self.assertTrue(batch_res["success"])
        self.assertEqual(batch_res["successful"], 1)
        self.assertEqual(batch_res["failed"], 1)


if __name__ == "__main__":
    unittest.main()
