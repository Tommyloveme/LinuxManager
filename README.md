# Cedar

SUSE Linux 上的主机运维控制台。通过发布端口在浏览器里完成用户切换、脚本与批处理、文件打包同步、进程与服务管理、以及接近原生的终端操作。

默认地址：`http://<主机>:8080`

## 能做什么

1. **运行概览**：主机资源、负载与网络的实时摘要。
2. **进程与服务**：进程按 CPU/内存排序、结束/强杀，systemd 单元启停，支持实时自动刷新。
3. **执行身份**：选择 Linux 用户并输入其密码校验（通过 `su`），之后脚本、终端、命令都以该用户运行；密码只留在服务内存。
4. **脚本中心**：保存、编辑、单次或批量执行脚本，列表内直接勾选批量运行。
5. **文件管理**：浏览、名称正则过滤、隐藏文件开关、文本/图片预览；批量下载到本机（复制文件或打成压缩包）；本机文件批量上传（含拖拽）。
6. **远程终端**：浏览器 PTY，顶栏随 shell 内 `cd` 实时显示当前用户与目录。

界面是暖纸色 + 石色侧栏，避免常见的紫渐变「AI 风」。

## 快速开始（开发）

需要 Python 3.11+ 与 Node 20+。

```bash
# 后端
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 前端（另一终端）
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 提示的地址（默认 `http://127.0.0.1:5173`）。  
登录：`admin` / `changeme`。

生产安装见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)，仓库约定见 [docs/REPO_GUIDE.md](docs/REPO_GUIDE.md)，分层与扩展点见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 架构一览

```
frontend (Vue 3)  →  /api/v1  →  FastAPI routers
                                      ↓
                               modules/* 业务服务
                                      ↓
                          adapters: executor / pty / archive
                                      ↓
                               SQLite + 本机操作系统
```

新增功能：复制一个 `backend/app/modules/<name>`，挂路由，在 `module_registry.py` 登记，前端加页面即可。

## 许可

内部运维工具，按仓库现状使用。请勿把控制台暴露到公网而不加认证与网络隔离。
