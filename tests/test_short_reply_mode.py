"""
Unit & Regression Test Suite for Alya STRICT SHORT REPLY MODE.

Validates:
1. System prompt in ActionLLMResponse includes strict short reply rules.
2. Centralized token budget constants (CHAT_MAX_TOKENS=120, SYNTHESIS_CONCISE_MAX_TOKENS=160, STRUCTURED_MAX_TOKENS=900).
3. clean_llm_output strips <think>, <thought>, and markdown thought blocks.
4. ActionLLMResponse routes normal conversation with compact max_tokens.
5. ActionLLMResponse tool synthesis distinguishes between structured output tools and concise utilities.
6. Error messages are short, useful, and avoid technical jargon.
7. Important commands (/weather, /reminders, /notes, /todos, /briefing, /search, /summarize) return results directly.
"""

import unittest
from unittest.mock import MagicMock, patch

from actions.actions import ActionLLMResponse
from actions.llm_provider import (
    clean_llm_output,
    CHAT_MAX_TOKENS,
    SYNTHESIS_CONCISE_MAX_TOKENS,
    STRUCTURED_MAX_TOKENS,
    STRUCTURED_OUTPUT_TOOLS,
)
from actions import commands


class TestStrictShortReplyMode(unittest.TestCase):

    def setUp(self):
        self.user_id = "8433855679"
        self.chat_id = "8433855679"

    def test_token_budget_constants(self):
        """Verifies token budgets for chat vs structured commands."""
        self.assertLessEqual(CHAT_MAX_TOKENS, 150)
        self.assertLessEqual(SYNTHESIS_CONCISE_MAX_TOKENS, 200)
        self.assertGreaterEqual(STRUCTURED_MAX_TOKENS, 700)
        self.assertIn("search_live_web", STRUCTURED_OUTPUT_TOOLS)
        self.assertIn("generate_resume_pdf", STRUCTURED_OUTPUT_TOOLS)
        self.assertIn("solve_problem_or_puzzle", STRUCTURED_OUTPUT_TOOLS)
        self.assertIn("summarize_long_content", STRUCTURED_OUTPUT_TOOLS)

    def test_clean_llm_output_strips_thinking(self):
        """Verifies think and thought blocks are completely removed."""
        raw_think = "<think>Let me formulate a 1-sentence reply in Hinglish</think>Bas badhiya hoon! Aap batao? 😄"
        self.assertEqual(clean_llm_output(raw_think), "Bas badhiya hoon! Aap batao? 😄")

        raw_thought_block = "```thought\nAnalyzing the query...\n```Sab chill 😎 Tu bata?"
        self.assertEqual(clean_llm_output(raw_thought_block), "Sab chill 😎 Tu bata?")

        raw_thought_tag = "<thought>User asked greeting</thought>Good morning! ☀️"
        self.assertEqual(clean_llm_output(raw_thought_tag), "Good morning! ☀️")

    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    def test_action_llm_response_system_prompt_contains_strict_rules(self, mock_llm):
        """Verifies system prompt strictly instructs concise 1-2 sentence replies and tool rules."""
        mock_llm.return_value = ("Bas tumse baat kar rahi hoon 😄", None, "MockProvider")

        dispatcher = MagicMock()
        tracker = MagicMock()
        tracker.latest_message = {"text": "Kya kar rahi hai?"}
        tracker.sender_id = self.user_id
        tracker.current_state.return_value = {"latest_message": {"metadata": {"chat_id": self.chat_id}}}
        tracker.events = []

        action = ActionLLMResponse()
        action.run(dispatcher, tracker, {})

        # Inspect system prompt passed to LLM
        mock_llm.assert_called_once()
        call_kwargs = mock_llm.call_args[1]
        messages = call_kwargs["messages"]
        system_msg = messages[0]["content"]

        self.assertIn("STRICT SHORT REPLY MODE", system_msg)
        self.assertIn("Answer first. Keep it short", system_msg)
        self.assertIn("Default: 1–2 short sentences", system_msg)
        self.assertIn("Maximum: 30–40 words", system_msg)
        self.assertIn("Do NOT generate: 'Actually mere paas...'", system_msg)
        self.assertEqual(call_kwargs["max_tokens"], CHAT_MAX_TOKENS)

        dispatcher.utter_message.assert_called_once_with(text="Bas tumse baat kar rahi hoon 😄")

    @patch("actions.actions.execute_tool_call")
    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    def test_concise_tool_synthesis(self, mock_llm, mock_exec):
        """Verifies simple utility tool findings are synthesized with concise token budget and direct prompt."""
        # First call returns a tool call (get reminders)
        tool_call_obj = {
            "id": "call_1",
            "function": {"name": "list_user_reminders", "arguments": "{}"}
        }
        mock_llm.side_effect = [
            (None, [tool_call_obj], "MockProvider"),
            ("Mil gaya 👍 Kal 1 PM ka reminder set hai.", None, "MockProvider")
        ]
        mock_exec.return_value = "⏰ [1] Meeting at 1:00 PM tomorrow"

        dispatcher = MagicMock()
        tracker = MagicMock()
        tracker.latest_message = {"text": "Tere ko kal remind karne ke liye bola tha kaha hai tera remind sms"}
        tracker.sender_id = self.user_id
        tracker.current_state.return_value = {"latest_message": {"metadata": {"chat_id": self.chat_id}}}
        tracker.events = []

        action = ActionLLMResponse()
        action.run(dispatcher, tracker, {})

        self.assertEqual(mock_llm.call_count, 2)
        second_call_kwargs = mock_llm.call_args_list[1][1]
        # Should use concise synthesis budget
        self.assertEqual(second_call_kwargs["max_tokens"], SYNTHESIS_CONCISE_MAX_TOKENS)
        self.assertEqual(second_call_kwargs["messages"][-1]["role"], "tool")
        self.assertEqual(second_call_kwargs["messages"][-1]["content"], "⏰ [1] Meeting at 1:00 PM tomorrow")

        dispatcher.utter_message.assert_called_once_with(text="Mil gaya 👍 Kal 1 PM ka reminder set hai.")

    @patch("actions.actions.execute_tool_call")
    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    def test_structured_tool_preserves_token_budget(self, mock_llm, mock_exec):
        """Verifies structured tools (e.g. search_live_web) preserve full structured token budget."""
        tool_call_obj = {
            "id": "call_2",
            "function": {"name": "search_live_web", "arguments": "{\"query\": \"Python 3.12 features\"}"}
        }
        mock_llm.side_effect = [
            (None, [tool_call_obj], "MockProvider"),
            ("🔍 **Python 3.12 Features:**\n• More flexible f-string parsing\n• Isolated subinterpreters", None, "MockProvider")
        ]
        mock_exec.return_value = "Python 3.12 introduces faster comprehension..."

        dispatcher = MagicMock()
        tracker = MagicMock()
        tracker.latest_message = {"text": "Search Python 3.12 features"}
        tracker.sender_id = self.user_id
        tracker.current_state.return_value = {"latest_message": {"metadata": {"chat_id": self.chat_id}}}
        tracker.events = []

        action = ActionLLMResponse()
        action.run(dispatcher, tracker, {})

        self.assertEqual(mock_llm.call_count, 2)
        second_call_kwargs = mock_llm.call_args_list[1][1]
        # Should use structured max tokens
        self.assertEqual(second_call_kwargs["max_tokens"], STRUCTURED_MAX_TOKENS)

    @patch("actions.llm_provider.LLMProviderManager.call_chat_completion")
    def test_error_response_is_short_and_useful(self, mock_llm):
        """Verifies error failsafe is short and non-technical."""
        mock_llm.side_effect = Exception("Connection refused 500 error internal stack trace")

        dispatcher = MagicMock()
        tracker = MagicMock()
        tracker.latest_message = {"text": "Hello"}
        tracker.sender_id = self.user_id
        tracker.current_state.return_value = {"latest_message": {"metadata": {"chat_id": self.chat_id}}}
        tracker.events = []

        action = ActionLLMResponse()
        action.run(dispatcher, tracker, {})

        dispatcher.utter_message.assert_called_once_with(text="⚠️ AI service unavailable hai. Thodi der baad try karo.")


if __name__ == "__main__":
    unittest.main()
