"""
Tests for Live Fuel Price Check (Petrol, Diesel & CNG) in Alya Rasa Assistant.
"""

import unittest
from unittest.mock import MagicMock
from actions.actions import extract_city_from_fuel_query, ActionLLMResponse
from actions.skills_indian_markets import get_fuel_rates
from actions.commands import handle_slash_command


class TestFuelRates(unittest.TestCase):

    def test_extract_city_from_fuel_query(self):
        cases = {
            "/fuel": None,
            "/fuel Delhi": "Delhi",
            "/petrol Kolkata": "Kolkata",
            "/diesel in Pune": "Pune",
            "/cng Mumbai": "Mumbai",
            "petrol price kya hai": None,
            "delhi me petrol kitna hai": "delhi",
            "aaj ka petrol rate in Kolkata": "Kolkata",
            "what is the petrol price in Mumbai": "Mumbai",
            "Pune fuel rate": "Pune",
            "cng price in Ahmedabad": "Ahmedabad",
            "malda petrol diesel dam": "malda",
            "Lucknow me aaj petrol ka daam kya hai": "Lucknow",
        }
        for q, expected in cases.items():
            result = extract_city_from_fuel_query(q)
            self.assertEqual(result, expected, f"Failed for input: {q}")

    def test_get_fuel_rates_format_and_data(self):
        for city in ["Delhi", "Kolkata", "Malda", "Pune", "Mumbai", "NonExistentPlaceXYZ"]:
            res = get_fuel_rates(city)
            self.assertIn("⛽", res)
            self.assertIn("Petrol", res)
            self.assertIn("Diesel", res)
            self.assertIn("CNG", res)
            self.assertIn("Date", res)
            self.assertIn("OMCs", res)

    def test_slash_command_fuel_routing(self):
        for cmd in ["/fuel", "/fuel Delhi", "/petrol Kolkata", "/diesel Pune", "/cng Mumbai"]:
            out = handle_slash_command(cmd, "test_user", "test_chat")
            self.assertTrue(out.get("handled"), f"Command {cmd} was not handled")
            text = out.get("text", "")
            self.assertIn("⛽", text)
            self.assertIn("Petrol", text)
            self.assertIn("Diesel", text)

    def test_action_llm_response_fuel_fast_path(self):
        dispatcher = MagicMock()
        tracker = MagicMock()
        tracker.latest_message = {"text": "delhi me petrol kitna hai"}
        tracker.sender_id = "test_user_fuel"
        tracker.current_state.return_value = {}

        action = ActionLLMResponse()
        action.run(dispatcher, tracker, {})

        dispatcher.utter_message.assert_called_once()
        called_text = dispatcher.utter_message.call_args[1].get("text", "")
        self.assertIn("⛽", called_text)
        self.assertIn("Delhi", called_text)
        self.assertIn("Petrol", called_text)


if __name__ == "__main__":
    unittest.main()
