#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${1:-$ROOT_DIR/data/stock_agent.sqlite}"
BACKUP_DIR="${2:-$ROOT_DIR/data/backups}"

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB_PATH" ]]; then
  echo "database not found: $DB_PATH" >&2
  exit 1
fi

STAMP="$(date +%Y-%m-%d_%H%M%S)"
TARGET="$BACKUP_DIR/$(basename "${DB_PATH%.sqlite}")_${STAMP}.sqlite"
cp "$DB_PATH" "$TARGET"

echo "backup created: $TARGET"

