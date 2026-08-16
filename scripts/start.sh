#!/usr/bin/env bash
# 启动 Cedar。systemd 部署等价于 systemctl start cedar；否则用 uvicorn + pid 文件。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if use_systemd; then
  systemctl start "$CEDAR_UNIT"
  echo "已通过 systemd 启动 ${CEDAR_UNIT}.service"
  exit 0
fi

if pid_running; then
  echo "Cedar 已在运行（pid $(pid_of)），无需重复启动"
  exit 0
fi

mkdir -p "$DATA_DIR"
PY="$(find_python)"

# 启动前自检依赖；缺失时默认自动装进仓库根 .venv（CEDAR_AUTO_INSTALL=0 可关闭）
MISSING="$(missing_deps "$PY")"
if [[ -n "$MISSING" ]]; then
  echo "检测到缺失的 Python 依赖：$MISSING"
  if [[ "${CEDAR_AUTO_INSTALL:-1}" == "1" ]]; then
    echo "开始自动安装（可设 CEDAR_AUTO_INSTALL=0 关闭自动安装）..."
    install_deps
    PY="$(find_python)"
    MISSING="$(missing_deps "$PY")"
  fi
  if [[ -n "$MISSING" ]]; then
    echo "依赖仍不完整：$MISSING"
    echo "请手动安装后重试："
    echo "  python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt"
    echo "详见 docs/DEPLOYMENT.md 的「Python 依赖安装」章节。"
    exit 1
  fi
  echo "依赖安装完成"
fi

echo "使用 $PY 启动，监听 ${CEDAR_HOST}:${CEDAR_PORT}，日志：$UVICORN_LOG"
cd "$ROOT/backend"
nohup "$PY" -m uvicorn app.main:app --host "$CEDAR_HOST" --port "$CEDAR_PORT" >>"$UVICORN_LOG" 2>&1 &
echo $! >"$PID_FILE"

for _ in $(seq 1 20); do
  if health_ok; then
    echo "启动成功：http://127.0.0.1:${CEDAR_PORT}（pid $(pid_of)）"
    exit 0
  fi
  sleep 0.5
done
echo "进程已拉起（pid $(pid_of)），但健康检查暂未通过，请查看 $UVICORN_LOG"
