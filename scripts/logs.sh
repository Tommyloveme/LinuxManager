#!/usr/bin/env bash
# 跟踪 Cedar 日志。systemd 部署走 journalctl，否则 tail 数据目录下的日志文件。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if use_systemd; then
  exec journalctl -u "$CEDAR_UNIT" -f --no-pager
fi

FILES=()
[[ -f "$DATA_DIR/cedar.log" ]] && FILES+=("$DATA_DIR/cedar.log")
[[ -f "$UVICORN_LOG" ]] && FILES+=("$UVICORN_LOG")
if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "暂无日志文件（$DATA_DIR 下未找到 cedar.log / cedar-uvicorn.log）"
  exit 1
fi
exec tail -n 100 -f "${FILES[@]}"
