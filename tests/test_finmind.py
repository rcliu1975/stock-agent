import unittest
from unittest.mock import patch

from src.collectors import finmind


class FinMindTests(unittest.TestCase):
    def test_normalize_tw_symbol(self):
        self.assertEqual(finmind.normalize_tw_symbol("2330.TW"), "2330")
        self.assertEqual(finmind.normalize_tw_symbol("6488.TWO"), "6488")
        self.assertEqual(finmind.normalize_tw_symbol("2330"), "2330")

    def test_fetch_price_history_maps_finmind_payload(self):
        payload = {
            "status": 200,
            "data": [
                {
                    "date": "2026-01-02",
                    "open": 100,
                    "max": 110,
                    "min": 99,
                    "close": 108,
                    "Trading_Volume": 12345,
                    "Trading_money": 987654,
                }
            ],
        }
        with patch("src.collectors.finmind._request_dataset", return_value=payload):
            rows = finmind.fetch_price_history("2330.TW", "TW", offline=False, start_date="2026-01-01", end_date="2026-01-31")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "2330.TW")
        self.assertEqual(rows[0]["trade_date"], "2026-01-02")
        self.assertEqual(rows[0]["volume"], 12345)
        self.assertEqual(rows[0]["close"], 108.0)

    def test_fetch_stock_profile_uses_stock_info(self):
        with patch(
            "src.collectors.finmind._get_tw_stock_info",
            return_value={
                "2330": {
                    "stock_id": "2330",
                    "stock_name": "台積電",
                    "type": "twse",
                    "industry_category": "半導體業",
                }
            },
        ):
            profile = finmind.fetch_stock_profile("2330.TW", "TW")
        self.assertEqual(profile["name"], "台積電")
        self.assertEqual(profile["exchange"], "twse")
        self.assertEqual(profile["industry"], "半導體業")
