# 贡献说明

请先阅读：

- [架构](./ARCHITECTURE.md)
- [仓库维护](./REPO_GUIDE.md)
- [如何加模块](./MODULES.md)

补丁应保持分层：路由不写业务，模块不直接操作 HTTP，适配器是唯一碰操作系统的地方。
