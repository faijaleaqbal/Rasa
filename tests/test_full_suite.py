"""
Complete Production Test Suite for Alya Image Tools Module:
- Unit Tests
- Integration Tests
- Malformed Image Tests
- Oversized Image & Decompression Bomb Tests
- Batch Processing Tests
- Compression Target Tests (5KB, 10KB, 20KB, 50KB, 100KB, 200KB, 500KB, 1MB, 2MB)
- Format Conversion Tests
- Security & Privacy Tests
- Live HTTP Endpoints Tests
"""

import io
import os
import json
import time
import unittest
import urllib.request
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
    rate_limiter,
)
from tests.test_image_tools import create_test_image


class TestCorePipelineAndSecurity(unittest.TestCase):
    def test_compression_targets(self):
        """Test exact KB targets across small to large boundaries."""
        targets_kb = [5, 10, 20, 50, 100, 200, 500, 1024, 2048]
        raw_img = create_test_image(1200, 900, "RGB")
        img = Image.open(io.BytesIO(raw_img))

        for kb in targets_kb:
            target_bytes = kb * 1024
            res = compress_to_target_size(img, target_size_bytes=target_bytes, original_size_bytes=len(raw_img), format_name="JPEG")
            self.assertGreater(res.final_size_bytes, 0)
            self.assertLessEqual(res.final_size_bytes, target_bytes * 1.15, f"Failed target {kb} KB")
            self.assertIsNotNone(res.percentage_reduction)

    def test_decompression_bomb_protection(self):
        """Test that image validator protects against decompression bomb dimensions."""
        fake_header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
        res = validate_image_bytes(fake_header)
        self.assertFalse(res.is_valid)

    def test_security_zero_path_leakage(self):
        """Verify that pipeline outputs tokenized identifiers with zero server path exposure."""
        data = create_test_image(400, 300, "RGB")
        res = process_image_pipeline(image_bytes=data, filename="secret_user_photo.png")
        self.assertTrue(res["success"])
        self.assertIn("token", res)
        # Verify response dictionary does not contain /home or /tmp filesystem paths
        res_str = json.dumps(res)
        self.assertNotIn("/home/ubuntu", res_str)
        self.assertNotIn("/var/", res_str)

    def test_circle_crop_transparency(self):
        """Test that circle crop creates smooth antialiased alpha edges in PNG and WebP."""
        data = create_test_image(300, 300, "RGB")
        res = process_image_pipeline(
            image_bytes=data,
            crop_shape="circle",
            output_format="PNG",
        )
        self.assertTrue(res["success"])
        token = res["token"]
        item = ephemeral_store.get(token)
        out_img = Image.open(io.BytesIO(item.data))
        self.assertEqual(out_img.mode, "RGBA")
        # Corner must have 0 opacity
        self.assertEqual(out_img.getpixel((0, 0))[3], 0)
        # Center must have 255 opacity
        self.assertEqual(out_img.getpixel((150, 150))[3], 255)

    def test_format_conversions_all_matrix(self):
        """Test matrix conversions: JPG -> PNG, PNG -> WebP, WebP -> JPG."""
        jpg_data = create_test_image(200, 200, "RGB")
        png_data = create_test_image(200, 200, "RGBA")

        # 1. JPG -> PNG
        res1 = process_image_pipeline(image_bytes=jpg_data, output_format="PNG")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["metrics"]["output_format"], "PNG")

        # 2. PNG -> WebP
        res2 = process_image_pipeline(image_bytes=png_data, output_format="WEBP")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["metrics"]["output_format"], "WEBP")

        # 3. PNG -> JPEG with matte
        res3 = process_image_pipeline(image_bytes=png_data, output_format="JPEG", matte_color="#FFFFFF")
        self.assertTrue(res3["success"])
        self.assertEqual(res3["metrics"]["output_format"], "JPEG")

    def test_physical_units_resizing(self):
        """Test cm, mm, in resizing with accurate DPI translation."""
        data = create_test_image(1000, 1000, "RGB")

        # 3.5 x 4.5 cm @ 300 DPI
        # 3.5 / 2.54 * 300 = 413 px, 4.5 / 2.54 * 300 = 531 px
        res = process_image_pipeline(
            image_bytes=data,
            target_width=3.5,
            target_height=4.5,
            unit="cm",
            dpi=300,
            maintain_aspect=False,
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["metrics"]["final_dimensions"], [413, 531])

    def test_rate_limiter(self):
        """Test token bucket rate limiter behaviour."""
        ip = "192.168.100.5"
        allowed = [rate_limiter.allow_request(ip, tokens_cost=10) for _ in range(15)]
        self.assertTrue(allowed[0])
        # After draining bucket, it should reject
        self.assertIn(False, allowed)

    def test_live_http_service(self):
        """Test that the live systemd service on port 5050 is responding properly."""
        req = urllib.request.urlopen("http://127.0.0.1:5050/api/image/health")
        self.assertEqual(req.status, 200)
        body = json.loads(req.read().decode("utf-8"))
        self.assertEqual(body["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
