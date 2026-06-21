"""Unittest coverage for i18n input language and booking date parsing."""

import unittest
from datetime import datetime, timedelta

from agents import booking_agent
from i18n import detect_input_language


class TestI18nAndBookingLanguage(unittest.TestCase):
    def test_detect_input_language_chinese(self) -> None:
        self.assertEqual(detect_input_language("我想查明天下午練習室"), "zh")

    def test_detect_input_language_english(self) -> None:
        self.assertEqual(detect_input_language("Can I book a studio tomorrow afternoon?"), "en")

    def test_detect_input_language_fallback(self) -> None:
        self.assertEqual(detect_input_language("   ", fallback="en"), "en")

    def test_parse_date_tomorrow(self) -> None:
        expected = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        self.assertEqual(booking_agent._parse_date("Any studio tomorrow?"), expected)

    def test_parse_date_day_after_tomorrow(self) -> None:
        expected = (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d")
        self.assertEqual(booking_agent._parse_date("I need a room day after tomorrow"), expected)

    def test_parse_date_next_monday(self) -> None:
        result = booking_agent._parse_date("next Monday")
        self.assertIsNotNone(result)
        parsed = datetime.fromisoformat(result).date()
        self.assertEqual(parsed.weekday(), 0)

    def test_parse_date_month_day(self) -> None:
        result = booking_agent._parse_date("June 20")
        self.assertIsNotNone(result)
        parsed = datetime.fromisoformat(result).date()
        self.assertEqual(parsed.month, 6)
        self.assertEqual(parsed.day, 20)


if __name__ == "__main__":
    unittest.main()
