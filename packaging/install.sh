#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-/opt/cedar}"
DATA_DIR="${DATA_DIR:-/var/lib/cedar}"
ENV_DIR="${ENV_DIR:-/etc/cedar}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请使用 root 运行：sudo $0"
  exit 1
fi

id cedar >/dev/null 2>&1 || useradd --system --home "$DATA_DIR" --shell /sbin/nologin cedar

mkdir -p "$PREFIX" "$DATA_DIR" "$ENV_DIR"
rsync -a --delete --exclude '.venv' --exclude 'node_modules' --exclude 'data' "$ROOT/backend" "$PREFIX/"
rsync -a --delete --exclude 'node_modules' "$ROOT/frontend" "$PREFIX/"
rsync -a "$ROOT/docs" "$PREFIX/" 2>/dev/null || true

python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install -U pip
"$PREFIX/venv/bin/pip" install -r "$PREFIX/backend/requirements.txt"

if command -v npm >/dev/null 2>&1; then
  (cd "$PREFIX/frontend" && npm install && npm run build)
fi

if [[ ! -f "$ENV_DIR/cedar.env" ]]; then
  cp "$ROOT/packaging/cedar.env.example" "$ENV_DIR/cedar.env"
  chmod 640 "$ENV_DIR/cedar.env"
fi

install -m 644 "$ROOT/packaging/cedar.service" /etc/systemd/system/cedar.service
chown -R cedar:cedar "$PREFIX" "$DATA_DIR"
systemctl daemon-reload
systemctl enable --now cedar
echo "Cedar 已启动。访问 http://$(hostname -f 2>/dev/null || hostname):8080"
