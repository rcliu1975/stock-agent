#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.config import load_config
from src.core.database import connect, initialize
from src.core.env import load_dotenv
from src.core.logging_utils import setup_logging
from src.core.signal_backfill import backfill_signals


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill historical signals from existing prices, indicators, and fundamentals")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD")
    parser.add_argument("--symbols", help="Comma-separated symbol override")
    parser.add_argument("--dry-run", action="store_true", help="Calculate only, do not write signals")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT_DIR)
    config = load_config(args.config)
    if args.symbols:
        config["universe"]["symbols"] = [item.strip() for item in args.symbols.split(",") if item.strip()]
    log_path = setup_logging(config.get("log_dir", "logs"), f"{config['market']}_signal_backfill")
    connection = connect(config["database_path"])
    initialize(connection)
    results = backfill_signals(
        connection=connection,
        config=config,
        market=config["market"],
        symbols=config["universe"].get("symbols", []),
        start_date=args.start_date,
        end_date=args.end_date,
        dry_run=args.dry_run,
    )
    connection.close()

    success = sum(1 for item in results if item.status == "success")
    skipped = sum(1 for item in results if item.status == "skipped")
    failed = [item for item in results if item.status == "failed"]
    total_rows = sum(item.rows_written for item in results)
    print(f"Signal backfill log: {log_path}")
    print(f"Symbols success: {success}")
    print(f"Symbols skipped: {skipped}")
    print(f"Symbols failed: {len(failed)}")
    print(f"Signal rows counted/written: {total_rows}")
    if failed:
        print("Failures:")
        for item in failed[:20]:
            print(f"- {item.symbol}: {item.error_message}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
