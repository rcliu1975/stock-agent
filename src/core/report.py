from __future__ import annotations

from html import escape
from pathlib import Path


def render_report(config: dict, run_date: str, ranked_rows: list[dict], failures: list[str] | None = None) -> str:
    failure_lines = failures or []
    lines = [
        f"# {config['market_name']} 每日股票報告",
        "",
        f"- 日期：{run_date}",
        f"- 市場：{config['market']}",
        f"- 追蹤數量：{len(ranked_rows)}",
        f"- 失敗數量：{len(failure_lines)}",
        "",
        "## 排名",
        "",
        "| 排名 | Symbol | 類別 | 投機 | 成長 | 績優 | 社群熱度 | 風險 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for index, row in enumerate(ranked_rows, start=1):
        lines.append(
            f"| {index} | {row['symbol']} | {row['category']} | {row['speculation_score']:.2f} | "
            f"{row['growth_score']:.2f} | {row['quality_score']:.2f} | {row['social_heat_score']:.2f} | {row['risk_score']:.2f} |"
        )
    lines.extend(["", "## 重點觀察", ""])
    for row in ranked_rows:
        lines.append(f"### {row['symbol']} {row['category']}")
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
        "",
        "<b>重點名單</b>",
    ]
    if not ranked_rows:
        lines.append("目前沒有可用標的。")
    for index, row in enumerate(ranked_rows[:5], start=1):
        reason = escape(row["reason"])
        warning = escape(row["warning"])
        lines.append(
            f"{index}. <code>{escape(row['symbol'])}</code> {escape(row['category'])}\n"
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
