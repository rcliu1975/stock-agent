from __future__ import annotations


def _bounded_score(ratio: float, weight: float) -> float:
    return round(max(0.0, min(weight, ratio * weight)), 4)


def score_stock(weights: dict, latest_price: dict, indicator: dict, fundamental: dict, news_count: int, social_heat: float) -> dict:
    breakout_ratio = 1.0 if latest_price["close"] >= indicator["high_20d"] else latest_price["close"] / indicator["high_20d"]
    volume_ratio = 1.0
    if indicator["volume_ma20"]:
        volume_ratio = latest_price["volume"] / indicator["volume_ma20"]
    price_alignment_ratio = 1.0 if indicator["ma5"] and indicator["ma20"] and latest_price["close"] >= indicator["ma5"] >= indicator["ma20"] else 0.0

    speculation = (
        _bounded_score(breakout_ratio, weights["speculation"]["price_breakout"])
        + _bounded_score(min(volume_ratio / 2, 1.0), weights["speculation"]["volume_breakout"])
        + weights["speculation"]["price_alignment"] * price_alignment_ratio
        + _bounded_score(social_heat / 100, weights["speculation"]["social_heat"])
        + _bounded_score(min(news_count / 5, 1.0), weights["speculation"]["news_heat"])
    )

    revenue_yoy_ratio = min(max(fundamental["revenue_yoy"], 0.0) / 30, 1.0)
    eps_growth_ratio = min(max(fundamental["eps"], 0.0) / 10, 1.0)
    gross_margin_ratio = min(max(fundamental["gross_margin"], 0.0) / 60, 1.0)
    roe_ratio = min(max(fundamental["roe"], 0.0) / 20, 1.0)
    price_trend_ratio = 1.0 if indicator["ma20"] and latest_price["close"] >= indicator["ma20"] else 0.0

    growth = (
        _bounded_score(revenue_yoy_ratio, weights["growth"]["revenue_yoy"])
        + _bounded_score(eps_growth_ratio, weights["growth"]["eps_growth"])
        + _bounded_score(gross_margin_ratio, weights["growth"]["gross_margin"])
        + _bounded_score(roe_ratio, weights["growth"]["roe"])
        + weights["growth"]["price_trend"] * price_trend_ratio
    )

    roe_stability_ratio = min(max(fundamental["roe"], 0.0) / 20, 1.0)
    dividend_ratio = min(max(fundamental["dividend_yield"], 0.0) / 8, 1.0)
    fcf_ratio = min(max(fundamental["free_cash_flow"], 0.0) / 100, 1.0)
    debt_ratio = 1.0 - min(max(fundamental["debt_ratio"], 0.0) / 100, 1.0)
    drawdown_ratio = min((latest_price["close"] - indicator["low_52w"]) / max(indicator["high_52w"] - indicator["low_52w"], 1e-6), 1.0)

    quality = (
        _bounded_score(roe_stability_ratio, weights["quality"]["roe_stability"])
        + _bounded_score(dividend_ratio, weights["quality"]["dividend_stability"])
        + _bounded_score(fcf_ratio, weights["quality"]["free_cash_flow"])
        + _bounded_score(debt_ratio, weights["quality"]["debt_ratio"])
        + _bounded_score(drawdown_ratio, weights["quality"]["drawdown_control"])
    )

    scores = {
        "speculation_score": round(speculation, 2),
        "growth_score": round(growth, 2),
        "quality_score": round(quality, 2),
        "social_heat_score": round(social_heat, 2),
        "sentiment_score": round(min(100.0, 40 + news_count * 10 + social_heat * 0.2), 2),
        "risk_score": round(max(0.0, 100 - quality), 2),
    }
    category = max(
        ("投機股", scores["speculation_score"]),
        ("成長股", scores["growth_score"]),
        ("績優股", scores["quality_score"]),
        key=lambda item: item[1],
    )[0]
    scores["category"] = category
    scores["reason"] = f"{category}分數最高；收盤 {latest_price['close']:.2f}，RSI {indicator['rsi14'] or 0:.1f}。"
    scores["warning"] = "RSI 偏高" if (indicator["rsi14"] or 0) >= 70 else "注意量價是否延續"
    scores["ai_summary"] = "MVP 版本未接入外部 LLM，先以規則摘要取代。"
    return scores

