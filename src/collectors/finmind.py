from __future__ import annotations

from datetime import date

from src.collectors.sample_data import SAMPLE_FUNDAMENTALS


def fetch_fundamental(symbol: str, market: str) -> dict:
    payload = SAMPLE_FUNDAMENTALS.get(symbol)
    if payload is None:
        payload = {
            "eps": 4.0,
            "revenue_yoy": 8.0,
            "roe": 10.0,
            "gross_margin": 20.0,
            "debt_ratio": 45.0,
            "free_cash_flow": 30.0,
            "dividend_yield": 2.0,
        }
    return {
        "symbol": symbol,
        "market": market,
        "period": date.today().replace(day=1).isoformat(),
        **payload,
    }

