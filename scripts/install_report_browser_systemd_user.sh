#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="stock-agent-report-browser"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8787}"
REPORTS_DIR="${REPORTS_DIR:-reports/daily}"

mkdir -p "$SYSTEMD_DIR"

cat > "${SYSTEMD_DIR}/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=stock-agent read-only report browser
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${ROOT_DIR}
ExecStart=/usr/bin/env python3 ${ROOT_DIR}/scripts/report_browser.py --host ${HOST} --port ${PORT} --reports-dir ${REPORTS_DIR}
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}.service"

echo "installed: ${SYSTEMD_DIR}/${SERVICE_NAME}.service"
echo "listen: http://${HOST}:${PORT}"
echo "check: systemctl --user status ${SERVICE_NAME}.service"
