import tempfile
import unittest
from pathlib import Path

from src.core import database
from src.core.database import connect, initialize
from src.core.signal_backfill import backfill_signals


class SignalBackfillTests(unittest.TestCase):
    def test_signal_backfill_writes_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            stock = {"symbol": "2330.TW", "name": "台積電", "market": "TW", "exchange": "twse", "industry": "電子工業", "currency": "TWD"}
            database.upsert_stock(connection, stock)
            prices = [
                {"symbol": "2330.TW", "market": "TW", "trade_date": "2026-03-01", "open": 100, "high": 110, "low": 99, "close": 108, "volume": 1000, "turnover": 108000},
                {"symbol": "2330.TW", "market": "TW", "trade_date": "2026-03-02", "open": 108, "high": 112, "low": 107, "close": 111, "volume": 1200, "turnover": 133200},
            ]
            database.upsert_price_rows(connection, prices)
            for row in [
                {"symbol": "2330.TW", "market": "TW", "trade_date": "2026-03-01", "ma5": 108, "ma20": 107, "ma60": 100, "ma120": 95, "rsi14": 60, "volume_ma5": 1000, "volume_ma20": 900, "high_20d": 108, "low_20d": 90, "high_52w": 120, "low_52w": 80},
                {"symbol": "2330.TW", "market": "TW", "trade_date": "2026-03-02", "ma5": 109, "ma20": 108, "ma60": 100, "ma120": 95, "rsi14": 62, "volume_ma5": 1100, "volume_ma20": 950, "high_20d": 111, "low_20d": 90, "high_52w": 120, "low_52w": 80},
            ]:
                database.upsert_indicator(connection, row)
            database.upsert_fundamental(
                connection,
                {"symbol": "2330.TW", "market": "TW", "period": "2026-03-01", "eps": 8.0, "revenue_yoy": 20.0, "roe": 18.0, "gross_margin": 50.0, "debt_ratio": 25.0, "free_cash_flow": 80.0, "dividend_yield": 2.0},
            )
            connection.commit()
            config = {
                "market": "TW",
                "score_weights": {
                    "speculation": {"price_breakout": 25, "volume_breakout": 25, "price_alignment": 20, "social_heat": 20, "news_heat": 10},
                    "growth": {"revenue_yoy": 35, "eps_growth": 25, "gross_margin": 15, "roe": 15, "price_trend": 10},
                    "quality": {"roe_stability": 30, "dividend_stability": 20, "free_cash_flow": 20, "debt_ratio": 15, "drawdown_control": 15},
                },
                "universe": {"symbols": ["2330.TW"]},
            }
            results = backfill_signals(connection, config, "TW", ["2330.TW"], "2026-03-01", "2026-03-02", dry_run=False)
            count = connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].rows_written, 2)
            self.assertEqual(count, 2)
            connection.close()

    def test_signal_backfill_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            config = {
                "market": "TW",
                "score_weights": {
                    "speculation": {"price_breakout": 25, "volume_breakout": 25, "price_alignment": 20, "social_heat": 20, "news_heat": 10},
                    "growth": {"revenue_yoy": 35, "eps_growth": 25, "gross_margin": 15, "roe": 15, "price_trend": 10},
                    "quality": {"roe_stability": 30, "dividend_stability": 20, "free_cash_flow": 20, "debt_ratio": 15, "drawdown_control": 15},
                },
                "universe": {"symbols": ["2330.TW"]},
            }
            results = backfill_signals(connection, config, "TW", ["2330.TW"], "2026-03-01", "2026-03-02", dry_run=True)
            count = connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            self.assertEqual(results[0].status, "skipped")
            self.assertEqual(count, 0)
            connection.close()
