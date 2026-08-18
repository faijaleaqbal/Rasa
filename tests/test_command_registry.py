"""
Automated Test Suite for Alya Canonical Command Registry.
Verifies single-source-of-truth integrity, category consistency, alias uniqueness,
Telegram Bot API menu limits, and admin permission security.
"""

import os
import unittest
from actions import command_registry as reg
from actions import commands as cmd_handler
from actions import db as app_db


class TestCommandRegistry(unittest.TestCase):

    def test_registry_audit_integrity(self):
        """Audit registry for duplicate names, alias collisions, and naming standards."""
        stats = reg.audit_registry()
        self.assertEqual(stats["collisions"], [], f"Command collisions found: {stats['collisions']}")
        self.assertEqual(stats["invalid_telegram_names"], [], f"Invalid Telegram command names: {stats['invalid_telegram_names']}")
        self.assertTrue(stats["native_menu_within_telegram_limit"], f"Native menu has {stats['native_menu_count']} commands, exceeds 100 limit!")
        self.assertGreaterEqual(stats["total_canonical_commands"], 90, "Registry missing canonical commands!")

    def test_get_command_by_name_and_aliases(self):
        """Verify primary names and aliases resolve correctly."""
        cmd = reg.get_command_by_name("weather")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.name, "weather")

        # Test alias resolution
        alias_cmd = reg.get_command_by_name("voicenote")
        self.assertIsNotNone(alias_cmd)
        self.assertEqual(alias_cmd.name, "voice")

        # Non-existent command
        self.assertIsNone(reg.get_command_by_name("non_existent_command_xyz"))

    def test_generate_help_text(self):
        """Verify dynamic help text contains all expected categories and commands."""
        help_text = reg.generate_help_text()
        self.assertIn("Alya AI Assistant", help_text)
        self.assertIn("🖼️ Image Tools & Passport Studio", help_text)
        self.assertIn("🤖 AI & Super-Skills", help_text)
        self.assertIn("📱 Mobile & Android Automation", help_text)
        self.assertIn("🇮🇳 Indian Utilities & Markets", help_text)
        self.assertIn("⏱️ Reminders & Productivity", help_text)
        self.assertIn("💻 Developer & MCP Tools", help_text)
        self.assertIn("📁 Documents, Resumes & Formats", help_text)
        self.assertIn("🔐 Privacy, Security & Web APIs", help_text)
        self.assertIn("💰 Financial, Health & Lifestyle", help_text)
        self.assertIn("🎮 Entertainment & Media", help_text)
        self.assertIn("👥 Admin & Management", help_text)

        # Check key commands in help
        self.assertIn("/imagetools", help_text)
        self.assertIn("/solve", help_text)
        self.assertIn("/weather", help_text)
        self.assertIn("/remind", help_text)

    def test_generate_skills_directory(self):
        """Verify skills directory contains clean list of commands."""
        skills_dir = reg.generate_skills_directory()
        self.assertIn("Complete Skills Directory", skills_dir)
        self.assertIn("`/weather`", skills_dir)
        self.assertIn("`/solve`", skills_dir)
        self.assertIn("`/imagetools`", skills_dir)

    def test_native_bot_commands_telegram_spec(self):
        """Verify native Telegram commands meet all API constraints."""
        bot_cmds = reg.get_native_bot_commands()
        self.assertLessEqual(len(bot_cmds), 100)
        self.assertGreaterEqual(len(bot_cmds), 50)

        # 'help' must always be present
        cmd_names = [c["command"] for c in bot_cmds]
        self.assertIn("help", cmd_names)

        # No duplicate names in the native menu
        self.assertEqual(len(cmd_names), len(set(cmd_names)), "Duplicate command in native menu!")

        # All descriptions must be non-empty and under 256 characters
        for c in bot_cmds:
            self.assertTrue(1 <= len(c["command"]) <= 32, f"Invalid command length: {c['command']}")
            self.assertTrue(3 <= len(c["description"]) <= 256, f"Invalid description length for {c['command']}")

    def test_admin_commands_access_control(self):
        """Verify admin commands require admin authorization."""
        # Unauthorized user
        fake_user = "9999999999"
        res_add = cmd_handler.handle_slash_command("/adduser 12345", fake_user, fake_user)
        self.assertTrue(res_add.get("handled"))
        self.assertIn("Access Denied", res_add.get("text", ""))

        res_del = cmd_handler.handle_slash_command("/removeuser 12345", fake_user, fake_user)
        self.assertTrue(res_del.get("handled"))
        self.assertIn("Access Denied", res_del.get("text", ""))

        res_users = cmd_handler.handle_slash_command("/users", fake_user, fake_user)
        self.assertTrue(res_users.get("handled"))
        self.assertIn("Access Denied", res_users.get("text", ""))

    def test_help_and_menu_slash_commands_dispatch(self):
        """Verify /help, /menu, /commands, /skills, /directory all dispatch properly."""
        user_id = "8433855679"
        for cmd_name in ["/help", "/menu", "/commands", "/allcommands", "/start"]:
            res = cmd_handler.handle_slash_command(cmd_name, user_id, user_id)
            self.assertTrue(res.get("handled"), f"Command {cmd_name} was not handled!")
            self.assertIn("Alya AI Assistant", res.get("text", ""))

        for cmd_name in ["/skills", "/directory", "/allskills"]:
            res = cmd_handler.handle_slash_command(cmd_name, user_id, user_id)
            self.assertTrue(res.get("handled"), f"Command {cmd_name} was not handled!")
            self.assertIn("Complete Skills Directory", res.get("text", ""))


if __name__ == "__main__":
    unittest.main()
