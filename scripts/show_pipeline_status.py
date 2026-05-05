#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show latest stock-agent pipeline status")
    parser.add_argument("--db", default="data/stock_agent.sqlite", help="SQLite database path")
    parser.add_argument("--market", default=None, help="Filter by market code")
    parser.add_argument("--limit", type=int, default=5, help="Number of rows to show")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"database not found: {db_path}")
        return 1

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    signal_columns = {row["name"] for row in connection.execute("PRAGMA table_info(signals)")}
    has_decision_columns = {"action", "confidence_score", "entry_price", "stop_loss", "take_profit"}.issubset(signal_columns)

    run_query = """
    SELECT market, run_date, status, processed_count, success_count, failed_count, report_path
    FROM pipeline_runs
    """
    if has_decision_columns:
        signal_query = """
        SELECT signal_date, symbol, market, category, action, confidence_score, entry_price, stop_loss, take_profit,
               speculation_score, growth_score, quality_score
        FROM signals
        """
    else:
        signal_query = """
        SELECT signal_date, symbol, market, category, NULL AS action, NULL AS confidence_score,
               NULL AS entry_price, NULL AS stop_loss, NULL AS take_profit,
               speculation_score, growth_score, quality_score
        FROM signals
        """
    parameters: list[object] = []
    if args.market:
        run_query += " WHERE market = ?"
        signal_query += " WHERE market = ?"
        parameters.append(args.market)

    run_query += " ORDER BY id DESC LIMIT ?"
    if has_decision_columns:
        signal_query += " ORDER BY signal_date DESC, CASE WHEN action IS NULL THEN 1 ELSE 0 END, id DESC LIMIT ?"
    else:
        signal_query += " ORDER BY signal_date DESC, id DESC LIMIT ?"
    run_params = [*parameters, args.limit]
    signal_params = [*parameters, args.limit]

    print("Latest pipeline runs")
    for row in connection.execute(run_query, run_params):
        print(
            f"{row['run_date']} {row['market']} status={row['status']} "
            f"processed={row['processed_count']} success={row['success_count']} failed={row['failed_count']} "
            f"report={row['report_path']}"
        )

    print("")
    print("Latest signals")
    for row in connection.execute(signal_query, signal_params):
        action = row["action"] or "N/A"
        confidence = f"{row['confidence_score']:.2f}" if row["confidence_score"] is not None else "N/A"
        entry = f"{row['entry_price']:.2f}" if row["entry_price"] is not None else "N/A"
        stop = f"{row['stop_loss']:.2f}" if row["stop_loss"] is not None else "N/A"
        target = f"{row['take_profit']:.2f}" if row["take_profit"] is not None else "N/A"
        print(
            f"{row['signal_date']} {row['market']} {row['symbol']} action={action} confidence={confidence} "
            f"entry={entry} stop={stop} target={target} category={row['category']} "
            f"spec={row['speculation_score']:.2f} growth={row['growth_score']:.2f} quality={row['quality_score']:.2f}"
        )

    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
