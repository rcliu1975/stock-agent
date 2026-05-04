#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="stock-agent-tw-daily"
ON_CALENDAR="${ON_CALENDAR:-Mon..Fri 15:50}"
PERSISTENT="${PERSISTENT:-true}"

mkdir -p "$SYSTEMD_DIR"

cat > "${SYSTEMD_DIR}/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=stock-agent TW daily automation
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=${ROOT_DIR}
ExecStart=/usr/bin/env bash ${ROOT_DIR}/scripts/run_tw_automation.sh

[Install]
WantedBy=default.target
EOF

cat > "${SYSTEMD_DIR}/${SERVICE_NAME}.timer" <<EOF
[Unit]
Description=Run stock-agent TW daily automation on schedule

[Timer]
OnCalendar=${ON_CALENDAR}
Persistent=${PERSISTENT}
Unit=${SERVICE_NAME}.service

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "${SERVICE_NAME}.timer"

echo "installed: ${SYSTEMD_DIR}/${SERVICE_NAME}.service"
echo "installed: ${SYSTEMD_DIR}/${SERVICE_NAME}.timer"
echo "schedule: ${ON_CALENDAR}"
echo "check: systemctl --user list-timers ${SERVICE_NAME}.timer"

