import tempfile
import unittest
from pathlib import Path

from src.core.database import connect, fetch_stocks, initialize, upsert_stock
from src.core.universe import classify_symbol_category


class MarketBackfillTests(unittest.TestCase):
    def test_fetch_stocks_returns_active_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            upsert_stock(connection, {"symbol": "2330.TW", "name": "台積電", "market": "TW", "exchange": "twse", "industry": "電子工業", "currency": "TWD"})
            connection.execute(
                """
                INSERT INTO stocks(symbol, name, market, exchange, industry, currency, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, market) DO UPDATE SET is_active=excluded.is_active
                """,
                ("0050.TW", "元大台灣50", "TW", "twse", "ETF", "TWD", 0),
            )
            connection.commit()
            rows = fetch_stocks(connection, "TW")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "2330.TW")
            connection.close()

    def test_classify_symbol_category_etf(self):
        self.assertEqual(classify_symbol_category("ETF"), "etf")


if __name__ == "__main__":
    unittest.main()
