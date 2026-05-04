import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.pipeline import run_pipeline


class PipelineTests(unittest.TestCase):
    def test_pipeline_offline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            config = {
                "market": "TW",
                "market_name": "Taiwan Stock Market",
                "currency": "TWD",
                "database_path": str(tmp_path / "stock_agent.sqlite"),
                "universe": {"symbols": ["2330.TW", "2454.TW"]},
                "data_sources": {"price": "yfinance", "fundamentals": "builtin"},
                "score_weights": {
                    "speculation": {"price_breakout": 25, "volume_breakout": 25, "price_alignment": 20, "social_heat": 20, "news_heat": 10},
                    "growth": {"revenue_yoy": 35, "eps_growth": 25, "gross_margin": 15, "roe": 15, "price_trend": 10},
                    "quality": {"roe_stability": 30, "dividend_stability": 20, "free_cash_flow": 20, "debt_ratio": 15, "drawdown_control": 15},
                },
                "report": {"output_dir": str(tmp_path / "reports"), "telegram_enabled": False, "top_n": 10},
            }
            result = run_pipeline(config, offline=True, send_telegram_enabled=False)
            self.assertEqual(len(result.ranked_rows), 2)
            self.assertTrue(result.report_path.exists())

    def test_pipeline_continues_on_symbol_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            config = {
                "market": "TW",
                "market_name": "Taiwan Stock Market",
                "currency": "TWD",
                "database_path": str(tmp_path / "stock_agent.sqlite"),
                "universe": {"symbols": ["2330.TW", "2454.TW"]},
                "data_sources": {"price": "yfinance", "fundamentals": "builtin"},
                "score_weights": {
                    "speculation": {"price_breakout": 25, "volume_breakout": 25, "price_alignment": 20, "social_heat": 20, "news_heat": 10},
                    "growth": {"revenue_yoy": 35, "eps_growth": 25, "gross_margin": 15, "roe": 15, "price_trend": 10},
                    "quality": {"roe_stability": 30, "dividend_stability": 20, "free_cash_flow": 20, "debt_ratio": 15, "drawdown_control": 15},
                },
                "report": {"output_dir": str(tmp_path / "reports"), "telegram_enabled": False, "top_n": 10},
            }

            from src.collectors import yfinance_collector

            original_fetch = yfinance_collector.fetch_price_history

            def flaky_fetch(config: dict, symbol: str, market: str, offline: bool = False, start_date=None, end_date=None):
                if symbol == "2454.TW":
                    raise RuntimeError("simulated fetch failure")
                return original_fetch(symbol, market, offline=offline, start_date=start_date, end_date=end_date)

            with patch("src.core.pipeline.fetch_price_history", side_effect=flaky_fetch):
                previous_disable = logging.root.manager.disable
                logging.disable(logging.CRITICAL)
                try:
                    result = run_pipeline(config, offline=True, send_telegram_enabled=False)
                finally:
                    logging.disable(previous_disable)
            self.assertEqual(len(result.ranked_rows), 1)
            self.assertEqual(len(result.failures), 1)
            self.assertIn("2454.TW", result.failures[0])


if __name__ == "__main__":
    unittest.main()
