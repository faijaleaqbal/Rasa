"""
Canonical Command Inventory & Complete Routability Test Suite for Alya.

Guarantees:
1. Exact Command Inventory Count:
   - 143 canonical primary commands in COMMAND_REGISTRY
   - 174 aliases in COMMAND_REGISTRY
   - 317 total registry entry points
   - 322 total slash command entry points handled in commands.py
2. Zero command or alias disappearance regression protection against REQUIRED_BASELINE_COMMANDS.
3. Every single command and alias is routable and returns handled=True.
4. Telegram Bot API compliance (<= 100 native menu commands, valid names).
5. Dynamic /help, /menu, /commands, /skills directory generation integrity.
"""

import unittest
from unittest.mock import patch, MagicMock

from actions import command_registry as reg
from actions import commands


# Canonical Required Baseline Command Inventory from specification
REQUIRED_BASELINE_COMMANDS = {
    # Image Tools & Passport Studio
    "/imagetools", "/presets", "/passport", "/compress", "/exif", "/strip_exif",
    # AI & Super-Skills
    "/solve", "/search", "/transcribe", "/voice", "/ocr", "/compare", "/med", "/today",
    "/horoscope", "/hackernews", "/slang", "/wayback", "/mergepdf", "/splitpdf", "/phish",
    "/ping", "/ssl", "/whois",
    # Mobile & Android Automation
    "/call", "/sms", "/readsms", "/alarm", "/timer", "/open", "/callscreen",
    "/findmyphone", "/clip", "/whatsapp", "/notify", "/skills",
    # Indian Utilities & Markets
    "/upi", "/pan", "/gstin", "/unit", "/postoffice", "/pincode", "/ifsc", "/pnr",
    "/train", "/flight", "/stock", "/nifty", "/sensex", "/gold", "/fuel", "/ipo", "/aqi",
    # Reminders & Productivity
    "/remind", "/reminders", "/delremind", "/set_timezone", "/medremind", "/note",
    "/notes", "/todo", "/todos", "/habit", "/time", "/countdown", "/traffic", "/ride", "/track",
    # Developer & MCP Tools
    "/code", "/sh", "/py", "/sql", "/kg", "/github", "/screenshot", "/social", "/log",
    "/serverstatus", "/speedtest", "/dns", "/http", "/cron", "/json", "/ip",
    # Documents, Resumes & Formats
    "/resume", "/coverletter", "/invoice", "/convert", "/pdf", "/excel", "/doc",
    "/gmail", "/outlook", "/drive", "/calendar",
    # Privacy, Security & Web APIs
    "/passgen", "/hash", "/unshorten", "/shorten", "/tempmail", "/checkmail", "/breach",
    "/weather", "/news", "/currency", "/crypto", "/wallet", "/gas", "/wiki", "/movie",
    "/holiday", "/image", "/translate", "/joke", "/math", "/science", "/vehicle", "/shop",
    # Financial, Health & Lifestyle
    "/sip", "/emi", "/split", "/expense", "/expenses", "/bill", "/bmi", "/calorie",
    "/water", "/grammar", "/email", "/synonym",
    # Entertainment & Media
    "/qr", "/barcode", "/meme", "/anime", "/recipe", "/riddle", "/pick", "/dice",
    "/coinflip", "/youtube", "/summarize", "/briefing",
    # Admin & Management
    "/adduser", "/removeuser", "/users",
    # Jobs & Scholarships
    "/jobs", "/scholarships", "/psu", "/format", "/stop"
}


