import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.core.backfill import backfill_history, chunk_date_ranges
from src.core.database import connect, initialize


class BackfillTests(unittest.TestCase):
    def test_chunk_date_ranges(self):
        ranges = chunk_date_ranges("2026-01-01", "2026-01-10", 4)
        self.assertEqual(
            ranges,
            [
                ("2026-01-01", "2026-01-04"),
                ("2026-01-05", "2026-01-08"),
                ("2026-01-09", "2026-01-10"),
            ],
        )

    def test_backfill_offline_writes_prices_and_indicators(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            results = backfill_history(
                connection=connection,
                config={"data_sources": {"price": "yfinance"}},
                market="TW",
                currency="TWD",
                symbols=["2330.TW"],
                start_date="2026-03-01",
                end_date="2026-04-30",
                chunk_size_days=30,
                offline=True,
                resume=True,
                dry_run=False,
            )
            self.assertTrue(results)
            price_count = connection.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
            indicator_count = connection.execute("SELECT COUNT(*) FROM technical_indicators").fetchone()[0]
            checkpoint_count = connection.execute("SELECT COUNT(*) FROM backfill_checkpoints WHERE status = 'success'").fetchone()[0]
            self.assertGreater(price_count, 0)
            self.assertGreater(indicator_count, 0)
            self.assertEqual(checkpoint_count, 3)
            connection.close()

    def test_backfill_dry_run_only_updates_checkpoints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = connect(db_path)
            initialize(connection)
            results = backfill_history(
                connection=connection,
                config={"data_sources": {"price": "yfinance"}},
                market="TW",
                currency="TWD",
                symbols=["2330.TW"],
                start_date="2026-03-01",
                end_date="2026-03-15",
                chunk_size_days=10,
                offline=True,
                resume=True,
                dry_run=True,
            )
            self.assertEqual(len(results), 2)
            price_count = connection.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
            indicator_count = connection.execute("SELECT COUNT(*) FROM technical_indicators").fetchone()[0]
            checkpoint_count = connection.execute("SELECT COUNT(*) FROM backfill_checkpoints WHERE status = 'dry_run'").fetchone()[0]
            self.assertEqual(price_count, 0)
            self.assertEqual(indicator_count, 0)
            self.assertEqual(checkpoint_count, 2)
            connection.close()
