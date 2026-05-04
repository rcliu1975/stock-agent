#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.collectors.finmind import fetch_tw_all_stock_universe, select_tw_tracking_symbols
from src.core.config import load_config
from src.core.database import activate_market_symbols, connect, deactivate_market_stocks, initialize, upsert_stock
from src.core.env import load_dotenv
from src.core.logging_utils import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Taiwan stock universe into SQLite from FinMind TaiwanStockInfo")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--exchanges", default="twse,tpex", help="Comma-separated exchanges, e.g. twse,tpex")
    parser.add_argument("--all-stock-id-pattern", default="^\\d+[A-Z]?$", help="Regex for tradable stock_id values to import into metadata")
    parser.add_argument("--exclude-industries", default="ETN", help="Comma-separated industry keywords to exclude from active tracking universe")
    parser.add_argument("--company-stock-id-pattern", default="^\\d{4}$", help="Regex for company stock_id values to include in active tracking universe")
    parser.add_argument("--keep-others-active", action="store_true", help="Do not deactivate old active stocks not selected in this sync")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of rows to import")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT_DIR)
    config = load_config(args.config)
    setup_logging(config.get("log_dir", "logs"), "tw_universe_sync")
    connection = connect(config["database_path"])
    initialize(connection)

    exchanges = tuple(item.strip().lower() for item in args.exchanges.split(",") if item.strip())
    exclude_industries = tuple(item.strip() for item in args.exclude_industries.split(",") if item.strip())
    rows = fetch_tw_all_stock_universe(
        include_exchanges=exchanges,
        stock_id_pattern=args.all_stock_id_pattern,
    )
    if args.limit is not None and args.limit > 0 and not args.keep_others_active:
        print("Refusing to rebuild active universe with --limit. Use --keep-others-active for sampling, or remove --limit.")
        connection.close()
        return 1
    if args.limit is not None and args.limit > 0:
        rows = rows[: args.limit]
    active_symbols = select_tw_tracking_symbols(
        rows,
        company_stock_id_pattern=args.company_stock_id_pattern,
        exclude_industry_keywords=exclude_industries,
    )

    if not args.keep_others_active:
        deactivate_market_stocks(connection, config["market"])

    for row in rows:
        row["is_active"] = 0
        upsert_stock(connection, row)
    activate_market_symbols(connection, config["market"], active_symbols)
    connection.commit()
    connection.close()

    print(f"Imported rows: {len(rows)}")
    print(f"Active tracking symbols: {len(active_symbols)}")
    print(f"Exchanges: {','.join(exchanges)}")
    print(f"All stock ID pattern: {args.all_stock_id_pattern}")
    print(f"Excluded industries: {','.join(exclude_industries)}")
    print(f"Company stock ID pattern: {args.company_stock_id_pattern}")
    print(f"Deactivate others: {'no' if args.keep_others_active else 'yes'}")
    if rows:
        print(f"First symbol: {rows[0]['symbol']}")
        print(f"Last symbol: {rows[-1]['symbol']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
