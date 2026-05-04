from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import logging

from src.collectors.provider import fetch_price_history
from src.core import database
from src.core.indicators import generate_indicator_rows
from src.core.universe import resolve_symbols


@dataclass(slots=True)
class ChunkResult:
    symbol: str
    chunk_start: str
    chunk_end: str
    rows_written: int
    skipped: bool
    status: str
    error_message: str | None = None


def chunk_date_ranges(start_date: str, end_date: str, chunk_size_days: int) -> list[tuple[str, str]]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    ranges: list[tuple[str, str]] = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_size_days - 1), end)
        ranges.append((current.isoformat(), chunk_end.isoformat()))
        current = chunk_end + timedelta(days=1)
    return ranges


def validate_price_rows(rows: list[dict]) -> None:
    seen_dates: set[str] = set()
    for row in rows:
        trade_date = row["trade_date"]
        if trade_date in seen_dates:
            raise ValueError(f"duplicate trade_date {trade_date}")
        seen_dates.add(trade_date)
        if row["volume"] < 0:
            raise ValueError(f"negative volume on {trade_date}")
        high = row["high"]
        low = row["low"]
        open_price = row["open"]
        close = row["close"]
        if high < max(open_price, close):
            raise ValueError(f"invalid high on {trade_date}")
        if low > min(open_price, close):
            raise ValueError(f"invalid low on {trade_date}")


def backfill_history(
    connection,
    config: dict,
    market: str,
    currency: str,
    symbols: list[str],
    start_date: str,
    end_date: str,
    chunk_size_days: int = 90,
    offline: bool = False,
    resume: bool = True,
    dry_run: bool = False,
) -> list[ChunkResult]:
    results: list[ChunkResult] = []
    if not symbols:
        symbols = resolve_symbols(config, connection)
    for symbol in symbols:
        stock = {
            "symbol": symbol,
            "name": symbol,
            "market": market,
            "exchange": market,
            "industry": "",
            "currency": currency,
        }
        database.upsert_stock(connection, stock)
        for chunk_start, chunk_end in chunk_date_ranges(start_date, end_date, chunk_size_days):
            checkpoint = database.fetch_backfill_checkpoint(connection, market, symbol, chunk_start, chunk_end)
            if resume and checkpoint and checkpoint["status"] == "success":
                results.append(
                    ChunkResult(
                        symbol=symbol,
                        chunk_start=chunk_start,
                        chunk_end=chunk_end,
                        rows_written=int(checkpoint["rows_written"]),
                        skipped=True,
                        status="success",
                    )
                )
                continue

            database.upsert_backfill_checkpoint(
                connection,
                {
                    "market": market,
                    "symbol": symbol,
                    "chunk_start": chunk_start,
                    "chunk_end": chunk_end,
                    "status": "running",
                    "rows_written": 0,
                    "last_trade_date": None,
                    "error_message": None,
                },
            )
            connection.commit()

            try:
                prices = fetch_price_history(
                    config,
                    symbol,
                    market,
                    offline=offline,
                    start_date=chunk_start,
                    end_date=chunk_end,
                )
                validate_price_rows(prices)
                if dry_run:
                    rows_written = len(prices)
                    checkpoint_status = "dry_run"
                else:
                    database.upsert_price_rows(connection, prices)
                    history_start = date.fromisoformat(chunk_start) - timedelta(days=251)
                    full_prices = fetch_price_history(
                        config,
                        symbol,
                        market,
                        offline=offline,
                        start_date=history_start.isoformat(),
                        end_date=chunk_end,
                    )
                    validate_price_rows(full_prices)
                    indicator_rows = [
                        row
                        for row in generate_indicator_rows(symbol, market, full_prices)
                        if chunk_start <= row["trade_date"] <= chunk_end
                    ]
                    for indicator_row in indicator_rows:
                        database.upsert_indicator(connection, indicator_row)
                    rows_written = len(prices)
                    checkpoint_status = "success"
                last_trade_date = prices[-1]["trade_date"] if prices else None
                database.upsert_backfill_checkpoint(
                    connection,
                    {
                        "market": market,
                        "symbol": symbol,
                        "chunk_start": chunk_start,
                        "chunk_end": chunk_end,
                        "status": checkpoint_status,
                        "rows_written": rows_written,
                        "last_trade_date": last_trade_date,
                        "error_message": None,
                    },
                )
                connection.commit()
                results.append(
                    ChunkResult(
                        symbol=symbol,
                        chunk_start=chunk_start,
                        chunk_end=chunk_end,
                        rows_written=rows_written,
                        skipped=False,
                        status=checkpoint_status,
                    )
                )
                logging.info(
                    "backfill success symbol=%s chunk=%s..%s rows=%s dry_run=%s",
                    symbol,
                    chunk_start,
                    chunk_end,
                    rows_written,
                    dry_run,
                )
            except Exception as exc:
                connection.rollback()
                database.upsert_backfill_checkpoint(
                    connection,
                    {
                        "market": market,
                        "symbol": symbol,
                        "chunk_start": chunk_start,
                        "chunk_end": chunk_end,
                        "status": "failed",
                        "rows_written": 0,
                        "last_trade_date": None,
                        "error_message": str(exc),
                    },
                )
                connection.commit()
                logging.exception("backfill failed symbol=%s chunk=%s..%s", symbol, chunk_start, chunk_end)
                results.append(
                    ChunkResult(
                        symbol=symbol,
                        chunk_start=chunk_start,
                        chunk_end=chunk_end,
                        rows_written=0,
                        skipped=False,
                        status="failed",
                        error_message=str(exc),
                    )
                )
    return results
