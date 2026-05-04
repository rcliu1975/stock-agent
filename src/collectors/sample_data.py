from __future__ import annotations

from datetime import date, timedelta


def build_price_rows(symbol: str, market: str, start_price: float, slope: float, base_volume: int) -> list[dict]:
    rows: list[dict] = []
    start_day = date.today() - timedelta(days=90)
    for index in range(65):
        trade_day = start_day + timedelta(days=index)
        close = round(start_price + slope * index + ((index % 5) - 2) * 0.35, 2)
        open_price = round(close * 0.992, 2)
        high = round(close * 1.014, 2)
        low = round(close * 0.988, 2)
        volume = base_volume + (index % 7) * 12000 + index * 350
        rows.append(
            {
                "symbol": symbol,
                "market": market,
                "trade_date": trade_day.isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "turnover": round(close * volume, 2),
            }
        )
    return rows


SAMPLE_FUNDAMENTALS = {
    "2330.TW": {"eps": 8.4, "revenue_yoy": 24.0, "roe": 28.5, "gross_margin": 53.2, "debt_ratio": 22.0, "free_cash_flow": 88.0, "dividend_yield": 1.7},
    "2317.TW": {"eps": 5.6, "revenue_yoy": 12.5, "roe": 14.8, "gross_margin": 11.2, "debt_ratio": 41.5, "free_cash_flow": 61.0, "dividend_yield": 3.4},
    "2454.TW": {"eps": 6.9, "revenue_yoy": 19.7, "roe": 18.3, "gross_margin": 46.0, "debt_ratio": 17.5, "free_cash_flow": 72.0, "dividend_yield": 2.0},
    "2382.TW": {"eps": 4.8, "revenue_yoy": 9.3, "roe": 12.0, "gross_margin": 7.5, "debt_ratio": 48.0, "free_cash_flow": 39.0, "dividend_yield": 4.5},
    "NVDA": {"eps": 9.1, "revenue_yoy": 38.0, "roe": 31.0, "gross_margin": 70.5, "debt_ratio": 21.0, "free_cash_flow": 95.0, "dividend_yield": 0.1},
    "MSFT": {"eps": 8.3, "revenue_yoy": 16.0, "roe": 29.4, "gross_margin": 68.2, "debt_ratio": 29.0, "free_cash_flow": 91.0, "dividend_yield": 0.8},
    "AAPL": {"eps": 7.4, "revenue_yoy": 11.0, "roe": 24.0, "gross_margin": 45.2, "debt_ratio": 35.0, "free_cash_flow": 89.0, "dividend_yield": 0.6},
    "AMZN": {"eps": 6.1, "revenue_yoy": 14.5, "roe": 17.5, "gross_margin": 48.0, "debt_ratio": 32.0, "free_cash_flow": 73.0, "dividend_yield": 0.0},
}


SAMPLE_NEWS = {
    "2330.TW": ["先進製程產能擴張", "AI 晶片需求帶動營運"],
    "2317.TW": ["伺服器出貨成長", "電動車布局持續"],
    "2454.TW": ["高階手機晶片新品發布"],
    "2382.TW": ["NB 與 AI PC 題材升溫"],
    "NVDA": ["AI 基礎設施需求續強", "資料中心訂單動能延續"],
    "MSFT": ["雲端與 Copilot 業務擴張"],
    "AAPL": ["服務營收與新品周期受關注"],
    "AMZN": ["AWS 成長穩定，零售效率改善"],
}


SAMPLE_SOCIAL = {
    "2330.TW": 72.0,
    "2317.TW": 55.0,
    "2454.TW": 64.0,
    "2382.TW": 48.0,
    "NVDA": 88.0,
    "MSFT": 74.0,
    "AAPL": 66.0,
    "AMZN": 61.0,
}

