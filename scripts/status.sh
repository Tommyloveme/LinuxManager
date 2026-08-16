#!/usr/bin/env bash
# 查看 Cedar 运行状态与健康检查结果。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if use_systemd; then
  systemctl status "$CEDAR_UNIT" --no-pager || true
elif pid_running; then
  echo "运行中（pid $(pid_of)，pid 文件：$PID_FILE）"
else
  echo "未运行"
fi

if command -v curl >/dev/null 2>&1; then
  if health_ok; then
    echo "健康检查：OK（http://127.0.0.1:${CEDAR_PORT}/api/health）"
  else
    echo "健康检查：失败（端口 ${CEDAR_PORT} 无响应）"
  fi
fi

if command -v ss >/dev/null 2>&1; then
  echo "端口监听："
  ss -ltnp 2>/dev/null | grep ":${CEDAR_PORT}" || echo "  （端口 ${CEDAR_PORT} 未监听）"
fi
