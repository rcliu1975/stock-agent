from __future__ import annotations

from src.collectors import finmind as finmind_collector
from src.collectors import yfinance_collector


def fetch_price_history(
    config: dict,
    symbol: str,
    market: str,
    offline: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    source = config.get("data_sources", {}).get("price", "yfinance")
    if source == "finmind":
        return finmind_collector.fetch_price_history(
            symbol,
            market,
            offline=offline,
            start_date=start_date,
            end_date=end_date,
        )
    return yfinance_collector.fetch_price_history(
        symbol,
        market,
        offline=offline,
        start_date=start_date,
        end_date=end_date,
    )


def fetch_fundamental(config: dict, symbol: str, market: str) -> dict:
    source = config.get("data_sources", {}).get("fundamentals", "builtin")
    if source == "finmind":
        return finmind_collector.fetch_fundamental(symbol, market)
    return finmind_collector.fetch_builtin_fundamental(symbol, market)


def fetch_stock_profile(config: dict, symbol: str, market: str, currency: str) -> dict:
    source = config.get("data_sources", {}).get("price", "yfinance")
    if source == "finmind":
        profile = finmind_collector.fetch_stock_profile(symbol, market)
        profile["currency"] = currency
        return profile
    return {
        "symbol": symbol,
        "name": symbol,
        "market": market,
        "exchange": market,
        "industry": "",
        "currency": currency,
    }
