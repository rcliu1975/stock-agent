import tempfile
import unittest
from pathlib import Path

from src.core.database import connect, initialize, replace_watchlist_snapshot
from src.core.universe import classify_symbol_category, resolve_symbols


class WatchlistTests(unittest.TestCase):
    def test_classify_symbol_category(self):
        self.assertEqual(classify_symbol_category("ETF"), "etf")
        self.assertEqual(classify_symbol_category("上櫃ETF"), "etf")
        self.assertEqual(classify_symbol_category("電子工業"), "company")

    def test_resolve_symbols_prefers_db_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            replace_watchlist_snapshot(
                connection,
                market="TW",
                strategy="tw_top_companies_etfs",
                snapshot_date="2026-05-04",
                rows=[
                    {
                        "market": "TW",
                        "strategy": "tw_top_companies_etfs",
                        "snapshot_date": "2026-05-04",
                        "symbol": "2330.TW",
                        "category": "company",
                        "rank_order": 1,
                        "metric_name": "avg_turnover",
                        "metric_value": 1000.0,
                    },
                    {
                        "market": "TW",
                        "strategy": "tw_top_companies_etfs",
                        "snapshot_date": "2026-05-04",
                        "symbol": "0050.TW",
                        "category": "etf",
                        "rank_order": 1,
                        "metric_name": "avg_turnover",
                        "metric_value": 500.0,
                    },
                ],
            )
            connection.commit()
            config = {
                "market": "TW",
                "universe": {
                    "source": "db_top_liquidity",
                    "db_strategy": "tw_top_companies_etfs",
                    "symbols": ["2317.TW"],
                },
            }
            self.assertEqual(resolve_symbols(config, connection), ["2330.TW", "0050.TW"])
            connection.close()

    def test_resolve_symbols_falls_back_to_manual(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            config = {
                "market": "TW",
                "universe": {
                    "source": "db_top_liquidity",
                    "db_strategy": "tw_top_companies_etfs",
                    "symbols": ["2317.TW"],
                },
            }
            self.assertEqual(resolve_symbols(config, connection), ["2317.TW"])
            connection.close()


if __name__ == "__main__":
    unittest.main()
