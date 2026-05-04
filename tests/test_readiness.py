import tempfile
import unittest
from pathlib import Path

from src.core.database import connect, initialize, replace_watchlist_snapshot, upsert_stock


class ReadinessTests(unittest.TestCase):
    def test_watchlist_snapshot_insert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            upsert_stock(connection, {"symbol": "2330.TW", "name": "台積電", "market": "TW", "exchange": "twse", "industry": "電子工業", "currency": "TWD", "is_active": 1})
            replace_watchlist_snapshot(
                connection,
                market="TW",
                strategy="tw_top_companies_etfs",
                snapshot_date="2026-05-05",
                rows=[
                    {
                        "market": "TW",
                        "strategy": "tw_top_companies_etfs",
                        "snapshot_date": "2026-05-05",
                        "symbol": "2330.TW",
                        "category": "company",
                        "rank_order": 1,
                        "metric_name": "avg_turnover",
                        "metric_value": 1000.0,
                    }
                ],
            )
            connection.commit()
            count = connection.execute("SELECT COUNT(*) FROM watchlist_snapshots").fetchone()[0]
            self.assertEqual(count, 1)
            connection.close()


if __name__ == "__main__":
    unittest.main()
