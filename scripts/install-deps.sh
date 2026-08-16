#!/usr/bin/env bash
# 安装/修复后端 Python 依赖：在仓库根创建 .venv 并安装 backend/requirements.txt。
# 需要走镜像源时：PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple ./scripts/install-deps.sh
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/_common.sh"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3，请先安装（openSUSE：sudo zypper install python313 python313-pip）"
  exit 1
fi

install_deps

PY="$ROOT/.venv/bin/python"
MISSING="$(missing_deps "$PY")"
if [[ -n "$MISSING" ]]; then
  echo "安装后仍缺失模块：$MISSING，请检查 pip 输出中的报错"
  exit 1
fi
echo "依赖安装完成，全部模块可导入。解释器：$PY"
"$PY" --version
