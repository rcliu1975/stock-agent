from __future__ import annotations

from dataclasses import dataclass


DEFAULT_DECISION_RULES = {
    "buy_min_score": 72,
    "watch_min_score": 62,
    "hold_min_score": 55,
    "max_buy_risk": 45,
    "max_watch_risk": 60,
    "min_trend_score": 65,
    "buy_rsi_min": 45,
    "buy_rsi_max": 68,
    "sell_rsi_max": 42,
    "min_volume_ratio": 1.05,
    "stop_loss_pct": 0.08,
    "take_profit_pct": 0.16,
}


@dataclass(slots=True, frozen=True)
class TradeDecision:
    action: str
    confidence_score: float
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    sell_trigger: str
    decision_reason: str


def make_trade_decision(
    latest_price: dict,
    indicator: dict,
    scores: dict,
    rules: dict | None = None,
) -> TradeDecision:
    active_rules = {**DEFAULT_DECISION_RULES, **(rules or {})}
    close = _number(latest_price.get("close"))
    ma5 = _optional_number(indicator.get("ma5"))
    ma20 = _optional_number(indicator.get("ma20"))
    ma60 = _optional_number(indicator.get("ma60"))
    high_20d = _optional_number(indicator.get("high_20d"))
    low_20d = _optional_number(indicator.get("low_20d"))
    rsi14 = _optional_number(indicator.get("rsi14"))
    volume = _optional_number(latest_price.get("volume"))
    volume_ma20 = _optional_number(indicator.get("volume_ma20"))
    volume_ratio = volume / volume_ma20 if volume is not None and volume_ma20 else 1.0

    best_score = max(
        _number(scores.get("speculation_score")),
        _number(scores.get("growth_score")),
        _number(scores.get("quality_score")),
    )
    risk_score = _number(scores.get("risk_score"))
    trend_score = _trend_score(close, ma5, ma20, ma60, high_20d, volume_ratio, rsi14, active_rules)
    confidence = round(max(0.0, min(100.0, best_score * 0.55 + trend_score * 0.35 + (100 - risk_score) * 0.10)), 2)

    action = _classify_action(close, ma5, ma20, ma60, rsi14, best_score, risk_score, trend_score, volume_ratio, active_rules)
    stop_loss, take_profit = _price_targets(close, low_20d, active_rules)
    sell_trigger = _sell_trigger(stop_loss, ma20, ma60)
    decision_reason = _decision_reason(action, best_score, risk_score, trend_score, volume_ratio, rsi14)

    return TradeDecision(
        action=action,
        confidence_score=confidence,
        entry_price=round(close, 2) if action in {"BUY", "WATCH", "HOLD"} else None,
        stop_loss=stop_loss if action in {"BUY", "WATCH", "HOLD"} else None,
        take_profit=take_profit if action in {"BUY", "WATCH", "HOLD"} else None,
        sell_trigger=sell_trigger,
        decision_reason=decision_reason,
    )


def _classify_action(
    close: float,
    ma5: float | None,
    ma20: float | None,
    ma60: float | None,
    rsi14: float | None,
    best_score: float,
    risk_score: float,
    trend_score: float,
    volume_ratio: float,
    rules: dict,
) -> str:
    if _sell_signal(close, ma5, ma20, ma60, rsi14, rules):
        return "SELL"
    if (
        best_score >= rules["buy_min_score"]
        and risk_score <= rules["max_buy_risk"]
        and trend_score >= rules["min_trend_score"]
        and rules["buy_rsi_min"] <= (rsi14 or 50.0) <= rules["buy_rsi_max"]
        and volume_ratio >= rules["min_volume_ratio"]
    ):
        return "BUY"
    if best_score >= rules["watch_min_score"] and risk_score <= rules["max_watch_risk"] and _above(close, ma20):
        return "WATCH"
    if best_score >= rules["hold_min_score"] and _above(close, ma20):
        return "HOLD"
    return "AVOID"


def _sell_signal(
    close: float,
    ma5: float | None,
    ma20: float | None,
    ma60: float | None,
    rsi14: float | None,
    rules: dict,
) -> bool:
    weak_short_trend = ma5 is not None and ma20 is not None and close < ma20 and ma5 < ma20
    broken_medium_trend = ma60 is not None and close < ma60
    weak_momentum = rsi14 is not None and rsi14 <= rules["sell_rsi_max"]
    return (weak_short_trend and weak_momentum) or broken_medium_trend


def _trend_score(
    close: float,
    ma5: float | None,
    ma20: float | None,
    ma60: float | None,
    high_20d: float | None,
    volume_ratio: float,
    rsi14: float | None,
    rules: dict,
) -> float:
    score = 0.0
    if _above(close, ma20):
        score += 25
    if ma5 is not None and ma20 is not None and ma5 >= ma20:
        score += 20
    if ma20 is not None and ma60 is not None and ma20 >= ma60:
        score += 15
    elif _above(close, ma20):
        score += 8
    if high_20d is not None and close >= high_20d * 0.98:
        score += 15
    if volume_ratio >= rules["min_volume_ratio"]:
        score += 10
    if rsi14 is not None and rules["buy_rsi_min"] <= rsi14 <= rules["buy_rsi_max"]:
        score += 15
    return min(score, 100.0)


def _price_targets(close: float, low_20d: float | None, rules: dict) -> tuple[float, float]:
    pct_stop = close * (1 - rules["stop_loss_pct"])
    support_stop = low_20d * 0.98 if low_20d else pct_stop
    stop_loss = min(pct_stop, support_stop)
    take_profit = close * (1 + rules["take_profit_pct"])
    return round(stop_loss, 2), round(take_profit, 2)


def _sell_trigger(stop_loss: float, ma20: float | None, ma60: float | None) -> str:
    triggers = [f"跌破停損 {stop_loss:.2f}"]
    if ma20 is not None:
        triggers.append(f"或收盤跌破 MA20 {ma20:.2f}")
    if ma60 is not None:
        triggers.append(f"中線跌破 MA60 {ma60:.2f}")
    return "；".join(triggers)


def _decision_reason(action: str, best_score: float, risk_score: float, trend_score: float, volume_ratio: float, rsi14: float | None) -> str:
    rsi_text = f"{rsi14:.1f}" if rsi14 is not None else "N/A"
    return (
        f"{action}: best_score={best_score:.1f}, risk={risk_score:.1f}, "
        f"trend={trend_score:.1f}, volume_ratio={volume_ratio:.2f}, RSI={rsi_text}"
    )


def _above(value: float, baseline: float | None) -> bool:
    return baseline is not None and value >= baseline


def _number(value: object) -> float:
    return float(value or 0.0)


def _optional_number(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
