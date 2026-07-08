from datetime import datetime
import unittest

from app.runtime_config import format_interval, parse_interval_seconds, parse_notify_window


class RuntimeConfigTests(unittest.TestCase):
    def test_notify_window_contains_regular_range(self) -> None:
        window = parse_notify_window("08:00-23:30")

        self.assertTrue(window.contains(datetime(2026, 7, 8, 12, 0)))
        self.assertFalse(window.contains(datetime(2026, 7, 8, 7, 59)))

    def test_notify_window_contains_cross_midnight_range(self) -> None:
        window = parse_notify_window("22:00-02:00")

        self.assertTrue(window.contains(datetime(2026, 7, 8, 23, 0)))
        self.assertTrue(window.contains(datetime(2026, 7, 9, 1, 30)))
        self.assertFalse(window.contains(datetime(2026, 7, 8, 12, 0)))

    def test_parse_notify_window_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            parse_notify_window("8:00-23:30")
        with self.assertRaises(ValueError):
            parse_notify_window("24:00-23:30")

    def test_parse_interval_seconds(self) -> None:
        self.assertEqual(parse_interval_seconds("15m"), 900)
        self.assertEqual(parse_interval_seconds("1h"), 3600)
        self.assertEqual(format_interval(900), "15m")

    def test_parse_interval_seconds_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            parse_interval_seconds("15")
        with self.assertRaises(ValueError):
            parse_interval_seconds("0m")


if __name__ == "__main__":
    unittest.main()
