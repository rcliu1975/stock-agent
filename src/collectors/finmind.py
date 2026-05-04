from __future__ import annotations

from datetime import date, timedelta
import os
from functools import lru_cache
import re
from typing import Any

import requests

from src.collectors.sample_data import SAMPLE_FUNDAMENTALS
from src.collectors.yfinance_collector import fetch_price_history as fetch_yfinance_price_history

API_URL = "https://api.finmindtrade.com/api/v4/data"


def fetch_price_history(
    symbol: str,
    market: str,
    offline: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    if offline or market != "TW":
        return fetch_yfinance_price_history(
            symbol,
            market,
            offline=offline,
            start_date=start_date,
            end_date=end_date,
        )

    stock_id = normalize_tw_symbol(symbol)
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    try:
        payload = _request_dataset(params)
        data = payload.get("data", [])
        if not data:
            raise ValueError("FinMind returned empty TaiwanStockPrice data")
        rows: list[dict] = []
        for item in data:
            close = _safe_float(item.get("close"))
            volume = _safe_int(item.get("Trading_Volume", item.get("trading_volume", 0)))
            turnover = item.get("Trading_money", item.get("trading_money"))
            if turnover is None:
                turnover = close * volume
            rows.append(
                {
                    "symbol": symbol,
                    "market": market,
                    "trade_date": str(item["date"]),
                    "open": _safe_float(item.get("open")),
                    "high": _safe_float(item.get("max")),
                    "low": _safe_float(item.get("min")),
                    "close": close,
                    "volume": volume,
                    "turnover": round(_safe_float(turnover), 2),
                }
            )
        return rows
    except Exception:
        return fetch_yfinance_price_history(
            symbol,
            market,
            offline=False,
            start_date=start_date,
            end_date=end_date,
        )


def fetch_fundamental(symbol: str, market: str) -> dict:
    base_payload = _builtin_fundamental_payload(symbol)

    if market != "TW":
        return {
            "symbol": symbol,
            "market": market,
            "period": date.today().replace(day=1).isoformat(),
            **base_payload,
        }

    stock_id = normalize_tw_symbol(symbol)
    start_date = (date.today() - timedelta(days=370)).isoformat()
    params = {
        "dataset": "TaiwanStockPER",
        "data_id": stock_id,
        "start_date": start_date,
    }
    try:
        payload = _request_dataset(params)
        data = payload.get("data", [])
        if data:
            latest = data[-1]
            base_payload = {
                **base_payload,
                "dividend_yield": _safe_float(latest.get("dividend_yield", base_payload["dividend_yield"])),
            }
    except Exception:
        pass

    return {
        "symbol": symbol,
        "market": market,
        "period": date.today().replace(day=1).isoformat(),
        **base_payload,
    }


def fetch_stock_profile(symbol: str, market: str) -> dict:
    default = {
        "symbol": symbol,
        "name": symbol,
        "market": market,
        "exchange": market,
        "industry": "",
        "currency": "TWD" if market == "TW" else "USD",
    }
    if market != "TW":
        return default
    info = _get_tw_stock_info().get(normalize_tw_symbol(symbol))
    if not info:
        return default
    return {
        "symbol": symbol,
        "name": info.get("stock_name") or symbol,
        "market": market,
        "exchange": info.get("type", market),
        "industry": info.get("industry_category", ""),
        "currency": "TWD",
    }


def fetch_tw_stock_universe(
    include_exchanges: tuple[str, ...] = ("twse", "tpex"),
    exclude_industry_keywords: tuple[str, ...] = ("ETF", "上櫃ETF", "ETN"),
    stock_id_pattern: str = r"^\d{4}$",
) -> list[dict]:
    allowed = {item.lower() for item in include_exchanges}
    excluded_keywords = tuple(keyword.lower() for keyword in exclude_industry_keywords)
    stock_id_regex = re.compile(stock_id_pattern) if stock_id_pattern else None
    rows: list[dict] = []
    for stock_id, info in _get_tw_stock_info().items():
        exchange = str(info.get("type", "")).lower()
        if allowed and exchange not in allowed:
            continue
        if stock_id_regex and not stock_id_regex.match(stock_id):
            continue
        industry = str(info.get("industry_category", ""))
        if excluded_keywords and any(keyword in industry.lower() for keyword in excluded_keywords):
            continue
        rows.append(
            {
                "symbol": f"{stock_id}.TW" if exchange == "twse" else f"{stock_id}.TWO",
                "name": info.get("stock_name") or stock_id,
                "market": "TW",
                "exchange": exchange or "TW",
                "industry": industry,
                "currency": "TWD",
            }
        )
    rows.sort(key=lambda item: item["symbol"])
    return rows


def fetch_tw_all_stock_universe(
    include_exchanges: tuple[str, ...] = ("twse", "tpex"),
    stock_id_pattern: str = r"^\d+[A-Z]?$",
) -> list[dict]:
    allowed = {item.lower() for item in include_exchanges}
    stock_id_regex = re.compile(stock_id_pattern) if stock_id_pattern else None
    rows: list[dict] = []
    for stock_id, info in _get_tw_stock_info().items():
        exchange = str(info.get("type", "")).lower()
        if allowed and exchange not in allowed:
            continue
        if stock_id_regex and not stock_id_regex.match(stock_id):
            continue
        rows.append(
            {
                "symbol": f"{stock_id}.TW" if exchange == "twse" else f"{stock_id}.TWO",
                "name": info.get("stock_name") or stock_id,
                "market": "TW",
                "exchange": exchange or "TW",
                "industry": str(info.get("industry_category", "")),
                "currency": "TWD",
            }
        )
    rows.sort(key=lambda item: item["symbol"])
    return rows


def select_tw_tracking_symbols(
    rows: list[dict],
    company_stock_id_pattern: str = r"^\d{4}$",
    exclude_industry_keywords: tuple[str, ...] = ("ETN",),
) -> list[str]:
    company_regex = re.compile(company_stock_id_pattern) if company_stock_id_pattern else None
    excluded_keywords = tuple(keyword.lower() for keyword in exclude_industry_keywords)
    symbols: list[str] = []
    for row in rows:
        symbol = row["symbol"]
        stock_id = normalize_tw_symbol(symbol)
        industry = str(row.get("industry", ""))
        lowered_industry = industry.lower()
        if excluded_keywords and any(keyword in lowered_industry for keyword in excluded_keywords):
            continue
        if "etf" in lowered_industry:
            symbols.append(symbol)
            continue
        if company_regex and company_regex.match(stock_id):
            symbols.append(symbol)
    return symbols


def normalize_tw_symbol(symbol: str) -> str:
    if symbol.endswith(".TW") or symbol.endswith(".TWO"):
        return symbol.split(".", 1)[0]
    return symbol


@lru_cache(maxsize=1)
def _get_tw_stock_info() -> dict[str, dict[str, Any]]:
    payload = _request_dataset({"dataset": "TaiwanStockInfo"})
    items = payload.get("data", [])
    mapping: dict[str, dict[str, Any]] = {}
    for item in items:
        stock_id = str(item.get("stock_id", "")).strip()
        if stock_id:
            mapping[stock_id] = item
    return mapping


def _request_dataset(params: dict[str, Any]) -> dict[str, Any]:
    headers = {}
    token = os.getenv("FINMIND_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(API_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") not in (200, None):
        raise ValueError(f"FinMind API error: {payload}")
    return payload


def _safe_float(value: Any) -> float:
    return round(float(value), 4)


def _safe_int(value: Any) -> int:
    return int(float(value))


def fetch_builtin_fundamental(symbol: str, market: str) -> dict:
    return {
        "symbol": symbol,
        "market": market,
        "period": date.today().replace(day=1).isoformat(),
        **_builtin_fundamental_payload(symbol),
    }


def _builtin_fundamental_payload(symbol: str) -> dict[str, float]:
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
    return payload
