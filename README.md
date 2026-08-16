# Cedar

SUSE Linux 上的主机运维控制台。通过发布端口在浏览器里完成用户切换、脚本与批处理、文件打包同步、进程与服务管理、以及接近原生的终端操作。

默认地址：`http://<主机>:8080`

## 能做什么

1. **Linux 用户**：列出系统用户，把后续操作切换到指定账号（`sudo -u`）。
2. **脚本库**：保存、编辑、单次或批量执行脚本。
3. **批处理**：把命令、脚本、打包、同步、进程/服务动作编成可复用流程，支持失败停止或继续。
4. **文件**：浏览目录、上传下载、按正则从多个目录收集文件并打包，以及目录同步。
5. **进程与资源**：查看 CPU/内存、结束进程；在 SUSE 上管理 systemd 单元。
6. **终端**：浏览器 PTY，顶栏持续显示当前 Linux 用户与工作目录。
7. **作业与审计**：长任务产物可下载；写操作留痕。

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
