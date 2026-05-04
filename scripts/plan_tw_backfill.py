#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.config import load_config
from src.core.database import connect, fetch_stocks, initialize
from src.core.env import load_dotenv
from src.core.universe import classify_symbol_category


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan TW market backfill phases and estimate workload")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--years", type=int, default=1, help="History years to plan")
    parser.add_argument("--batch-size", type=int, default=25, help="Symbols per batch")
    parser.add_argument("--company-limit", type=int, default=50, help="Phase 1 company count")
    parser.add_argument("--etf-limit", type=int, default=20, help="Phase 1 ETF count")
    parser.add_argument("--include-signals", action="store_true", help="Include historical signal backfill command")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT_DIR)
    config = load_config(args.config)
    connection = connect(config["database_path"])
    initialize(connection)

    all_active = [dict(row) for row in fetch_stocks(connection, config["market"])]
    company_symbols = [row["symbol"] for row in all_active if classify_symbol_category(row.get("industry", "")) == "company"]
    etf_symbols = [row["symbol"] for row in all_active if classify_symbol_category(row.get("industry", "")) == "etf"]

    end_date = _latest_trade_date(connection, config["market"]) or date.today().isoformat()
    start_date = (date.fromisoformat(end_date) - timedelta(days=365 * args.years - 1)).isoformat()
    phase1_count = _phase_count(args.company_limit, len(company_symbols)) + _phase_count(args.etf_limit, len(etf_symbols))
    phase1_batches = _estimate_batches(phase1_count, args.batch_size)
    phase2_count = len(all_active)
    phase2_batches = _estimate_batches(phase2_count, args.batch_size)

    print("TW backfill readiness")
    print(f"- active stocks total: {len(all_active)}")
    print(f"- active companies: {len(company_symbols)}")
    print(f"- active etfs: {len(etf_symbols)}")
    print(f"- latest trade_date in DB: {end_date}")
    print(f"- suggested start_date for {args.years} year(s): {start_date}")
    print(f"- batch size: {args.batch_size}")
    print("")
    print("Phase 1")
    print(f"- target universe: {args.company_limit} companies + {args.etf_limit} etfs")
    print(f"- estimated selected symbols: {phase1_count}")
    print(f"- estimated batches: {phase1_batches}")
    print(_phase_command(config["config_path"], start_date, end_date, args.batch_size, args.company_limit, args.etf_limit, args.include_signals))
    print("")
    print("Phase 2")
    print("- target universe: all active stocks")
    print(f"- estimated selected symbols: {phase2_count}")
    print(f"- estimated batches: {phase2_batches}")
    print(_phase_command(config["config_path"], start_date, end_date, args.batch_size, -1, -1, args.include_signals))
    print("")
    print("Pre-check")
    print(f"- daily_prices coverage: {_count_rows(connection, 'daily_prices', config['market'])}")
    print(f"- technical_indicators coverage: {_count_rows(connection, 'technical_indicators', config['market'])}")
    print(f"- signals coverage: {_count_rows(connection, 'signals', config['market'])}")
    print(f"- watchlist snapshots: {_count_rows(connection, 'watchlist_snapshots', config['market'])}")

    connection.close()
    return 0


def _phase_command(
    config_path: str,
    start_date: str,
    end_date: str,
    batch_size: int,
    company_limit: int,
    etf_limit: int,
    include_signals: bool,
) -> str:
    command = (
        f"python3 scripts/backfill_tw_market_batches.py --config {config_path} "
        f"--start-date {start_date} --end-date {end_date} "
        f"--batch-size {batch_size} --company-limit {company_limit} --etf-limit {etf_limit}"
    )
    if include_signals:
        command += " --include-signals"
    return command


def _latest_trade_date(connection: sqlite3.Connection, market: str) -> str | None:
    row = connection.execute(
        "SELECT MAX(trade_date) FROM daily_prices WHERE market = ?",
        (market,),
    ).fetchone()
    return row[0] if row else None


def _count_rows(connection: sqlite3.Connection, table: str, market: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table} WHERE market = ?", (market,)).fetchone()[0])


def _estimate_batches(symbol_count: int, batch_size: int) -> int:
    if symbol_count == 0:
        return 0
    return math.ceil(symbol_count / batch_size)


def _phase_count(limit: int, available: int) -> int:
    if limit < 0:
        return available
    if limit == 0:
        return 0
    return min(limit, available)


if __name__ == "__main__":
    raise SystemExit(main())
