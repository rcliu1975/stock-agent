import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

from src.collectors.finmind import fetch_tw_all_stock_universe, fetch_tw_stock_universe, select_tw_tracking_symbols
from src.core.database import activate_market_symbols, connect, deactivate_market_stocks, fetch_stocks, initialize, upsert_stock


class UniverseTests(unittest.TestCase):
    def test_fetch_tw_stock_universe_filters_exchange(self):
        payload = {
            "2330": {"stock_id": "2330", "stock_name": "台積電", "type": "twse", "industry_category": "半導體業"},
            "6488": {"stock_id": "6488", "stock_name": "環球晶", "type": "tpex", "industry_category": "半導體業"},
            "7777": {"stock_id": "7777", "stock_name": "興櫃樣本", "type": "rotc", "industry_category": "其他"},
            "0050": {"stock_id": "0050", "stock_name": "元大台灣50", "type": "twse", "industry_category": "ETF"},
            "01001T": {"stock_id": "01001T", "stock_name": "國泰投資級公司債", "type": "twse", "industry_category": "債券"},
        }
        with patch("src.collectors.finmind._get_tw_stock_info", return_value=payload):
            rows = fetch_tw_stock_universe(include_exchanges=("twse", "tpex"))
        self.assertEqual([row["symbol"] for row in rows], ["2330.TW", "6488.TWO"])

    def test_upsert_universe_rows_into_db(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            rows = [
                {"symbol": "2330.TW", "name": "台積電", "market": "TW", "exchange": "twse", "industry": "半導體業", "currency": "TWD"},
                {"symbol": "6488.TWO", "name": "環球晶", "market": "TW", "exchange": "tpex", "industry": "半導體業", "currency": "TWD"},
            ]
            for row in rows:
                upsert_stock(connection, row)
            connection.commit()
            count = connection.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
            self.assertEqual(count, 2)
            connection.close()

    def test_deactivate_market_stocks_keeps_rows_but_marks_inactive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            upsert_stock(connection, {"symbol": "2330.TW", "name": "台積電", "market": "TW", "exchange": "twse", "industry": "電子工業", "currency": "TWD"})
            upsert_stock(connection, {"symbol": "0050.TW", "name": "元大台灣50", "market": "TW", "exchange": "twse", "industry": "ETF", "currency": "TWD"})
            connection.commit()
            deactivate_market_stocks(connection, "TW")
            connection.commit()
            active_rows = fetch_stocks(connection, "TW")
            total_rows = connection.execute("SELECT COUNT(*) FROM stocks WHERE market='TW'").fetchone()[0]
            self.assertEqual(total_rows, 2)
            self.assertEqual(len(active_rows), 0)
            connection.close()

    def test_select_tw_tracking_symbols_keeps_companies_and_etfs(self):
        rows = [
            {"symbol": "2330.TW", "industry": "電子工業"},
            {"symbol": "0050.TW", "industry": "ETF"},
            {"symbol": "00632R.TW", "industry": "ETF"},
            {"symbol": "020000.TW", "industry": "ETN"},
        ]
        symbols = select_tw_tracking_symbols(rows, company_stock_id_pattern=r"^\d{4}$", exclude_industry_keywords=("ETN",))
        self.assertEqual(symbols, ["2330.TW", "0050.TW", "00632R.TW"])

    def test_fetch_tw_all_stock_universe_filters_non_tradable_ids(self):
        payload = {
            "2330": {"stock_id": "2330", "stock_name": "台積電", "type": "twse", "industry_category": "電子工業"},
            "00632R": {"stock_id": "00632R", "stock_name": "元大台灣50反1", "type": "twse", "industry_category": "ETF"},
            "TradingConsumersGoods": {"stock_id": "TradingConsumersGoods", "stock_name": "類股指數", "type": "twse", "industry_category": "指數"},
        }
        with patch("src.collectors.finmind._get_tw_stock_info", return_value=payload):
            rows = fetch_tw_all_stock_universe(include_exchanges=("twse",))
        self.assertEqual([row["symbol"] for row in rows], ["00632R.TW", "2330.TW"])

    def test_activate_market_symbols_marks_subset_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            upsert_stock(connection, {"symbol": "2330.TW", "name": "台積電", "market": "TW", "exchange": "twse", "industry": "電子工業", "currency": "TWD"})
            upsert_stock(connection, {"symbol": "0050.TW", "name": "元大台灣50", "market": "TW", "exchange": "twse", "industry": "ETF", "currency": "TWD"})
            deactivate_market_stocks(connection, "TW")
            activate_market_symbols(connection, "TW", ["0050.TW"])
            connection.commit()
            active_rows = fetch_stocks(connection, "TW")
            self.assertEqual([row["symbol"] for row in active_rows], ["0050.TW"])
            connection.close()

    def test_upsert_stock_respects_is_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            upsert_stock(connection, {"symbol": "2330.TW", "name": "台積電", "market": "TW", "exchange": "twse", "industry": "電子工業", "currency": "TWD", "is_active": 0})
            connection.commit()
            row = connection.execute("SELECT is_active FROM stocks WHERE symbol='2330.TW' AND market='TW'").fetchone()
            self.assertEqual(row[0], 0)
            connection.close()

    def test_sync_script_rejects_invalid_regex(self):
        repo_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [
                "python3",
                "scripts/sync_tw_universe.py",
                "--config",
                "config/config_tw.yaml",
                "--all-stock-id-pattern",
                r"^\d+[A-Z]?$",
                "--company-stock-id-pattern",
                "[",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Invalid regex pattern", result.stdout)


if __name__ == "__main__":
    unittest.main()
