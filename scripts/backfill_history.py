#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.backfill import backfill_history
from src.core.config import load_config
from src.core.database import connect, initialize
from src.core.logging_utils import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill daily_prices and technical_indicators safely")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD")
    parser.add_argument("--symbols", help="Comma-separated symbol override")
    parser.add_argument("--chunk-size-days", type=int, default=90, help="Chunk size in calendar days")
    parser.add_argument("--offline", action="store_true", help="Use built-in sample data")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count without writing prices/indicators")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip completed checkpoints")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.symbols:
        config["universe"]["symbols"] = [item.strip() for item in args.symbols.split(",") if item.strip()]
    log_path = setup_logging(config.get("log_dir", "logs"), f"{config['market']}_backfill")
    connection = connect(config["database_path"])
    initialize(connection)
    results = backfill_history(
        connection=connection,
        market=config["market"],
        currency=config["currency"],
        symbols=config["universe"]["symbols"],
        start_date=args.start_date,
        end_date=args.end_date,
        chunk_size_days=args.chunk_size_days,
        offline=args.offline,
        resume=not args.no_resume,
        dry_run=args.dry_run,
    )
    connection.close()

    success_count = sum(1 for item in results if item.status == "success" and not item.skipped)
    dry_run_count = sum(1 for item in results if item.status == "dry_run")
    skipped_count = sum(1 for item in results if item.skipped)
    failed = [item for item in results if item.status == "failed"]
    total_rows = sum(item.rows_written for item in results if item.status in {"success", "dry_run"})

    print(f"Backfill log: {log_path}")
    print(f"Chunks success: {success_count}")
    print(f"Chunks dry-run: {dry_run_count}")
    print(f"Chunks skipped: {skipped_count}")
    print(f"Chunks failed: {len(failed)}")
    print(f"Rows counted/written: {total_rows}")
    if failed:
        print("Failures:")
        for item in failed[:20]:
            print(f"- {item.symbol} {item.chunk_start}..{item.chunk_end}: {item.error_message}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
