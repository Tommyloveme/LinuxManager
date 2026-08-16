# Cedar 架构说明

Cedar 是运行在 SUSE Linux 上的主机运维控制台。浏览器通过发布端口访问，后端以本机身份（或切换后的 Linux 用户）执行运维操作。

## 设计目标

- **分层清晰**：表现层、接口层、应用服务、适配器、基础设施彼此独立。
- **模块可插拔**：每个业务能力是一个独立模块，通过注册表挂到 API 上。
- **新增功能成本低**：复制一个模块目录、注册路由、补前端页面即可。
- **单机可部署**：SQLite + 静态前端，不强制依赖外部中间件。

## 逻辑分层

```
┌──────────────────────────────────────────────┐
│  Presentation   Vue 3 SPA（浏览器）           │
├──────────────────────────────────────────────┤
│  Interface      FastAPI routers / WebSocket  │
├──────────────────────────────────────────────┤
│  Application    modules/* 业务服务            │
├──────────────────────────────────────────────┤
│  Adapter        executor / pty / archive     │
├──────────────────────────────────────────────┤
│  Infrastructure config / db / security / log │
└──────────────────────────────────────────────┘
```

依赖方向只允许自上而下。模块之间不互相 import 实现细节，共享能力走适配器或基础设施。

## 目录约定

| 路径 | 职责 |
| --- | --- |
| `backend/app/core` | 配置、安全、日志、模块注册 |
| `backend/app/db` | SQLAlchemy 模型与会话 |
| `backend/app/api` | HTTP / WebSocket 接口，不做业务 |
| `backend/app/modules` | 领域服务：脚本、批处理、文件、进程等 |
| `backend/app/adapters` | 对接操作系统：命令执行、PTY、打包 |
| `frontend/src/views` | 页面 |
| `frontend/src/api` | 对后端的唯一入口 |
| `packaging` | systemd、安装脚本、示例配置 |

## 运行时数据流

1. 浏览器携带 JWT 调用 `/api/v1/...`。
2. 路由层做鉴权，把「当前 Web 用户」和「当前 Linux 身份」交给模块服务。
3. 模块服务通过 `LinuxExecutor` 以指定用户执行命令，或通过 PTY 打开终端。
4. 写操作写入审计日志；长任务进入作业队列，前端轮询或稍后扩展 WebSocket 推送。

## 扩展一个新功能

1. 在 `backend/app/modules/<name>/` 增加 `service.py`。
2. 在 `backend/app/api/v1/` 增加路由，只调用该服务。
3. 在 `backend/app/core/module_registry.py` 注册模块元数据（名称、路由前缀、权限）。
4. 前端增加 `src/api/<name>.ts` 与 `src/views/<Name>View.vue`，在侧栏配置里加一项。
5. 补文档与一次独立 git commit。

详见 [REPO_GUIDE.md](./REPO_GUIDE.md)。

## 安全边界

- Web 登录与 Linux 用户切换是两套身份。
- 文件路径必须规范化并拒绝 `..` 逃逸。
- 终端与任意命令执行仅对已认证会话开放，并写入审计。
- 默认只监听可配置地址；生产环境应置于内网或反向代理之后。
