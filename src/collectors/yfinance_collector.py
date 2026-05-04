from __future__ import annotations

from typing import Any

from src.collectors.sample_data import build_price_rows


def fetch_price_history(symbol: str, market: str, offline: bool = False) -> list[dict]:
    if offline:
        return _fallback(symbol, market)
    try:
        import yfinance as yf
    except ImportError:
        return _fallback(symbol, market)

    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="6mo", interval="1d", auto_adjust=False)
    except Exception:
        return _fallback(symbol, market)

    if history.empty:
        return _fallback(symbol, market)

    rows: list[dict] = []
    for trade_date, row in history.iterrows():
        open_price = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])
        close = float(row["Close"])
        volume = int(row["Volume"])
        rows.append(
            {
                "symbol": symbol,
                "market": market,
                "trade_date": trade_date.date().isoformat(),
                "open": round(open_price, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": volume,
                "turnover": round(close * volume, 2),
            }
        )
    return rows or _fallback(symbol, market)


def _fallback(symbol: str, market: str) -> list[dict]:
    seed = sum(ord(char) for char in symbol)
    start_price = 45 + seed % 120
    slope = 0.25 + (seed % 7) * 0.03
    base_volume = 120000 + (seed % 10) * 18000
    return build_price_rows(symbol, market, start_price=float(start_price), slope=slope, base_volume=base_volume)

