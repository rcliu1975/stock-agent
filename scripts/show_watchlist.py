#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show latest stock-agent watchlist snapshot")
    parser.add_argument("--db", default="data/stock_agent.sqlite", help="SQLite database path")
    parser.add_argument("--market", default="TW", help="Market code")
    parser.add_argument("--strategy", default="tw_top_companies_etfs", help="Strategy name")
    parser.add_argument("--category", default=None, help="Optional category filter: company or etf")
    parser.add_argument("--limit", type=int, default=100, help="Number of rows to show")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"database not found: {db_path}")
        return 1

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    latest_snapshot = connection.execute(
        """
        SELECT snapshot_date
        FROM watchlist_snapshots
        WHERE market = ? AND strategy = ?
        ORDER BY snapshot_date DESC
        LIMIT 1
        """,
        (args.market, args.strategy),
    ).fetchone()
    if not latest_snapshot:
        print("no watchlist snapshot found")
        connection.close()
        return 1

    snapshot_date = latest_snapshot["snapshot_date"]
    query = """
    SELECT symbol, category, rank_order, metric_name, metric_value
    FROM watchlist_snapshots
    WHERE market = ? AND strategy = ? AND snapshot_date = ?
    """
    params: list[object] = [args.market, args.strategy, snapshot_date]
    if args.category:
        query += " AND category = ?"
        params.append(args.category)
    query += " ORDER BY category, rank_order LIMIT ?"
    params.append(args.limit)

    print(f"Latest watchlist snapshot: {snapshot_date}")
    for row in connection.execute(query, params):
        print(
            f"{row['category']} rank={row['rank_order']} "
            f"{row['symbol']} {row['metric_name']}={row['metric_value']:.2f}"
        )
    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
