"""
Weather NLP City Extraction Test Suite for Alya.

Tests the extract_city_from_weather_query function which parses natural
language weather queries in English, Hindi, and Hinglish to extract the
actual city name, returning None for default location fallback.
"""

import unittest
from actions.actions import extract_city_from_weather_query


class TestWeatherCityExtraction(unittest.TestCase):
    """Tests for the weather NLP city extraction pipeline."""

    # ------------------------------------------------------------------
    # 1. No city mentioned → should return None (default location)
    # ------------------------------------------------------------------

    def test_hinglish_no_city_aj_kya_weather(self):
        """'Aj kya weather hai' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("Aj kya weather hai"))

    def test_hinglish_no_city_aaj_ka_weather(self):
        """'Aaj ka weather batao' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("Aaj ka weather batao"))

    def test_hinglish_no_city_aj_mausam(self):
        """'Aj mausam kaisa hai?' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("Aj mausam kaisa hai?"))

    def test_english_no_city_whats_the_weather(self):
        """'What's the weather?' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("What's the weather?"))

    def test_hinglish_no_city_mausam_kaisa(self):
        """'mausam kaisa hai?' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("mausam kaisa hai?"))

    def test_hinglish_no_city_weather_batao(self):
        """'weather batao' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("weather batao"))

    def test_hinglish_no_city_aaj_ka_mausam(self):
        """'aaj ka mausam kaisa hai' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("aaj ka mausam kaisa hai"))

    def test_hinglish_no_city_temperature_kya(self):
        """'temperature kya hai' → no city → None"""
        self.assertIsNone(extract_city_from_weather_query("temperature kya hai"))

    # ------------------------------------------------------------------
    # 2. Explicit city mentioned → should extract the city
    # ------------------------------------------------------------------

    def test_hinglish_kolkata_ka_weather(self):
        """'Kolkata ka weather kaisa hai?' → 'Kolkata'"""
        result = extract_city_from_weather_query("Kolkata ka weather kaisa hai?")
        self.assertEqual(result, "Kolkata")

    def test_english_weather_in_kolkata(self):
        """'Weather in Kolkata' → 'Kolkata'"""
        result = extract_city_from_weather_query("Weather in Kolkata")
        self.assertEqual(result, "Kolkata")

    def test_city_weather_today(self):
        """'Delhi weather today' → 'Delhi'"""
        result = extract_city_from_weather_query("Delhi weather today")
        self.assertEqual(result, "Delhi")

    def test_hinglish_mumbai_ka_mausam(self):
        """'Mumbai ka mausam' → 'Mumbai'"""
        result = extract_city_from_weather_query("Mumbai ka mausam")
        self.assertEqual(result, "Mumbai")

    def test_english_how_is_weather_in_delhi(self):
        """'how is the weather in Delhi' → 'Delhi'"""
        result = extract_city_from_weather_query("how is the weather in Delhi")
        self.assertEqual(result, "Delhi")

    def test_hinglish_delhi_me_mausam(self):
        """'Delhi me mausam kaisa hai' → 'Delhi'"""
        result = extract_city_from_weather_query("Delhi me mausam kaisa hai")
        # Should contain Delhi
        self.assertIsNotNone(result)
        self.assertIn("Delhi", result)

    def test_english_weather_forecast_new_york(self):
        """'weather in New York' → 'New York'"""
        result = extract_city_from_weather_query("weather in New York")
        self.assertEqual(result, "New York")

    # ------------------------------------------------------------------
    # 3. Slash command handling
    # ------------------------------------------------------------------

    def test_slash_weather_no_city(self):
        """/weather → None (default)"""
        self.assertIsNone(extract_city_from_weather_query("/weather"))

    def test_slash_weather_with_city(self):
        """/weather Mumbai → 'Mumbai'"""
        result = extract_city_from_weather_query("/weather Mumbai")
        self.assertEqual(result, "Mumbai")

    def test_slash_weather_with_city_multi_word(self):
        """/weather New Delhi → 'New Delhi'"""
        result = extract_city_from_weather_query("/weather New Delhi")
        self.assertEqual(result, "New Delhi")

    # ------------------------------------------------------------------
    # 4. Edge cases
    # ------------------------------------------------------------------

    def test_empty_string(self):
        """Empty string → None"""
        self.assertIsNone(extract_city_from_weather_query(""))

    def test_none_input(self):
        """None input → None"""
        self.assertIsNone(extract_city_from_weather_query(None))

    def test_whitespace_only(self):
        """Whitespace only → None"""
        self.assertIsNone(extract_city_from_weather_query("   "))

    def test_aaj_ka_weather_kya_hai(self):
        """'aaj ka weather kya hai' → None (no city)"""
        self.assertIsNone(extract_city_from_weather_query("aaj ka weather kya hai"))


if __name__ == "__main__":
    unittest.main()
