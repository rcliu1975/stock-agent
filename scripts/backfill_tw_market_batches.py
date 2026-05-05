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
from src.core.database import connect, fetch_stocks, initialize
from src.core.env import load_dotenv
from src.core.logging_utils import setup_logging
from src.core.signal_backfill import backfill_signals
from src.core.universe import classify_symbol_category


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill TW market in safe batches for prices, indicators, and optional signals")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD")
    parser.add_argument("--batch-size", type=int, default=25, help="Number of symbols per batch")
    parser.add_argument("--company-limit", type=int, default=50, help="Limit company count; 0 means none, -1 means all available")
    parser.add_argument("--etf-limit", type=int, default=20, help="Limit ETF count; 0 means none, -1 means all available")
    parser.add_argument("--include-signals", action="store_true", help="Also backfill historical signals after prices/indicators")
    parser.add_argument("--dry-run", action="store_true", help="Calculate only, do not write")
    parser.add_argument("--offline", action="store_true", help="Use built-in sample data")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT_DIR)
    config = load_config(args.config)
    log_path = setup_logging(config.get("log_dir", "logs"), f"{config['market']}_market_backfill")
    connection = connect(config["database_path"])
    initialize(connection)

    symbols = _select_symbols(connection, config["market"], args.company_limit, args.etf_limit)
    if not symbols:
        print("No symbols found in stocks table. Run sync_tw_universe.py first.")
        connection.close()
        return 1

    print(f"Backfill log: {log_path}")
    print(f"Selected symbols: {len(symbols)}")
    print(f"Batch size: {args.batch_size}")

    total_price_rows = 0
    total_signal_rows = 0
    failed_batches = 0
    batches = _chunk_list(symbols, args.batch_size)
    total_batches = len(batches)

    for batch_index, batch_symbols in enumerate(batches, start=1):
        print(f"Running batch {batch_index}/{total_batches}: {len(batch_symbols)} symbols")

        def on_progress(event) -> None:
            status = "skipped" if event.skipped else event.status
            detail = f"rows={event.rows_written}"
            if event.error_message:
                detail = f"{detail} error={event.error_message}"
            print(
                f"  batch {batch_index}/{total_batches} "
                f"[{event.completed_chunks}/{event.total_chunks}] {event.symbol} "
                f"{event.chunk_start}..{event.chunk_end} {status} {detail}",
                flush=True,
            )

        price_results = backfill_history(
            connection=connection,
            config=config,
            market=config["market"],
            currency=config["currency"],
            symbols=batch_symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            chunk_size_days=30,
            offline=args.offline,
            resume=True,
            dry_run=args.dry_run,
            progress_callback=on_progress,
        )
        batch_failed = any(item.status == "failed" for item in price_results)
        total_price_rows += sum(item.rows_written for item in price_results)

        if args.include_signals and not batch_failed:
            signal_results = backfill_signals(
                connection=connection,
                config=config,
                market=config["market"],
                symbols=batch_symbols,
                start_date=args.start_date,
                end_date=args.end_date,
                dry_run=args.dry_run,
            )
            if any(item.status == "failed" for item in signal_results):
                batch_failed = True
            total_signal_rows += sum(item.rows_written for item in signal_results)

        if batch_failed:
            failed_batches += 1

    connection.close()
    print(f"Price/indicator rows counted/written: {total_price_rows}")
    if args.include_signals:
        print(f"Signal rows counted/written: {total_signal_rows}")
    print(f"Failed batches: {failed_batches}")
    return 1 if failed_batches else 0


def _select_symbols(connection, market: str, company_limit: int, etf_limit: int) -> list[str]:
    stocks = [dict(row) for row in fetch_stocks(connection, market)]
    companies: list[str] = []
    etfs: list[str] = []
    for row in stocks:
        category = classify_symbol_category(row.get("industry", ""))
        if category == "etf":
            if etf_limit == 0:
                continue
            if etf_limit < 0 or len(etfs) < etf_limit:
                etfs.append(row["symbol"])
        else:
            if company_limit == 0:
                continue
            if company_limit < 0 or len(companies) < company_limit:
                companies.append(row["symbol"])
    return companies + etfs


def _chunk_list(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        return [items]
    return [items[index : index + size] for index in range(0, len(items), size)]


if __name__ == "__main__":
    raise SystemExit(main())
