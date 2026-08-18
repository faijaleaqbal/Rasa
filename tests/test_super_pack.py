import os
import tempfile
import unittest
from PIL import Image

from actions import skills_super_pack as superpack
from actions.commands import handle_slash_command


class TestSuperPackSkills(unittest.TestCase):
    """Tests all new skills and slash commands."""

    def test_voice_note_generation(self):
        ok, fpath, msg = superpack.generate_voice_note("नमस्ते, आप कैसे हैं?")
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(fpath))
        self.assertTrue(fpath.endswith(".mp3"))
        if os.path.exists(fpath):
            os.remove(fpath)

    def test_aqi_formatting(self):
        res = superpack.get_air_quality_index("Delhi")
        self.assertIn("Air Quality Index", res)
        self.assertIn("Health Advisory", res)

    def test_exif_inspector_and_stripper(self):
        # Create a dummy image
        tmp_img = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(tmp_img.name, "JPEG")
        tmp_img.close()

        # Inspect
        ok, msg, _ = superpack.inspect_or_strip_image_exif(tmp_img.name, strip_exif=False)
        self.assertTrue(ok)
        self.assertIn("EXIF", msg)

        # Strip
        ok_strip, msg_strip, clean_path = superpack.inspect_or_strip_image_exif(tmp_img.name, strip_exif=True)
        self.assertTrue(ok_strip)
        self.assertIsNotNone(clean_path)
        self.assertTrue(os.path.exists(clean_path))

        # Cleanup
        if os.path.exists(tmp_img.name):
            os.remove(tmp_img.name)
        if clean_path and os.path.exists(clean_path):
            os.remove(clean_path)

    def test_ipo_data(self):
        res = superpack.get_live_ipo_data()
        self.assertIn("IPO", res)

    def test_phishing_scanner(self):
        res_safe = superpack.scan_url_phishing_security("https://google.com")
        self.assertIn("Safety Score", res_safe)

        res_risk = superpack.scan_url_phishing_security("http://192.168.1.1/bank-login.php")
        self.assertIn("Phishing", res_risk)

    def test_post_office_lookup(self):
        res = superpack.get_post_office_branches("732101")
        self.assertIn("India Post", res)
        self.assertIn("732101", res)

    def test_ping_host(self):
        res = superpack.ping_server_health("8.8.8.8")
        self.assertIn("Ping", res)
        self.assertIn("Resolved", res)

    def test_slash_command_dispatch(self):
        res_aqi = handle_slash_command("/aqi Kolkata", "user_1", "chat_1")
        self.assertTrue(res_aqi["handled"])
        self.assertIn("Air Quality", res_aqi["text"])

        res_ipo = handle_slash_command("/ipo", "user_1", "chat_1")
        self.assertTrue(res_ipo["handled"])
        self.assertIn("IPO", res_ipo["text"])

        res_post = handle_slash_command("/postoffice 110001", "user_1", "chat_1")
        self.assertTrue(res_post["handled"])
        self.assertIn("India Post", res_post["text"])

        res_wayback = handle_slash_command("/wayback https://google.com", "user_1", "chat_1")
        self.assertTrue(res_wayback["handled"])
        self.assertIn("Wayback Machine", res_wayback["text"])

        res_compare = handle_slash_command("/compare Python vs Java", "user_1", "chat_1")
        self.assertTrue(res_compare["handled"])
        self.assertTrue(len(res_compare["text"]) > 20)

        res_solve = handle_slash_command("/solve What is the derivative of x^2?", "user_1", "chat_1")
        self.assertTrue(res_solve["handled"])
        self.assertIn("2x", res_solve["text"])


if __name__ == "__main__":
    unittest.main()
