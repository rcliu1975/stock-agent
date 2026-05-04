from __future__ import annotations


def summarize_event(symbol: str, category: str, reason: str) -> str:
    return f"{symbol} 目前歸類為{category}，重點依據為 {reason}"

