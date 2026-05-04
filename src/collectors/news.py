from __future__ import annotations

from datetime import UTC, datetime

from src.collectors.sample_data import SAMPLE_NEWS


def fetch_news(symbol: str, market: str) -> list[dict]:
    titles = SAMPLE_NEWS.get(symbol, ["題材關注度中性"])
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return [
        {
            "symbol": symbol,
            "market": market,
            "title": title,
            "url": "",
            "source": "builtin",
            "published_at": now,
            "raw_text": title,
        }
        for title in titles
    ]
