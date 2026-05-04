#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_PATH="${CONFIG_PATH:-config/config_tw.yaml}"
YEARS="${YEARS:-1}"
BATCH_SIZE="${BATCH_SIZE:-25}"
COMPANY_LIMIT="${COMPANY_LIMIT:-50}"
ETF_LIMIT="${ETF_LIMIT:-20}"
MIN_ACTIVE_COMPANIES="${MIN_ACTIVE_COMPANIES:-50}"
MIN_ACTIVE_ETFS="${MIN_ACTIVE_ETFS:-20}"
MIN_WATCHLIST_SIZE="${MIN_WATCHLIST_SIZE:-70}"
INCLUDE_SIGNALS="${INCLUDE_SIGNALS:-1}"
QUIET_DRY_RUN="${QUIET_DRY_RUN:-1}"

echo "Phase 1 readiness check"
echo "config=$CONFIG_PATH"
echo "limits=${COMPANY_LIMIT} companies + ${ETF_LIMIT} etfs"
echo "batch_size=$BATCH_SIZE"

python3 scripts/check_tw_readiness.py \
  --config "$CONFIG_PATH" \
  --min-active-companies "$MIN_ACTIVE_COMPANIES" \
  --min-active-etfs "$MIN_ACTIVE_ETFS" \
  --min-watchlist-size "$MIN_WATCHLIST_SIZE" || true

echo ""
echo "Phase 1 plan"
PLAN_ARGS=(
  --config "$CONFIG_PATH"
  --years "$YEARS"
  --batch-size "$BATCH_SIZE"
  --company-limit "$COMPANY_LIMIT"
  --etf-limit "$ETF_LIMIT"
)
if [[ "$INCLUDE_SIGNALS" == "1" ]]; then
  PLAN_ARGS+=(--include-signals)
fi
python3 scripts/plan_tw_backfill.py "${PLAN_ARGS[@]}"

echo ""
echo "Phase 1 dry-run"
START_DATE="$(python3 - <<'PY'
from datetime import date, timedelta
end_date = date(2026, 4, 8)
print((end_date - timedelta(days=365 - 1)).isoformat())
PY
)"
END_DATE="2026-04-08"
BACKFILL_ARGS=(
  --config "$CONFIG_PATH"
  --start-date "$START_DATE"
  --end-date "$END_DATE"
  --batch-size "$BATCH_SIZE"
  --company-limit "$COMPANY_LIMIT"
  --etf-limit "$ETF_LIMIT"
  --dry-run
)
if [[ "$INCLUDE_SIGNALS" == "1" ]]; then
  BACKFILL_ARGS+=(--include-signals)
fi
if [[ "$QUIET_DRY_RUN" == "1" ]]; then
  DRY_RUN_LOG="logs/tw_phase1_dry_run.log"
  python3 scripts/backfill_tw_market_batches.py "${BACKFILL_ARGS[@]}" >"$DRY_RUN_LOG" 2>&1
  tail -n 20 "$DRY_RUN_LOG"
  echo "full dry-run log: $DRY_RUN_LOG"
else
  python3 scripts/backfill_tw_market_batches.py "${BACKFILL_ARGS[@]}"
fi

echo ""
echo "Phase 1 preflight done"
