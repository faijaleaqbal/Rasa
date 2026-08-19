"""
Unit & Regression Test Suite for Centralized Free-Only Multi-Provider LLM Service.

Validates:
1. Paid Groq route is rejected in FREE_ONLY mode
2. Free OpenRouter route is accepted
3. Paid OpenRouter route is rejected
4. Unknown/unverified route is rejected
5. Free vision route is accepted
6. Paid vision route is rejected
7. 429 rate limit still triggers fallback
8. 413 context reduction / aggressive trimming
9. Timeout still triggers fallback & circuit breaker
10. 5xx server error triggers fallback
11. Auth failure (401/403) cools down provider
12. All free providers down produces the safe response
13. Text model receiving image request redirects with failsafe
14. Non-vision model rejected for vision requests
15. End-to-end fallback chain with 100% zero-cost routes
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from actions.llm_provider import (
    LLMProviderManager,
    FreeRouteRegistry,
    RoutePricing,
    health_tracker,
    ContextManager,
    ALL_PROVIDERS_FAILED_MSG
)


class TestFreeLLMProviderManager(unittest.TestCase):

    def setUp(self):
        self._original_env = dict(os.environ)
        health_tracker._health.clear()
        os.environ["FREE_ONLY"] = "true"
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-key"
        os.environ["GROQ_API_KEY"] = "gsk_test_key"
        os.environ["NVIDIA_NIM_API_KEY"] = "nvapi_test_key"
        os.environ["TEXT_PRIMARY_MODEL"] = "google/gemma-4-26b-a4b-it:free"
        os.environ["TEXT_FALLBACK_MODELS"] = "nvidia/nemotron-3-ultra-550b-a55b:free, dots-studio/dots-3-note-preview:free, openrouter/free"
        os.environ["VISION_PRIMARY_MODEL"] = "google/gemma-4-26b-a4b-it:free"
        os.environ["VISION_FALLBACK_MODELS"] = "dots-studio/dots-3-note-preview:free, openrouter/free"

    def tearDown(self):
        health_tracker._health.clear()
        os.environ.clear()
        os.environ.update(self._original_env)

    # 1. Paid Groq route is rejected in FREE_ONLY mode
    def test_paid_groq_route_is_rejected_in_free_only_mode(self):
        allowed, reason = FreeRouteRegistry.validate_route("Groq", "openai/gpt-oss-20b", is_free_only=True)
        self.assertFalse(allowed)
        self.assertIn("REJECTED", reason)
        self.assertIn("Paid/credit-metered", reason)

        allowed_120b, _ = FreeRouteRegistry.validate_route("Groq", "openai/gpt-oss-120b", is_free_only=True)
        self.assertFalse(allowed_120b)

        allowed_qwen, _ = FreeRouteRegistry.validate_route("Groq", "qwen/qwen3.6-27b", is_free_only=True)
        self.assertFalse(allowed_qwen)

    # 2. Free OpenRouter route is accepted
    def test_free_openrouter_route_is_accepted(self):
        allowed, reason = FreeRouteRegistry.validate_route("OpenRouter", "google/gemma-4-26b-a4b-it:free", is_free_only=True)
        self.assertTrue(allowed)
        self.assertIn("ACCEPTED", reason)

        allowed_nemo, _ = FreeRouteRegistry.validate_route("OpenRouter", "nvidia/nemotron-3-ultra-550b-a55b:free", is_free_only=True)
        self.assertTrue(allowed_nemo)

        allowed_dots, _ = FreeRouteRegistry.validate_route("OpenRouter", "dots-studio/dots-3-note-preview:free", is_free_only=True)
        self.assertTrue(allowed_dots)

        allowed_router, _ = FreeRouteRegistry.validate_route("OpenRouter", "openrouter/free", is_free_only=True)
        self.assertTrue(allowed_router)

    # 3. Paid OpenRouter route is rejected
    def test_paid_openrouter_route_is_rejected(self):
        paid_models = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-flash",
            "meta-llama/llama-3.3-70b-instruct"
        ]
        for pm in paid_models:
            allowed, reason = FreeRouteRegistry.validate_route("OpenRouter", pm, is_free_only=True)
            self.assertFalse(allowed, f"Model {pm} should have been rejected")
            self.assertIn("REJECTED", reason)

    # 4. Unknown route is rejected
    def test_unknown_route_is_rejected(self):
        allowed, reason = FreeRouteRegistry.validate_route("UnknownProvider", "unknown-model-xyz", is_free_only=True)
        self.assertFalse(allowed)
        self.assertIn("Unknown or unverified", reason)

    # 5. Free vision route is accepted
    def test_free_vision_route_is_accepted(self):
        allowed, reason = FreeRouteRegistry.validate_route("OpenRouter", "google/gemma-4-26b-a4b-it:free", is_free_only=True, is_vision=True)
        self.assertTrue(allowed)
        self.assertIn("ACCEPTED", reason)

        allowed_dots, _ = FreeRouteRegistry.validate_route("OpenRouter", "dots-studio/dots-3-note-preview:free", is_free_only=True, is_vision=True)
        self.assertTrue(allowed_dots)

    # 6. Paid vision route is rejected
    def test_paid_vision_route_is_rejected(self):
        # Paid model requested for vision
        allowed_paid, reason_paid = FreeRouteRegistry.validate_route("OpenRouter", "openai/gpt-4o", is_free_only=True, is_vision=True)
        self.assertFalse(allowed_paid)
        self.assertIn("REJECTED", reason_paid)

        # NVIDIA NIM credit-metered vision model requested in FREE_ONLY mode
        allowed_nim, reason_nim = FreeRouteRegistry.validate_route("NVIDIA", "meta/llama-3.2-11b-vision-instruct", is_free_only=True, is_vision=True)
        self.assertFalse(allowed_nim)
        self.assertIn("REJECTED", reason_nim)

        # Text-only free model requested for vision
        allowed_text, reason_text = FreeRouteRegistry.validate_route("OpenRouter", "nvidia/nemotron-3-ultra-550b-a55b:free", is_free_only=True, is_vision=True)
        self.assertFalse(allowed_text)
        self.assertIn("does not support multimodal", reason_text)

    # 7. 429 rate limit triggers fallback
    @patch("requests.post")
    def test_429_triggers_fallback_to_next_free_model(self, mock_post):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.text = "Rate limit exceeded"

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "choices": [{"message": {"content": "Response from second free model"}}]
        }

        # Model 1 returns 429 -> Next model in free chain returns 200
        mock_post.side_effect = [resp_429, resp_200]

        messages = [{"role": "user", "content": "Hello"}]
        text, tools, provider = LLMProviderManager.call_chat_completion(messages)

        self.assertEqual(text, "Response from second free model")
        self.assertIn("OpenRouter", provider)

    # 8. 413 context reduction and retry
    @patch("requests.post")
    def test_413_context_reduction_and_retry(self, mock_post):
        resp_413 = MagicMock()
        resp_413.status_code = 413
        resp_413.text = "Payload too large"

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "choices": [{"message": {"content": "Responded after trimming"}}]
        }

        mock_post.side_effect = [resp_413, resp_200]

        large_messages = [{"role": "user", "content": "A" * 15000}]
        text, _, provider = LLMProviderManager.call_chat_completion(large_messages)

        self.assertEqual(text, "Responded after trimming")
        self.assertEqual(mock_post.call_count, 2)

    # 9. Timeout triggers fallback
    @patch("requests.post")
    def test_timeout_triggers_fallback(self, mock_post):
        import requests
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "choices": [{"message": {"content": "Success after timeout fallback"}}]
        }

        mock_post.side_effect = [
            requests.exceptions.Timeout("Connection timed out"),
            resp_200
        ]

        messages = [{"role": "user", "content": "Timeout test"}]
        text, _, provider = LLMProviderManager.call_chat_completion(messages)

        self.assertEqual(text, "Success after timeout fallback")

    # 10. 5xx server error triggers fallback
    @patch("requests.post")
    def test_5xx_server_error_fallback(self, mock_post):
        resp_500 = MagicMock()
        resp_500.status_code = 500
        resp_500.text = "Internal Server Error"

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "choices": [{"message": {"content": "Success after 500"}}]
        }

        mock_post.side_effect = [resp_500, resp_500, resp_200]

        messages = [{"role": "user", "content": "500 test"}]
        text, _, provider = LLMProviderManager.call_chat_completion(messages)

        self.assertEqual(text, "Success after 500")

    # 11. Auth failure 401/403 skips provider
    @patch("requests.post")
    def test_auth_failure_cooldown(self, mock_post):
        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.text = "Invalid API Key"

        mock_post.return_value = resp_401

        messages = [{"role": "user", "content": "Auth test"}]
        text, _, provider = LLMProviderManager.call_chat_completion(messages)

        self.assertEqual(text, ALL_PROVIDERS_FAILED_MSG)
        self.assertFalse(health_tracker.is_healthy("OpenRouter"))

    # 12. All free providers down produces safe response
    @patch("requests.post")
    def test_all_free_providers_down_produces_safe_response(self, mock_post):
        resp_503 = MagicMock()
        resp_503.status_code = 503
        resp_503.text = "Service Unavailable"

        mock_post.return_value = resp_503

        messages = [{"role": "user", "content": "All fail"}]
        text, _, provider = LLMProviderManager.call_chat_completion(messages)

        self.assertEqual(text, ALL_PROVIDERS_FAILED_MSG)
        self.assertEqual(provider, "None")

    # 13. Text model receiving image request redirects with failsafe
    def test_text_model_receiving_image_redirects_failsafe(self):
        msg_with_image = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Look at this image"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}
            ]
        }]
        text, _, provider = LLMProviderManager.call_chat_completion(msg_with_image)
        self.assertEqual(text, ALL_PROVIDERS_FAILED_MSG)
        self.assertEqual(provider, "InvalidCall")

    # 14. Free-only text chain contains ZERO paid routes
    def test_text_chain_has_zero_paid_routes(self):
        chain = LLMProviderManager.get_text_fallback_chain()
        for p in chain:
            for m in p["models"]:
                allowed, reason = FreeRouteRegistry.validate_route(p["name"], m, is_free_only=True)
                self.assertTrue(allowed, f"Found non-free model {p['name']}/{m}: {reason}")

    # 15. Free-only vision chain contains ZERO paid routes
    def test_vision_chain_has_zero_paid_routes(self):
        chain = LLMProviderManager.get_vision_fallback_chain()
        for p in chain:
            for m in p["models"]:
                allowed, reason = FreeRouteRegistry.validate_route(p["name"], m, is_free_only=True, is_vision=True)
                self.assertTrue(allowed, f"Found invalid vision model {p['name']}/{m}: {reason}")


if __name__ == "__main__":
    unittest.main()