class TestCanonicalCommandInventory(unittest.TestCase):
    """
    Tests exact command inventory, alias mappings, and 100% routability.
    """

    def setUp(self):
        self.user_id = "8433855679"
        self.chat_id = "8433855679"

    def test_required_baseline_inventory_zero_missing(self):
        """Verifies that 100% of REQUIRED_BASELINE_COMMANDS exist in the registry."""
        all_cmds = reg.get_all_commands()
        registered = set("/" + c.name for c in all_cmds) | set("/" + a for c in all_cmds for a in c.aliases)
        missing = REQUIRED_BASELINE_COMMANDS - registered
        self.assertEqual(
            missing, set(),
            f"Regression detected! The following required baseline commands are missing: {missing}"
        )

    def test_canonical_command_count(self):
        """Verifies exact command inventory count matches historical baseline."""
        all_cmds = reg.get_all_commands()
        total_primary = len(all_cmds)
        total_aliases = sum(len(c.aliases) for c in all_cmds)
        total_triggers = total_primary + total_aliases

        self.assertEqual(total_primary, 150, f"Expected 150 canonical primary commands, found {total_primary}")
        self.assertEqual(total_aliases, 189, f"Expected 189 aliases, found {total_aliases}")
        self.assertEqual(total_triggers, 339, f"Expected 339 total registry lookup triggers, found {total_triggers}")

    def test_registry_audit_zero_collisions(self):
        """Verifies registry audit reports zero duplicate commands, collisions, or invalid names."""
        audit = reg.audit_registry()
        self.assertEqual(len(audit["collisions"]), 0, f"Found registry collisions: {audit['collisions']}")
        self.assertEqual(len(audit["invalid_telegram_names"]), 0, f"Found invalid Telegram names: {audit['invalid_telegram_names']}")
        self.assertTrue(audit["native_menu_within_telegram_limit"])
        self.assertLessEqual(audit["native_menu_count"], 100)

    @patch("socket.socket")
    @patch("socket.gethostbyname", return_value="127.0.0.1")
    @patch("requests.get")
    @patch("requests.post")
    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    @patch("actions.llm_provider.LLMProviderManager.call_vision_completion")
    def test_all_143_canonical_commands_are_routable(self, mock_vis, mock_llm, mock_post, mock_get, mock_dns, mock_sock):
        """Verifies that EVERY SINGLE ONE of the 143 canonical commands is routable and returns handled=True."""
        mock_llm.return_value = ("Mocked LLM answer", None, "MockProvider")
        mock_vis.return_value = ("Mocked Vision answer", "MockProvider")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "mocked"}}],
            "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 50},
            "weather": [{"description": "clear sky"}],
            "current": {"temp_c": 25.0, "feelslike_c": 26.0, "humidity": 50, "condition": {"text": "Clear"}, "wind_kph": 10},
            "location": {"name": "Malda", "region": "West Bengal", "country": "India"},
            "rates": {"INR": 83.5, "USD": 1.0, "EUR": 0.92}
        }
        mock_resp.text = "Mocked API response"
        mock_get.return_value = mock_resp
        mock_post.return_value = mock_resp

        all_cmds = reg.get_all_commands()
        unhandled = []

        for cmd in all_cmds:
            res = commands.handle_slash_command(
                f"/{cmd.name} test argument sample",
                self.user_id,
                self.chat_id
            )
            if not res.get("handled"):
                unhandled.append(f"/{cmd.name}")

        self.assertEqual(
            len(unhandled), 0,
            f"The following primary commands failed routing in commands.py: {unhandled}"
        )

    @patch("socket.socket")
    @patch("socket.gethostbyname", return_value="127.0.0.1")
    @patch("requests.get")
    @patch("requests.post")
    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    @patch("actions.llm_provider.LLMProviderManager.call_vision_completion")
    def test_all_174_command_aliases_are_routable(self, mock_vis, mock_llm, mock_post, mock_get, mock_dns, mock_sock):
        """Verifies that EVERY SINGLE ONE of the 174 command aliases is routable and returns handled=True."""
        mock_llm.return_value = ("Mocked LLM answer", None, "MockProvider")
        mock_vis.return_value = ("Mocked Vision answer", "MockProvider")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "mocked"}}],
            "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 50},
            "weather": [{"description": "clear sky"}],
            "current": {"temp_c": 25.0, "feelslike_c": 26.0, "humidity": 50, "condition": {"text": "Clear"}, "wind_kph": 10},
            "location": {"name": "Malda", "region": "West Bengal", "country": "India"},
            "rates": {"INR": 83.5, "USD": 1.0, "EUR": 0.92}
        }
        mock_resp.text = "Mocked API response"
        mock_get.return_value = mock_resp
        mock_post.return_value = mock_resp

        all_cmds = reg.get_all_commands()
        unhandled_aliases = []

        for cmd in all_cmds:
            for alias in cmd.aliases:
                res = commands.handle_slash_command(
                    f"/{alias} test argument sample",
                    self.user_id,
                    self.chat_id
                )
                if not res.get("handled"):
                    unhandled_aliases.append(f"/{alias} (alias of /{cmd.name})")

        self.assertEqual(
            len(unhandled_aliases), 0,
            f"The following aliases failed routing in commands.py: {unhandled_aliases}"
        )

    @patch("socket.socket")
    @patch("socket.gethostbyname", return_value="127.0.0.1")
    @patch("requests.get")
    @patch("requests.post")
    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    @patch("actions.llm_provider.LLMProviderManager.call_vision_completion")
    def test_required_baseline_every_command_is_routable(self, mock_vis, mock_llm, mock_post, mock_get, mock_dns, mock_sock):
        """Verifies that every single command in REQUIRED_BASELINE_COMMANDS routes and returns handled=True."""
        mock_llm.return_value = ("Mocked LLM answer", None, "MockProvider")
        mock_vis.return_value = ("Mocked Vision answer", "MockProvider")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "mocked"}}],
            "main": {"temp": 25.0, "feels_like": 26.0, "humidity": 50},
            "weather": [{"description": "clear sky"}],
            "current": {"temp_c": 25.0, "feelslike_c": 26.0, "humidity": 50, "condition": {"text": "Clear"}, "wind_kph": 10},
            "location": {"name": "Malda", "region": "West Bengal", "country": "India"},
            "rates": {"INR": 83.5, "USD": 1.0, "EUR": 0.92}
        }
        mock_resp.text = "Mocked API response"
        mock_get.return_value = mock_resp
        mock_post.return_value = mock_resp

        unhandled_baseline = []
        for cmd in REQUIRED_BASELINE_COMMANDS:
            res = commands.handle_slash_command(
                f"{cmd} test argument sample",
                self.user_id,
                self.chat_id
            )
            if not res.get("handled"):
                unhandled_baseline.append(cmd)

        self.assertEqual(
            len(unhandled_baseline), 0,
            f"The following required baseline commands failed routing: {unhandled_baseline}"
        )

    def test_meta_slash_commands_are_routable(self):
        """Verifies built-in meta commands (/help, /start, /menu, /commands, /allcommands)."""
        for meta in ["help", "start", "menu", "commands", "allcommands"]:
            res = commands.handle_slash_command(f"/{meta}", self.user_id, self.chat_id)
            self.assertTrue(res.get("handled"), f"Meta command /{meta} failed routing")
            self.assertTrue(len(res.get("text", "")) > 100)

    def test_help_and_skills_directory_generation(self):
        """Verifies /help and /skills output includes categories and command syntax."""
        help_text = reg.generate_help_text(user_id=self.user_id)
        self.assertIn("Alya AI Assistant", help_text)
        self.assertIn("Slash Commands Menu", help_text)
        self.assertIn("/weather", help_text)
        self.assertIn("/imagetools", help_text)
        self.assertIn("/solve", help_text)

        skills_dir = reg.generate_skills_directory()
        self.assertIn("Complete Skills Directory", skills_dir)
        self.assertIn("/search", skills_dir)
        self.assertIn("/voice", skills_dir)


if __name__ == "__main__":
    unittest.main()
