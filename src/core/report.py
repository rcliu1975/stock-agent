from __future__ import annotations

from html import escape
from pathlib import Path


ACTION_LABELS = {
    "BUY": "買進",
    "WATCH": "觀察",
    "HOLD": "續抱",
    "SELL": "賣出",
    "AVOID": "避開",
}


def render_report(config: dict, run_date: str, ranked_rows: list[dict], failures: list[str] | None = None) -> str:
    failure_lines = failures or []
    lines = [
        f"# {config['market_name']} 每日股票報告",
        "",
        f"- 日期：{run_date}",
        f"- 市場：{config['market']}",
        f"- 追蹤數量：{len(ranked_rows)}",
        f"- 失敗數量：{len(failure_lines)}",
        "- 說明：動作為規則式訊號，需搭配風險控管與人工判斷。",
        "",
        "## 排名",
        "",
        "| 排名 | Symbol | 動作 | 信心 | 類別 | 投機 | 成長 | 績優 | 風險 | 進場 | 停損 | 停利 |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for index, row in enumerate(ranked_rows, start=1):
        lines.append(
            f"| {index} | {row['symbol']} | {_action_label(row)} | {_format_number(row.get('confidence_score'))} | "
            f"{row['category']} | {row['speculation_score']:.2f} | {row['growth_score']:.2f} | "
            f"{row['quality_score']:.2f} | {row['risk_score']:.2f} | {_format_number(row.get('entry_price'))} | "
            f"{_format_number(row.get('stop_loss'))} | {_format_number(row.get('take_profit'))} |"
        )
    lines.extend(["", "## 重點觀察", ""])
    for row in ranked_rows:
        lines.append(f"### {row['symbol']} {_action_label(row)} {row['category']}")
        lines.append(f"- 決策：{row.get('decision_reason', '尚未產生決策理由')}")
        lines.append(f"- 賣出條件：{row.get('sell_trigger', '尚未產生賣出條件')}")
        lines.append(f"- 原因：{row['reason']}")
        lines.append(f"- 警示：{row['warning']}")
        lines.append(f"- 摘要：{row['ai_summary']}")
        lines.append("")
    if failure_lines:
        lines.extend(["## 失敗項目", ""])
        for item in failure_lines:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_telegram_html(config: dict, run_date: str, ranked_rows: list[dict], failures: list[str] | None = None) -> str:
    failure_lines = failures or []
    market_name = escape(config["market_name"])
    lines = [
        f"<b>{market_name} 每日股票報告</b>",
        f"日期：<code>{escape(run_date)}</code>",
        f"市場：<code>{escape(config['market'])}</code>",
        f"追蹤數量：<code>{len(ranked_rows)}</code>",
        f"失敗數量：<code>{len(failure_lines)}</code>",
        "說明：規則式訊號，需搭配風險控管。",
        "",
        "<b>重點名單</b>",
    ]
    if not ranked_rows:
        lines.append("目前沒有可用標的。")
    for index, row in enumerate(ranked_rows[:5], start=1):
        reason = escape(row["reason"])
        warning = escape(row["warning"])
        action = escape(_action_label(row))
        confidence = escape(_format_number(row.get("confidence_score")))
        stop_loss = escape(_format_number(row.get("stop_loss")))
        lines.append(
            f"{index}. <code>{escape(row['symbol'])}</code> {action} {escape(row['category'])}\n"
            f"信心 {confidence} / 停損 {stop_loss}\n"
            f"投機 {row['speculation_score']:.2f} / 成長 {row['growth_score']:.2f} / 績優 {row['quality_score']:.2f}\n"
            f"原因：{reason}\n"
            f"警示：{warning}"
        )
    if failure_lines:
        lines.extend(["", "<b>失敗項目</b>"])
        for item in failure_lines[:5]:
            lines.append(f"• {escape(item)}")
    return "\n".join(lines).strip()


def write_report(output_dir: str, market: str, run_label: str, content: str) -> Path:
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{run_label}_{market.lower()}_report.md"
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    return path


def _action_label(row: dict) -> str:
    action = row.get("action") or "WATCH"
    return ACTION_LABELS.get(str(action), str(action))


def _format_number(value: object) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}"
