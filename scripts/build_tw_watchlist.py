#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.config import load_config
from src.core.database import connect, initialize, replace_watchlist_snapshot
from src.core.env import load_dotenv
from src.core.logging_utils import setup_logging
from src.core.universe import classify_symbol_category


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build TW watchlist: top companies + top ETFs by average turnover from DB")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--companies", type=int, default=50, help="Top N companies")
    parser.add_argument("--etfs", type=int, default=20, help="Top N ETFs")
    parser.add_argument("--lookback-days", type=int, default=20, help="Lookback days from latest trade_date in DB")
    parser.add_argument("--strategy", default="tw_top_companies_etfs", help="Watchlist strategy name")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(ROOT_DIR)
    config = load_config(args.config)
    setup_logging(config.get("log_dir", "logs"), "tw_watchlist_build")
    connection = connect(config["database_path"])
    initialize(connection)

    latest_trade_date = connection.execute(
        """
        SELECT MAX(trade_date)
        FROM daily_prices
        WHERE market = ?
        """,
        (config["market"],),
    ).fetchone()[0]
    if not latest_trade_date:
        print("No daily_prices found. Backfill recent market data first.")
        connection.close()
        return 1

    snapshot_date = str(latest_trade_date)
    start_date = (date.fromisoformat(snapshot_date) - timedelta(days=args.lookback_days - 1)).isoformat()
    rows = connection.execute(
        """
        SELECT
            s.symbol,
            s.name,
            s.industry,
            AVG(dp.turnover) AS avg_turnover
        FROM stocks s
        JOIN daily_prices dp
          ON s.symbol = dp.symbol AND s.market = dp.market
        WHERE s.market = ?
          AND dp.trade_date BETWEEN ? AND ?
        GROUP BY s.symbol, s.name, s.industry
        HAVING COUNT(*) > 0
        ORDER BY avg_turnover DESC
        """,
        (config["market"], start_date, snapshot_date),
    ).fetchall()

    companies: list[dict] = []
    etfs: list[dict] = []
    for row in rows:
        category = classify_symbol_category(row["industry"] or "")
        payload = {
            "market": config["market"],
            "strategy": args.strategy,
            "snapshot_date": snapshot_date,
            "symbol": row["symbol"],
            "category": category,
            "metric_name": "avg_turnover",
            "metric_value": float(row["avg_turnover"]),
        }
        if category == "etf" and len(etfs) < args.etfs:
            payload["rank_order"] = len(etfs) + 1
            etfs.append(payload)
        elif category == "company" and len(companies) < args.companies:
            payload["rank_order"] = len(companies) + 1
            companies.append(payload)
        if len(companies) >= args.companies and len(etfs) >= args.etfs:
            break

    selected_rows = companies + etfs
    replace_watchlist_snapshot(
        connection,
        market=config["market"],
        strategy=args.strategy,
        snapshot_date=snapshot_date,
        rows=selected_rows,
    )
    connection.commit()
    connection.close()

    print(f"Snapshot date: {snapshot_date}")
    print(f"Company count: {len(companies)}")
    print(f"ETF count: {len(etfs)}")
    print(f"Lookback start: {start_date}")
    if companies:
        print(f"Top company: {companies[0]['symbol']}")
    if etfs:
        print(f"Top ETF: {etfs[0]['symbol']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
