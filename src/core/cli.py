from __future__ import annotations

import argparse

from src.core.config import load_config
from src.core.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stock agent daily pipeline")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--offline", action="store_true", help="Use built-in sample data")
    parser.add_argument("--no-telegram", action="store_true", help="Disable Telegram sending")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    result = run_pipeline(config, offline=args.offline, send_telegram_enabled=not args.no_telegram)
    top_symbol = result.ranked_rows[0]["symbol"] if result.ranked_rows else "N/A"
    print(f"完成 {config['market']} 分析，報告：{result.report_path}")
    print(f"Top pick: {top_symbol}")
    print(f"Telegram sent: {result.telegram_sent}")
    return 0

