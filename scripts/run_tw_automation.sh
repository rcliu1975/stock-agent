#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOCK_DIR="$ROOT_DIR/.locks"
mkdir -p "$LOCK_DIR"
LOCK_FILE="$LOCK_DIR/tw_automation.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "another TW automation run is still active"
  exit 1
fi

CONFIG_PATH="${CONFIG_PATH:-config/config_tw.yaml}"
MARKET_TZ="${MARKET_TZ:-Asia/Taipei}"
BACKFILL_DAYS="${BACKFILL_DAYS:-45}"
WATCHLIST_LOOKBACK_DAYS="${WATCHLIST_LOOKBACK_DAYS:-20}"
WATCHLIST_COMPANIES="${WATCHLIST_COMPANIES:-50}"
WATCHLIST_ETFS="${WATCHLIST_ETFS:-20}"
WATCHLIST_STRATEGY="${WATCHLIST_STRATEGY:-tw_top_companies_etfs}"
REPORT_TOP_N="${REPORT_TOP_N:-20}"
ENABLE_BACKUP="${ENABLE_BACKUP:-1}"
ENABLE_UNIVERSE_SYNC="${ENABLE_UNIVERSE_SYNC:-1}"
ENABLE_BACKFILL="${ENABLE_BACKFILL:-1}"
ENABLE_WATCHLIST_BUILD="${ENABLE_WATCHLIST_BUILD:-1}"
ENABLE_REPORT="${ENABLE_REPORT:-1}"
NO_TELEGRAM="${NO_TELEGRAM:-0}"
OFFLINE="${OFFLINE:-0}"
SYNC_EXCHANGES="${SYNC_EXCHANGES:-twse,tpex}"
SYNC_EXCLUDE_INDUSTRIES="${SYNC_EXCLUDE_INDUSTRIES:-ETN}"
SYNC_ALL_STOCK_ID_PATTERN="${SYNC_ALL_STOCK_ID_PATTERN:-^\\d+[A-Z]?$}"
SYNC_COMPANY_STOCK_ID_PATTERN="${SYNC_COMPANY_STOCK_ID_PATTERN:-^\\d{4}$}"

TODAY="$(TZ="$MARKET_TZ" date +%F)"
START_DATE="$(TZ="$MARKET_TZ" date -d "$TODAY - $((BACKFILL_DAYS - 1)) days" +%F)"
END_DATE="$TODAY"

echo "TW automation start"
echo "config=$CONFIG_PATH"
echo "window=$START_DATE..$END_DATE"
echo "watchlist=${WATCHLIST_COMPANIES} companies + ${WATCHLIST_ETFS} etfs"

if [[ "$ENABLE_BACKUP" == "1" ]] && [[ -f "$ROOT_DIR/data/stock_agent.sqlite" ]]; then
  bash "$ROOT_DIR/scripts/backup_sqlite.sh"
fi

if [[ "$ENABLE_UNIVERSE_SYNC" == "1" ]]; then
  python3 "$ROOT_DIR/scripts/sync_tw_universe.py" \
    --config "$CONFIG_PATH" \
    --exchanges "$SYNC_EXCHANGES" \
    --exclude-industries "$SYNC_EXCLUDE_INDUSTRIES" \
    --all-stock-id-pattern "$SYNC_ALL_STOCK_ID_PATTERN" \
    --company-stock-id-pattern "$SYNC_COMPANY_STOCK_ID_PATTERN"
fi

if [[ "$ENABLE_BACKFILL" == "1" ]]; then
  BACKFILL_ARGS=(
    --config "$CONFIG_PATH"
    --start-date "$START_DATE"
    --end-date "$END_DATE"
    --chunk-size-days 15
  )
  if [[ "$OFFLINE" == "1" ]]; then
    BACKFILL_ARGS+=(--offline)
  fi
  python3 "$ROOT_DIR/scripts/backfill_history.py" \
    "${BACKFILL_ARGS[@]}"
fi

if [[ "$ENABLE_WATCHLIST_BUILD" == "1" ]]; then
  python3 "$ROOT_DIR/scripts/build_tw_watchlist.py" \
    --config "$CONFIG_PATH" \
    --companies "$WATCHLIST_COMPANIES" \
    --etfs "$WATCHLIST_ETFS" \
    --lookback-days "$WATCHLIST_LOOKBACK_DAYS" \
    --strategy "$WATCHLIST_STRATEGY"
fi

if [[ "$ENABLE_REPORT" == "1" ]]; then
  REPORT_ARGS=(--config "$CONFIG_PATH" --top-n "$REPORT_TOP_N")
  if [[ "$NO_TELEGRAM" == "1" ]]; then
    REPORT_ARGS+=(--no-telegram)
  fi
  if [[ "$OFFLINE" == "1" ]]; then
    REPORT_ARGS+=(--offline)
  fi
  python3 "$ROOT_DIR/main.py" "${REPORT_ARGS[@]}"
fi

echo "TW automation done"
