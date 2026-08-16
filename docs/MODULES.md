# 扩展指南

复制下面的骨架即可增加一个业务模块，不必改动其他模块内部实现。

## 后端

1. `backend/app/modules/<name>/service.py` 只写业务。
2. `backend/app/api/v1/<name>.py` 只做鉴权、校验、调用 service。
3. 在 `backend/app/api/v1/__init__.py` 挂载路由。
4. 在 `backend/app/core/module_registry.py` 增加 `ModuleSpec`，总览页会自动出现。
5. 需要跑 Linux 命令时用 `LinuxExecutor`，不要 `os.system`。
6. 写操作调用 `AuditService.record`。

## 前端

1. `frontend/src/views/<Name>View.vue`
2. 在 `frontend/src/router/index.ts` 与侧栏 `AppLayout.vue` 增加入口
3. 只通过 `frontend/src/api/client.ts` 访问接口

## 提交

`feat(<name>): 一句话说明为什么加这项能力`
