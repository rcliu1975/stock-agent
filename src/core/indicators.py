from __future__ import annotations

from statistics import fmean


def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return round(fmean(values[-window:]), 4)


def relative_strength_index(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for current, previous in zip(values[1:], values[:-1]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
    avg_gain = fmean(gains[-period:])
    avg_loss = fmean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 4)


def latest_indicator_row(symbol: str, market: str, prices: list[dict]) -> dict:
    closes = [row["close"] for row in prices]
    volumes = [row["volume"] for row in prices]
    trade_date = prices[-1]["trade_date"]
    return {
        "symbol": symbol,
        "market": market,
        "trade_date": trade_date,
        "ma5": moving_average(closes, 5),
        "ma20": moving_average(closes, 20),
        "ma60": moving_average(closes, 60),
        "ma120": moving_average(closes, 120),
        "rsi14": relative_strength_index(closes, 14),
        "volume_ma5": moving_average([float(volume) for volume in volumes], 5),
        "volume_ma20": moving_average([float(volume) for volume in volumes], 20),
        "high_20d": round(max(closes[-20:]), 4) if len(closes) >= 20 else round(max(closes), 4),
        "low_20d": round(min(closes[-20:]), 4) if len(closes) >= 20 else round(min(closes), 4),
        "high_52w": round(max(closes[-252:]), 4) if len(closes) >= 252 else round(max(closes), 4),
        "low_52w": round(min(closes[-252:]), 4) if len(closes) >= 252 else round(min(closes), 4),
    }

