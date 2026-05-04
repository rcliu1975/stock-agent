#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show latest stock-agent backfill checkpoint status")
    parser.add_argument("--db", default="data/stock_agent.sqlite", help="SQLite database path")
    parser.add_argument("--market", default=None, help="Filter by market code")
    parser.add_argument("--symbol", default=None, help="Filter by symbol")
    parser.add_argument("--limit", type=int, default=20, help="Number of rows to show")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"database not found: {db_path}")
        return 1

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    query = """
    SELECT market, symbol, chunk_start, chunk_end, status, rows_written, last_trade_date, error_message, updated_at
    FROM backfill_checkpoints
    """
    filters: list[str] = []
    params: list[object] = []
    if args.market:
        filters.append("market = ?")
        params.append(args.market)
    if args.symbol:
        filters.append("symbol = ?")
        params.append(args.symbol)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    params.append(args.limit)

    print("Latest backfill checkpoints")
    for row in connection.execute(query, params):
        line = (
            f"{row['market']} {row['symbol']} {row['chunk_start']}..{row['chunk_end']} "
            f"status={row['status']} rows={row['rows_written']} last_trade_date={row['last_trade_date']}"
        )
        if row["error_message"]:
            line += f" error={row['error_message']}"
        print(line)

    print("")
    print("Checkpoint summary")
    summary_query = "SELECT status, COUNT(*) AS total, COALESCE(SUM(rows_written), 0) AS rows_total FROM backfill_checkpoints"
    summary_params: list[object] = []
    if filters:
        summary_query += " WHERE " + " AND ".join(filters)
        summary_params = params[:-1]
    summary_query += " GROUP BY status ORDER BY status"
    for row in connection.execute(summary_query, summary_params):
        print(f"{row['status']}: chunks={row['total']} rows={row['rows_total']}")

    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
