#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.config import load_config
from src.core.database import connect, initialize
from src.core.env import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check TW database readiness before large backfill")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--min-active-companies", type=int, default=50, help="Minimum active company count")
    parser.add_argument("--min-active-etfs", type=int, default=20, help="Minimum active ETF count")
    parser.add_argument("--min-watchlist-size", type=int, default=70, help="Minimum latest watchlist size")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT_DIR)
    config = load_config(args.config)
    connection = connect(config["database_path"])
    initialize(connection)

    checks = []
    active_companies = _count(
        connection,
        "SELECT COUNT(*) FROM stocks WHERE market = ? AND is_active = 1 AND lower(industry) NOT LIKE '%etf%'",
        (config["market"],),
    )
    active_etfs = _count(
        connection,
        "SELECT COUNT(*) FROM stocks WHERE market = ? AND is_active = 1 AND lower(industry) LIKE '%etf%'",
        (config["market"],),
    )
    all_stocks = _count(connection, "SELECT COUNT(*) FROM stocks WHERE market = ?", (config["market"],))
    daily_prices = _count(connection, "SELECT COUNT(*) FROM daily_prices WHERE market = ?", (config["market"],))
    indicators = _count(connection, "SELECT COUNT(*) FROM technical_indicators WHERE market = ?", (config["market"],))
    signals = _count(connection, "SELECT COUNT(*) FROM signals WHERE market = ?", (config["market"],))
    checkpoints = _count(connection, "SELECT COUNT(*) FROM backfill_checkpoints WHERE market = ?", (config["market"],))
    latest_trade_date = _scalar(connection, "SELECT MAX(trade_date) FROM daily_prices WHERE market = ?", (config["market"],))
    latest_snapshot_date = _scalar(
        connection,
        "SELECT MAX(snapshot_date) FROM watchlist_snapshots WHERE market = ? AND strategy = ?",
        (config["market"], config["universe"].get("db_strategy", "tw_top_companies_etfs")),
    )
    latest_watchlist_size = 0
    if latest_snapshot_date:
        latest_watchlist_size = _count(
            connection,
            "SELECT COUNT(*) FROM watchlist_snapshots WHERE market = ? AND strategy = ? AND snapshot_date = ?",
            (config["market"], config["universe"].get("db_strategy", "tw_top_companies_etfs"), latest_snapshot_date),
        )

    checks.append(("active companies", active_companies, args.min_active_companies, active_companies >= args.min_active_companies))
    checks.append(("active etfs", active_etfs, args.min_active_etfs, active_etfs >= args.min_active_etfs))
    checks.append(("latest watchlist size", latest_watchlist_size, args.min_watchlist_size, latest_watchlist_size >= args.min_watchlist_size))

    print("TW readiness summary")
    print(f"- market: {config['market']}")
    print(f"- all stocks: {all_stocks}")
    print(f"- active companies: {active_companies}")
    print(f"- active etfs: {active_etfs}")
    print(f"- daily_prices: {daily_prices}")
    print(f"- technical_indicators: {indicators}")
    print(f"- signals: {signals}")
    print(f"- backfill_checkpoints: {checkpoints}")
    print(f"- latest trade_date: {latest_trade_date}")
    print(f"- latest watchlist snapshot: {latest_snapshot_date}")
    print(f"- latest watchlist size: {latest_watchlist_size}")
    print("")
    print("Threshold checks")
    failed = 0
    for label, actual, expected, ok in checks:
        status = "OK" if ok else "WARN"
        print(f"- [{status}] {label}: actual={actual} expected>={expected}")
        if not ok:
            failed += 1

    print("")
    print("Suggested next step")
    if failed == 0:
        print("- Ready for Phase 1 market backfill.")
    else:
        print("- Not ready for full Phase 1 yet. Run sync_tw_universe.py, build_tw_watchlist.py, or recent backfill first.")

    connection.close()
    return 1 if failed else 0


def _count(connection: sqlite3.Connection, query: str, params: tuple[object, ...]) -> int:
    return int(connection.execute(query, params).fetchone()[0] or 0)


def _scalar(connection: sqlite3.Connection, query: str, params: tuple[object, ...]) -> str | None:
    row = connection.execute(query, params).fetchone()
    if row is None:
        return None
    return row[0]


if __name__ == "__main__":
    raise SystemExit(main())
