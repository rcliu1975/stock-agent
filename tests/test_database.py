import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.core.database import initialize


class DatabaseTests(unittest.TestCase):
    def test_initialize_migrates_existing_signals_table(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "stock_agent.sqlite"
            connection = sqlite3.connect(db_path)
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                CREATE TABLE signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    signal_date TEXT NOT NULL,
                    category TEXT,
                    speculation_score REAL,
                    growth_score REAL,
                    quality_score REAL,
                    social_heat_score REAL,
                    sentiment_score REAL,
                    risk_score REAL,
                    reason TEXT,
                    warning TEXT,
                    ai_summary TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, market, signal_date)
                )
                """
            )
            initialize(connection)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(signals)")}
            self.assertIn("action", columns)
            self.assertIn("confidence_score", columns)
            self.assertIn("stop_loss", columns)
            connection.close()


if __name__ == "__main__":
    unittest.main()
