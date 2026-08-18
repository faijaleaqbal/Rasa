"""
Integration test suite testing the aiohttp REST API endpoints for Image Tools.
"""

import io
import json
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import FormData
from PIL import Image

from addons.image_tools.server import create_image_tools_app
from tests.test_image_tools import create_test_image


class TestImageToolsAPI(AioHTTPTestCase):
    async def get_application(self):
        return create_image_tools_app()

    @unittest_run_loop
    async def test_health_endpoint(self):
        resp = await self.client.request("GET", "/api/image/health")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertGreater(data["presets_count"], 0)

    @unittest_run_loop
    async def test_presets_endpoint(self):
        resp = await self.client.request("GET", "/api/image/presets")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertIn("presets", data)
        self.assertIn("categories", data)

    @unittest_run_loop
    async def test_metadata_extraction(self):
        img_bytes = create_test_image(350, 450, "RGB")
        form = FormData()
        form.add_field("file", img_bytes, filename="test.jpg", content_type="image/jpeg")

        resp = await self.client.request("POST", "/api/image/metadata", data=form)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["basic"]["width"], 350)
        self.assertEqual(data["basic"]["height"], 450)

    @unittest_run_loop
    async def test_process_compress_endpoint(self):
        img_bytes = create_test_image(800, 600, "RGB")
        form = FormData()
        form.add_field("file", img_bytes, filename="photo.jpg", content_type="image/jpeg")
        options = {
            "target_size_kb": 50,
            "output_format": "JPEG",
            "strip_metadata": True,
        }
        form.add_field("options", json.dumps(options))

        resp = await self.client.request("POST", "/api/image/process", data=form)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertIn("token", data)
        self.assertIn("download_url", data)
        self.assertLessEqual(data["metrics"]["final_size_kb"], 60)

        # Test download endpoint
        dl_resp = await self.client.request("GET", data["download_url"])
        self.assertEqual(dl_resp.status, 200)
        self.assertEqual(dl_resp.headers.get("Content-Type"), "image/jpeg")
        dl_bytes = await dl_resp.read()
        self.assertGreater(len(dl_bytes), 0)

    @unittest_run_loop
    async def test_batch_process_endpoint(self):
        img1 = create_test_image(200, 200, "RGB")
        img2 = create_test_image(300, 300, "RGB")
        form = FormData()
        form.add_field("files", img1, filename="batch1.jpg", content_type="image/jpeg")
        form.add_field("files", img2, filename="batch2.jpg", content_type="image/jpeg")
        form.add_field("options", json.dumps({"output_format": "WEBP", "quality": 80}))

        resp = await self.client.request("POST", "/api/image/batch", data=form)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["successful"], 2)
        self.assertIn("zip_download_url", data)

        # Test zip download
        zip_resp = await self.client.request("GET", data["zip_download_url"])
        self.assertEqual(zip_resp.status, 200)
        self.assertEqual(zip_resp.headers.get("Content-Type"), "application/zip")
        zip_bytes = await zip_resp.read()
        self.assertGreater(len(zip_bytes), 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
