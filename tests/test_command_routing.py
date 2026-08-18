"""
Automated Test Suite for Alya Command Routing and Dispatcher Priority.
Verifies that:
1. Every registered slash command is intercepted and executed by its handler.
2. Bot username suffixes (e.g. /compress@AlyaBot) are stripped and handled.
3. Unknown slash commands return a command-not-found message and NEVER reach the generic AI fallback.
4. Normal text messages (e.g. "Hi buddy") route to normal AI conversation.
5. Media attachments / session caches are correctly preserved.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from actions import commands as cmd_handler
from actions import command_registry as reg


class TestCommandRouting(unittest.TestCase):

    def setUp(self):
        self.user_id = "8433855679"
        self.chat_id = "8433855679"

    def test_compress_command_routing_without_args(self):
        """Input '/compress' should execute compress handler and return usage, not generic AI."""
        res = cmd_handler.handle_slash_command("/compress", self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("Compressor Usage", res.get("text", ""))

    def test_compress_command_with_args(self):
        """Input '/compress file.jpg' should pass argument to compressor."""
        with patch("actions.skills_super_pack.compress_media_file") as mock_comp:
            mock_comp.return_value = (True, "Compressed 50%", "/tmp/file_compressed.jpg")
            res = cmd_handler.handle_slash_command("/compress /tmp/test.jpg", self.user_id, self.chat_id)
            self.assertTrue(res.get("handled"))
            self.assertEqual(res.get("file_path"), "/tmp/file_compressed.jpg")

    def test_compress_with_bot_suffix(self):
        """Input '/compress@Alya_Rasa_Bot' should strip bot name and route to compress handler."""
        res = cmd_handler.handle_slash_command("/compress@Alya_Rasa_Bot", self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("Compressor Usage", res.get("text", ""))

    def test_passport_command_routing(self):
        """Input '/passport' should execute passport handler, not generic AI."""
        res = cmd_handler.handle_slash_command("/passport", self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("Passport", res.get("text", ""))

    def test_imagetools_command_routing(self):
        """Input '/imagetools' should execute image studio guide."""
        res = cmd_handler.handle_slash_command("/imagetools", self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("Image Tools Studio", res.get("text", ""))

    def test_help_and_menu_command_routing(self):
        """Input '/help' and '/menu' should return canonical help menu."""
        res_help = cmd_handler.handle_slash_command("/help", self.user_id, self.chat_id)
        self.assertTrue(res_help.get("handled"))
        self.assertIn("Alya AI Assistant", res_help.get("text", ""))

        res_menu = cmd_handler.handle_slash_command("/menu", self.user_id, self.chat_id)
        self.assertTrue(res_menu.get("handled"))
        self.assertIn("Alya AI Assistant", res_menu.get("text", ""))

    def test_unknown_command_returns_command_not_found(self):
        """Unknown slash command should return helpful error and NOT route to AI."""
        res = cmd_handler.handle_slash_command("/doesnotexist123", self.user_id, self.chat_id)
        self.assertTrue(res.get("handled"))
        self.assertIn("Unknown Command", res.get("text", ""))
        self.assertIn("/doesnotexist123", res.get("text", ""))

    def test_normal_text_does_not_intercept(self):
        """Normal conversational text ('Hi buddy') must NOT be handled as slash command."""
        res = cmd_handler.handle_slash_command("Hi buddy", self.user_id, self.chat_id)
        self.assertFalse(res.get("handled"))

        res2 = cmd_handler.handle_slash_command("What is the capital of India?", self.user_id, self.chat_id)
        self.assertFalse(res2.get("handled"))

    def test_media_attachment_preservation(self):
        """Passing attachment_path should automatically be used by /compress."""
        test_file = "/tmp/test_alya_image.jpg"
        with open(test_file, "w") as f:
            f.write("fake-image-content")

        try:
            with patch("actions.skills_super_pack.compress_media_file") as mock_comp:
                mock_comp.return_value = (True, "Compressed OK", "/tmp/out.jpg")
                res = cmd_handler.handle_slash_command("/compress", self.user_id, self.chat_id, attachment_path=test_file)
                self.assertTrue(res.get("handled"))
                mock_comp.assert_called_once_with(test_file)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_two_step_media_workflow(self):
        """Uploading file first, then calling bare /compress should use cached media."""
        test_file = "/tmp/two_step_test.jpg"
        with open(test_file, "w") as f:
            f.write("image-content-user-a")

        try:
            # 1. User uploads file (cached)
            cmd_handler.set_last_user_media("user_100", test_file)

            # 2. User sends bare '/compress'
            with patch("actions.skills_super_pack.compress_media_file") as mock_comp:
                mock_comp.return_value = (True, "Compressed 2-step OK", "/tmp/out_2step.jpg")
                res = cmd_handler.handle_slash_command("/compress", "user_100", "user_100")
                self.assertTrue(res.get("handled"))
                mock_comp.assert_called_once_with(test_file)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_user_isolation_no_cross_user_media_leakage(self):
        """User A's media must never be accessible to User B."""
        file_a = "/tmp/user_a_file.jpg"
        file_b = "/tmp/user_b_file.jpg"
        with open(file_a, "w") as f:
            f.write("image-A")
        with open(file_b, "w") as f:
            f.write("image-B")

        try:
            cmd_handler.set_last_user_media("user_A", file_a)
            cmd_handler.set_last_user_media("user_B", file_b)

            with patch("actions.skills_super_pack.compress_media_file") as mock_comp:
                mock_comp.return_value = (True, "OK", "/tmp/out.jpg")

                # User A runs /compress -> processes file_a
                cmd_handler.handle_slash_command("/compress", "user_A", "user_A")
                mock_comp.assert_called_with(file_a)

                # User B runs /compress -> processes file_b
                cmd_handler.handle_slash_command("/compress", "user_B", "user_B")
                mock_comp.assert_called_with(file_b)

                # User C (no uploads) runs /compress -> gets usage prompt, does NOT touch A or B
                res_c = cmd_handler.handle_slash_command("/compress", "user_C", "user_C")
                self.assertTrue(res_c.get("handled"))
                self.assertIn("Compressor Usage", res_c.get("text", ""))
        finally:
            if os.path.exists(file_a):
                os.remove(file_a)
            if os.path.exists(file_b):
                os.remove(file_b)

    def test_cache_handles_missing_file_gracefully(self):
        """If cached file was deleted from disk, return usage without crashing."""
        non_existent = "/tmp/already_deleted_12345.jpg"
        cmd_handler._LAST_USER_MEDIA["user_ghost"] = {"path": non_existent, "ts": 100000}
        res = cmd_handler.handle_slash_command("/compress", "user_ghost", "user_ghost")
        self.assertTrue(res.get("handled"))
        self.assertIn("Compressor Usage", res.get("text", ""))


class TestDispatcherPriorityIntegration(unittest.TestCase):
    """
    Tests dispatcher priority:
    1. Slash commands execute handler (handled=True) -> generic AI is NOT called.
    2. Conversational text returns handled=False -> generic AI IS called.
    """

    def test_slash_command_bypasses_generic_ai(self):
        commands_to_test = ["/compress", "/passport", "/imagetools", "/help", "/weather", "/solve", "/unknowncommand"]
        for cmd in commands_to_test:
            res = cmd_handler.handle_slash_command(cmd, "8433855679", "8433855679")
            self.assertTrue(res.get("handled"), f"Command {cmd} failed to be intercepted before AI!")

    def test_conversational_text_reaches_generic_ai(self):
        conversations = ["Hi buddy", "How are you today?", "Tell me a story", "Explain quantum physics"]
        for text in conversations:
            res = cmd_handler.handle_slash_command(text, "8433855679", "8433855679")
            self.assertFalse(res.get("handled"), f"Text '{text}' was incorrectly intercepted as a command!")


if __name__ == "__main__":
    unittest.main()
