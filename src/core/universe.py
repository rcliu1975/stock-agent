from __future__ import annotations

import sqlite3

from src.core import database


def resolve_symbols(config: dict, connection: sqlite3.Connection | None = None) -> list[str]:
    universe = config.get("universe", {})
    source = universe.get("source", "manual")
    manual_symbols = list(universe.get("symbols", []))
    if source != "db_top_liquidity" or connection is None:
        return manual_symbols

    strategy = universe.get("db_strategy", "tw_top_companies_etfs")
    symbols = database.fetch_latest_watchlist_symbols(connection, config["market"], strategy)
    return symbols or manual_symbols


def classify_symbol_category(industry: str) -> str:
    lowered = (industry or "").lower()
    if "etf" in lowered:
        return "etf"
    return "company"
