# 维测脚本

日常启停与运维入口。所有脚本自动识别部署形态：

- **生产**（已安装 `cedar.service`）：转发给 `systemctl` / `journalctl`；
- **开发/临时环境**：用 pid 文件（`data/cedar.pid`）直接管理 uvicorn 进程。

| 脚本 | 作用 |
| --- | --- |
| `start.sh` | 启动服务，等待健康检查通过 |
| `stop.sh` | 优雅停止，超时后强制结束 |
| `restart.sh` | 重启 |
| `status.sh` | 运行状态 + 健康检查 + 端口监听 |
| `logs.sh` | 跟踪日志（journalctl 或 tail） |
| `backup.sh` | 备份 SQLite 数据库与配置到 `backups/` |

用法示例：

```bash
./scripts/start.sh
./scripts/status.sh
CEDAR_PORT=9000 ./scripts/restart.sh   # 环境变量可覆盖端口等默认值
./scripts/backup.sh
```

可用的环境变量：`CEDAR_UNIT`（systemd 单元名）、`CEDAR_HOST`、`CEDAR_PORT`、`CEDAR_DATA_DIR`、`BACKUP_DIR`。

`_common.sh` 是公共函数库，仅供其它脚本 `source`，不要直接执行。
