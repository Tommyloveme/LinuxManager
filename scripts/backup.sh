#!/usr/bin/env bash
# 备份 Cedar 数据：SQLite 数据库、环境配置，打包到 backups/ 下带时间戳的 tar.gz。
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="$BACKUP_DIR/cedar-backup-$STAMP.tar.gz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

DB="$DATA_DIR/cedar.db"
if [[ -f "$DB" ]]; then
  # sqlite3 .backup 可在服务运行中拿到一致快照；没有 sqlite3 时退化为直接复制
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB" ".backup '$TMP/cedar.db'"
  else
    cp "$DB" "$TMP/cedar.db"
  fi
else
  echo "警告：未找到数据库 $DB，仅备份配置"
fi

[[ -f /etc/cedar/cedar.env ]] && cp /etc/cedar/cedar.env "$TMP/cedar.env"
[[ -f "$ROOT/backend/.env" ]] && cp "$ROOT/backend/.env" "$TMP/backend.env"

mkdir -p "$BACKUP_DIR"
tar -czf "$TARGET" -C "$TMP" .
echo "备份完成：$TARGET"
ls -lh "$TARGET"
