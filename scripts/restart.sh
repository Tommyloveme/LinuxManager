#!/usr/bin/env bash
# 重启 Cedar。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_common.sh"

if use_systemd; then
  systemctl restart "$CEDAR_UNIT"
  echo "已通过 systemd 重启 ${CEDAR_UNIT}.service"
  exit 0
fi

"$SCRIPT_DIR/stop.sh"
"$SCRIPT_DIR/start.sh"
