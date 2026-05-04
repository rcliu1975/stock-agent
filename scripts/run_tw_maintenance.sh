#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOCK_DIR="$ROOT_DIR/.locks"
mkdir -p "$LOCK_DIR"
LOCK_FILE="$LOCK_DIR/tw_maintenance.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "another TW maintenance run is still active"
  exit 1
fi

CONFIG_PATH="${CONFIG_PATH:-config/config_tw.yaml}"
export CONFIG_PATH
MARKET_TZ="${MARKET_TZ:-Asia/Taipei}"
RECENT_DAYS="${RECENT_DAYS:-7}"
WATCHLIST_LOOKBACK_DAYS="${WATCHLIST_LOOKBACK_DAYS:-20}"
WATCHLIST_COMPANIES="${WATCHLIST_COMPANIES:-50}"
WATCHLIST_ETFS="${WATCHLIST_ETFS:-20}"
WATCHLIST_STRATEGY="${WATCHLIST_STRATEGY:-tw_top_companies_etfs}"
ENABLE_UNIVERSE_SYNC="${ENABLE_UNIVERSE_SYNC:-1}"
ENABLE_BACKFILL="${ENABLE_BACKFILL:-1}"
ENABLE_WATCHLIST_BUILD="${ENABLE_WATCHLIST_BUILD:-1}"
ENABLE_ANALYZE="${ENABLE_ANALYZE:-1}"
ENABLE_VACUUM="${ENABLE_VACUUM:-0}"
OFFLINE="${OFFLINE:-0}"
SYNC_EXCHANGES="${SYNC_EXCHANGES:-twse,tpex}"
SYNC_ALL_STOCK_ID_PATTERN="${SYNC_ALL_STOCK_ID_PATTERN:-^\\d+[A-Z]?$}"
SYNC_EXCLUDE_INDUSTRIES="${SYNC_EXCLUDE_INDUSTRIES:-ETN}"
SYNC_COMPANY_STOCK_ID_PATTERN="${SYNC_COMPANY_STOCK_ID_PATTERN:-^\\d{4}$}"

TODAY="$(TZ="$MARKET_TZ" date +%F)"
START_DATE="$(TZ="$MARKET_TZ" date -d "$TODAY - $((RECENT_DAYS - 1)) days" +%F)"
END_DATE="$TODAY"

echo "TW maintenance start"
echo "config=$CONFIG_PATH"
echo "window=$START_DATE..$END_DATE"

if [[ "$ENABLE_UNIVERSE_SYNC" == "1" ]]; then
  python3 "$ROOT_DIR/scripts/sync_tw_universe.py" \
    --config "$CONFIG_PATH" \
    --exchanges "$SYNC_EXCHANGES" \
    --all-stock-id-pattern "$SYNC_ALL_STOCK_ID_PATTERN" \
    --exclude-industries "$SYNC_EXCLUDE_INDUSTRIES" \
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
  python3 "$ROOT_DIR/scripts/backfill_history.py" "${BACKFILL_ARGS[@]}"
fi

if [[ "$ENABLE_WATCHLIST_BUILD" == "1" ]]; then
  python3 "$ROOT_DIR/scripts/build_tw_watchlist.py" \
    --config "$CONFIG_PATH" \
    --companies "$WATCHLIST_COMPANIES" \
    --etfs "$WATCHLIST_ETFS" \
    --lookback-days "$WATCHLIST_LOOKBACK_DAYS" \
    --strategy "$WATCHLIST_STRATEGY"
fi

if [[ "$ENABLE_ANALYZE" == "1" || "$ENABLE_VACUUM" == "1" ]]; then
  python3 - <<'PY'
from pathlib import Path
import os

from src.core.config import load_config
from src.core.database import connect
from src.core.env import load_dotenv

root = Path.cwd()
load_dotenv(root)
config = load_config(os.environ.get("CONFIG_PATH", "config/config_tw.yaml"))
conn = connect(config["database_path"])
if os.environ.get("ENABLE_ANALYZE", "1") == "1":
    conn.execute("ANALYZE;")
if os.environ.get("ENABLE_VACUUM", "0") == "1":
    conn.isolation_level = None
    conn.execute("VACUUM;")
conn.close()
PY
fi

echo "TW maintenance done"

