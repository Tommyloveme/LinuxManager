#!/usr/bin/env bash
# Cedar 维测脚本公共函数。仅供同目录脚本 source，不要直接执行。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CEDAR_UNIT="${CEDAR_UNIT:-cedar}"
CEDAR_HOST="${CEDAR_HOST:-0.0.0.0}"
CEDAR_PORT="${CEDAR_PORT:-8080}"
DATA_DIR="${CEDAR_DATA_DIR:-$ROOT/data}"
PID_FILE="$DATA_DIR/cedar.pid"
UVICORN_LOG="$DATA_DIR/cedar-uvicorn.log"

# 生产机装有 systemd 单元时优先走 systemctl，否则退回 pid 文件方式（开发/临时环境）
use_systemd() {
  command -v systemctl >/dev/null 2>&1 \
    && systemctl list-unit-files "${CEDAR_UNIT}.service" --no-legend 2>/dev/null | grep -q "$CEDAR_UNIT"
}

# 依次探测常见虚拟环境位置，找不到则退回系统 python3
find_python() {
  local candidate
  for candidate in \
    "$ROOT/.venv/bin/python" \
    "$ROOT/backend/.venv/bin/python" \
    /opt/cedar/venv/bin/python; do
    if [[ -x "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  command -v python3
}

pid_of() {
  [[ -f "$PID_FILE" ]] && cat "$PID_FILE" || true
}

pid_running() {
  local pid
  pid="$(pid_of)"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

health_ok() {
  command -v curl >/dev/null 2>&1 || return 0
  curl -fsS "http://127.0.0.1:${CEDAR_PORT}/api/health" >/dev/null 2>&1
}
