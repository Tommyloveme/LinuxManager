#!/usr/bin/env bash
# 停止 Cedar。先 TERM 优雅退出，超时后 KILL。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if use_systemd; then
  systemctl stop "$CEDAR_UNIT"
  echo "已通过 systemd 停止 ${CEDAR_UNIT}.service"
  exit 0
fi

if ! pid_running; then
  echo "Cedar 未在运行"
  rm -f "$PID_FILE"
  exit 0
fi

PID="$(pid_of)"
kill "$PID"
for _ in $(seq 1 20); do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "已停止（pid $PID）"
    exit 0
  fi
  sleep 0.5
done
echo "优雅退出超时，强制结束 pid $PID"
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
