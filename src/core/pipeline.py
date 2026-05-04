from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.ai.event_summary import summarize_event
from src.collectors.finmind import fetch_fundamental
from src.collectors.news import fetch_news
from src.collectors.social import fetch_social
from src.collectors.yfinance_collector import fetch_price_history
from src.core import database
from src.core.indicators import latest_indicator_row
from src.core.report import render_report, write_report
from src.core.scoring import score_stock
from src.notify.telegram import send_message


@dataclass(slots=True)
class PipelineResult:
    report_path: Path
    ranked_rows: list[dict]
    telegram_sent: bool


def run_pipeline(config: dict, offline: bool = False, send_telegram_enabled: bool = True) -> PipelineResult:
    run_date = date.today().isoformat()
    connection = database.connect(config["database_path"])
    database.initialize(connection)
    ranked_rows: list[dict] = []

    for symbol in config["universe"]["symbols"]:
        stock = {
            "symbol": symbol,
            "name": symbol,
            "market": config["market"],
            "exchange": config["market"],
            "industry": "",
            "currency": config["currency"],
        }
        database.upsert_stock(connection, stock)
        prices = fetch_price_history(symbol, config["market"], offline=offline)
        database.upsert_price_rows(connection, prices)
        indicator = latest_indicator_row(symbol, config["market"], prices)
        database.upsert_indicator(connection, indicator)

        fundamental = fetch_fundamental(symbol, config["market"])
        database.upsert_fundamental(connection, fundamental)

        news_items = fetch_news(symbol, config["market"])
        database.insert_news(connection, news_items)
        social_items, social_heat = fetch_social(symbol, config["market"])
        database.insert_social(connection, social_items)

        scores = score_stock(
            config["score_weights"],
            latest_price=prices[-1],
            indicator=indicator,
            fundamental=fundamental,
            news_count=len(news_items),
            social_heat=social_heat,
        )
        scores["ai_summary"] = summarize_event(symbol, scores["category"], scores["reason"])
        signal_row = {
            "symbol": symbol,
            "market": config["market"],
            "signal_date": run_date,
            **scores,
        }
        database.upsert_signal(connection, signal_row)
        ranked_rows.append({"symbol": symbol, **scores})

    connection.commit()
    connection.close()

    ranked_rows.sort(
        key=lambda row: max(row["speculation_score"], row["growth_score"], row["quality_score"]),
        reverse=True,
    )
    top_n = config["report"].get("top_n", len(ranked_rows))
    ranked_rows = ranked_rows[:top_n]
    report_content = render_report(config, run_date, ranked_rows)
    report_path = write_report(config["report"]["output_dir"], config["market"], run_date, report_content)
    telegram_sent = False
    if config["report"].get("telegram_enabled", False) and send_telegram_enabled:
        telegram_sent = send_message(report_content[:3500])
    return PipelineResult(report_path=report_path, ranked_rows=ranked_rows, telegram_sent=telegram_sent)

