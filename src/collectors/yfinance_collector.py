from __future__ import annotations

from datetime import date, datetime, timedelta

from src.collectors.sample_data import build_price_rows


def fetch_price_history(
    symbol: str,
    market: str,
    offline: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    if offline:
        return _filter_rows(_fallback(symbol, market), start_date=start_date, end_date=end_date)
    try:
        import yfinance as yf
    except ImportError:
        return _filter_rows(_fallback(symbol, market), start_date=start_date, end_date=end_date)

    try:
        ticker = yf.Ticker(symbol)
        history_kwargs = {"interval": "1d", "auto_adjust": False}
        if start_date or end_date:
            if start_date:
                history_kwargs["start"] = start_date
            if end_date:
                end_dt = date.fromisoformat(end_date) + timedelta(days=1)
                history_kwargs["end"] = end_dt.isoformat()
        else:
            history_kwargs["period"] = "6mo"
        history = ticker.history(**history_kwargs)
    except Exception:
        return _filter_rows(_fallback(symbol, market), start_date=start_date, end_date=end_date)

    if history.empty:
        return _filter_rows(_fallback(symbol, market), start_date=start_date, end_date=end_date)

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
    return rows or _filter_rows(_fallback(symbol, market), start_date=start_date, end_date=end_date)


def _fallback(symbol: str, market: str) -> list[dict]:
    seed = sum(ord(char) for char in symbol)
    start_price = 45 + seed % 120
    slope = 0.25 + (seed % 7) * 0.03
    base_volume = 120000 + (seed % 10) * 18000
    return build_price_rows(symbol, market, start_price=float(start_price), slope=slope, base_volume=base_volume)


def _filter_rows(rows: list[dict], start_date: str | None, end_date: str | None) -> list[dict]:
    if not start_date and not end_date:
        return rows
    start_bound = date.fromisoformat(start_date) if start_date else None
    end_bound = date.fromisoformat(end_date) if end_date else None
    filtered: list[dict] = []
    for row in rows:
        trade_date = date.fromisoformat(row["trade_date"])
        if start_bound and trade_date < start_bound:
            continue
        if end_bound and trade_date > end_bound:
            continue
        filtered.append(row)
    return filtered

