"""
Automated Test Suite for Telegram UX Features (Typing Indicator & Message Reactions).
Covers typing startup, periodic refresh, clean cancellation on success/error/timeout,
random emoji selection, message deduplication, fail-safe isolation, and concurrency.
"""

import os
import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from addons.telegram_ux import (
    TelegramTypingScope,
    SyncTelegramTypingScope,
    async_send_chat_action,
    sync_send_chat_action,
    async_set_message_reaction,
    sync_set_message_reaction,
    is_typing_enabled,
    is_reaction_enabled,
    get_reaction_emojis,
    _REACTED_MESSAGES,
)


class TestTelegramUXFeatures(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        _REACTED_MESSAGES.clear()
        os.environ["TELEGRAM_BOT_TOKEN"] = "123456:FAKE_TOKEN_FOR_TESTING"
        os.environ["TELEGRAM_TYPING_ENABLED"] = "true"
        os.environ["TELEGRAM_RANDOM_REACTION_ENABLED"] = "true"
        os.environ["TELEGRAM_REACTION_EMOJIS"] = "👍,❤️,😂,😎,🔥,👀,🤖,✨,😊,😁,🙌,💯,🚀,🫡,👌"
        os.environ["TELEGRAM_TYPING_INTERVAL_SECONDS"] = "0.05"

    def tearDown(self):
        _REACTED_MESSAGES.clear()

    async def test_typing_starts_on_enter_and_cleans_up_on_success(self):
        with patch("addons.telegram_ux.async_send_chat_action", new_callable=AsyncMock) as mock_action:
            mock_action.return_value = True

            scope = TelegramTypingScope(chat_id="12345", interval=0.05)
            self.assertIsNone(scope._task)

            async with scope:
                # Should have sent immediate typing action
                mock_action.assert_called_once_with("12345", action="typing", bot_token=os.getenv("TELEGRAM_BOT_TOKEN"), session=None)
                self.assertIsNotNone(scope._task)
                self.assertFalse(scope._task.done())

            # After exiting scope, task must be cancelled and cleared
            self.assertIsNone(scope._task)

    async def test_typing_continues_and_refreshes_during_long_operation(self):
        with patch("addons.telegram_ux.async_send_chat_action", new_callable=AsyncMock) as mock_action:
            mock_action.return_value = True

            # Use 0.03s interval so it fires multiple times quickly
            scope = TelegramTypingScope(chat_id="12345", interval=0.03)

            async with scope:
                await asyncio.sleep(0.1)  # Allow at least 2-3 refresh ticks

            # 1 initial + at least 2 background refreshes
            self.assertGreaterEqual(mock_action.call_count, 2)
            self.assertIsNone(scope._task)

    async def test_typing_cleanup_after_exception(self):
        with patch("addons.telegram_ux.async_send_chat_action", new_callable=AsyncMock) as mock_action:
            mock_action.return_value = True

            scope = TelegramTypingScope(chat_id="12345", interval=0.05)

            with self.assertRaises(ValueError):
                async with scope:
                    self.assertIsNotNone(scope._task)
                    raise ValueError("Simulated AI Failure!")

            # Guaranteed cleanup even after exception
            self.assertIsNone(scope._task)

    async def test_typing_cleanup_after_timeout(self):
        with patch("addons.telegram_ux.async_send_chat_action", new_callable=AsyncMock) as mock_action:
            mock_action.return_value = True

            scope = TelegramTypingScope(chat_id="12345", interval=0.05)

            async def timed_operation():
                async with scope:
                    await asyncio.sleep(0.5)

            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(timed_operation(), timeout=0.08)

            # Guaranteed cleanup after timeout cancellation
            self.assertIsNone(scope._task)

    async def test_random_emoji_is_selected_from_pool(self):
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            emoji_pool = get_reaction_emojis()
            chosen = await async_set_message_reaction(chat_id="12345", message_id=101)

            self.assertIsNotNone(chosen)
            self.assertIn(chosen, emoji_pool)

    async def test_exactly_one_reaction_per_user_message(self):
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            # First reaction should succeed
            res1 = await async_set_message_reaction(chat_id="12345", message_id=999)
            self.assertIsNotNone(res1)
            self.assertEqual(mock_post.call_count, 1)

            # Second call for the same message should be ignored (deduplicated)
            res2 = await async_set_message_reaction(chat_id="12345", message_id=999)
            self.assertIsNone(res2)
            self.assertEqual(mock_post.call_count, 1)

    async def test_reaction_failure_does_not_break_pipeline(self):
        with patch("aiohttp.ClientSession.post", side_effect=Exception("Network error")):
            # Should catch exception internally and return None without raising
            result = await async_set_message_reaction(chat_id="12345", message_id=505)
            self.assertIsNone(result)

    async def test_disabled_configuration(self):
        os.environ["TELEGRAM_TYPING_ENABLED"] = "false"
        os.environ["TELEGRAM_RANDOM_REACTION_ENABLED"] = "false"

        self.assertFalse(is_typing_enabled())
        self.assertFalse(is_reaction_enabled())

        with patch("addons.telegram_ux.async_send_chat_action", new_callable=AsyncMock) as mock_action:
            scope = TelegramTypingScope(chat_id="12345")
            async with scope:
                pass
            mock_action.assert_not_called()

        res = await async_set_message_reaction(chat_id="12345", message_id=777)
        self.assertIsNone(res)

    async def test_concurrent_users_get_independent_typing_and_reactions(self):
        with patch("addons.telegram_ux.async_send_chat_action", new_callable=AsyncMock) as mock_action:
            mock_action.return_value = True

            with patch("aiohttp.ClientSession.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_post.return_value.__aenter__.return_value = mock_response

                scope1 = TelegramTypingScope(chat_id="user_1", interval=0.03)
                scope2 = TelegramTypingScope(chat_id="user_2", interval=0.03)

                async def user_workflow(scope, msg_id):
                    async with scope:
                        rxn = await async_set_message_reaction(chat_id=scope.chat_id, message_id=msg_id)
                        await asyncio.sleep(0.08)
                        return rxn

                res1, res2 = await asyncio.gather(
                    user_workflow(scope1, 1001),
                    user_workflow(scope2, 2002)
                )

                self.assertIsNotNone(res1)
                self.assertIsNotNone(res2)
                self.assertIsNone(scope1._task)
                self.assertIsNone(scope2._task)


class TestSyncTelegramUX(unittest.TestCase):
    def setUp(self):
        _REACTED_MESSAGES.clear()
        os.environ["TELEGRAM_BOT_TOKEN"] = "123456:FAKE_TOKEN"
        os.environ["TELEGRAM_TYPING_ENABLED"] = "true"
        os.environ["TELEGRAM_RANDOM_REACTION_ENABLED"] = "true"

    def test_sync_typing_scope_lifecycle(self):
        with patch("addons.telegram_ux.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_post.return_value = mock_resp

            scope = SyncTelegramTypingScope(chat_id="9988", interval=0.05)
            with scope:
                self.assertIsNotNone(scope._thread)
                self.assertTrue(scope._thread.is_alive())
                import time
                time.sleep(0.12)

            # Thread should be joined and stopped
            self.assertIsNone(scope._thread)
            self.assertGreaterEqual(mock_post.call_count, 2)

    def test_sync_reaction_success_and_fallback(self):
        with patch("addons.telegram_ux.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = '{"ok": true, "result": true}'
            mock_post.return_value = mock_resp

            res = sync_set_message_reaction(chat_id="12345", message_id=303, emoji="👍")
            self.assertEqual(res, "👍")
            self.assertEqual(mock_post.call_count, 1)

    def test_sync_reaction_fallback_on_invalid_emoji(self):
        with patch("addons.telegram_ux.requests.post") as mock_post:
            # First attempt fails with REACTION_INVALID, second attempt (fallback) succeeds
            fail_resp = MagicMock()
            fail_resp.status_code = 400
            fail_resp.text = '{"ok": false, "description": "Bad Request: REACTION_INVALID"}'

            ok_resp = MagicMock()
            ok_resp.status_code = 200
            ok_resp.text = '{"ok": true, "result": true}'

            mock_post.side_effect = [fail_resp, ok_resp]

            res = sync_set_message_reaction(chat_id="12345", message_id=304, emoji="🔥")
            self.assertIsNotNone(res)
            self.assertGreaterEqual(mock_post.call_count, 2)

    def test_sync_reaction_permission_denied(self):
        with patch("addons.telegram_ux.requests.post") as mock_post:
            fail_resp = MagicMock()
            fail_resp.status_code = 403
            fail_resp.text = '{"ok": false, "description": "Forbidden: bot was blocked by the user"}'
            mock_post.return_value = fail_resp

            res = sync_set_message_reaction(chat_id="12345", message_id=305)
            self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()

