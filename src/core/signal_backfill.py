from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging

from src.core import database
from src.core.scoring import score_stock
from src.core.universe import resolve_symbols


@dataclass(slots=True)
class SignalBackfillResult:
    symbol: str
    rows_written: int
    skipped: bool
    status: str
    error_message: str | None = None


def backfill_signals(
    connection,
    config: dict,
    market: str,
    symbols: list[str],
    start_date: str,
    end_date: str,
    dry_run: bool = False,
) -> list[SignalBackfillResult]:
    results: list[SignalBackfillResult] = []
    if not symbols:
        symbols = resolve_symbols(config, connection)

    for symbol in symbols:
        try:
            prices = [dict(row) for row in database.fetch_price_rows(connection, market, symbol, start_date, end_date)]
            indicators = {
                row["trade_date"]: dict(row)
                for row in database.fetch_indicator_rows(connection, market, symbol, start_date, end_date)
            }
            fundamentals = [dict(row) for row in database.fetch_fundamentals_for_symbol(connection, market, symbol)]
            if not prices or not indicators:
                results.append(SignalBackfillResult(symbol=symbol, rows_written=0, skipped=True, status="skipped"))
                continue

            rows_written = 0
            for price in prices:
                trade_date = price["trade_date"]
                indicator = indicators.get(trade_date)
                if not indicator:
                    continue
                fundamental = _fundamental_as_of(fundamentals, trade_date)
                if not fundamental:
                    continue
                scores = score_stock(
                    config["score_weights"],
                    latest_price=price,
                    indicator=indicator,
                    fundamental=fundamental,
                    news_count=0,
                    social_heat=0.0,
                )
                scores["reason"] = f"歷史回填；{scores['reason']}"
                scores["warning"] = f"backtest_only; {scores['warning']}"
                scores["ai_summary"] = "歷史回填版本，未納入新聞與社群資料。"
                signal_row = {
                    "symbol": symbol,
                    "market": market,
                    "signal_date": trade_date,
                    **scores,
                }
                if not dry_run:
                    database.upsert_signal(connection, signal_row)
                rows_written += 1
            if not dry_run:
                connection.commit()
            results.append(SignalBackfillResult(symbol=symbol, rows_written=rows_written, skipped=False, status="success"))
            logging.info("signal backfill success symbol=%s rows=%s dry_run=%s", symbol, rows_written, dry_run)
        except Exception as exc:
            connection.rollback()
            logging.exception("signal backfill failed symbol=%s", symbol)
            results.append(SignalBackfillResult(symbol=symbol, rows_written=0, skipped=False, status="failed", error_message=str(exc)))
    return results


def _fundamental_as_of(fundamentals: list[dict], trade_date: str) -> dict | None:
    target = date.fromisoformat(trade_date)
    current: dict | None = None
    for row in fundamentals:
        period = date.fromisoformat(row["period"])
        if period <= target:
            current = row
        else:
            break
    return current
