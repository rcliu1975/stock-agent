import unittest

from src.core.indicators import latest_indicator_row, moving_average, relative_strength_index


class IndicatorTests(unittest.TestCase):
    def test_moving_average(self):
        self.assertEqual(moving_average([1, 2, 3, 4, 5], 5), 3.0)

    def test_relative_strength_index_range(self):
        rsi = relative_strength_index([1, 2, 3, 2, 4, 5, 6, 5, 6, 7, 8, 7, 8, 9, 10], 14)
        self.assertIsNotNone(rsi)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)

    def test_latest_indicator_row(self):
        prices = [
            {"trade_date": f"2026-01-{day:02d}", "close": float(day), "volume": 1000 + day}
            for day in range(1, 31)
        ]
        row = latest_indicator_row("2330.TW", "TW", prices)
        self.assertEqual(row["trade_date"], "2026-01-30")
        self.assertEqual(row["ma5"], 28.0)
        self.assertEqual(row["high_20d"], 30.0)


if __name__ == "__main__":
    unittest.main()
