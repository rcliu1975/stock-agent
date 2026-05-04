from __future__ import annotations

from datetime import UTC, datetime

from src.collectors.sample_data import SAMPLE_SOCIAL


def fetch_social(symbol: str, market: str) -> tuple[list[dict], float]:
    heat = SAMPLE_SOCIAL.get(symbol, 40.0)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    item = {
        "symbol": symbol,
        "market": market,
        "platform": "builtin",
        "title": f"{symbol} 社群討論樣本",
        "content": f"社群熱度指數 {heat}",
        "url": "",
        "author": "system",
        "published_at": now,
        "likes": int(heat * 3),
        "comments": int(heat * 1.2),
    }
    return [item], heat
