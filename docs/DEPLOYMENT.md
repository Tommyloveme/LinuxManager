# 部署指南（SUSE Linux）

## 系统要求

- SUSE Linux Enterprise / openSUSE Leap 15.5+ 或 Tumbleweed
- Python 3.11+
- Node.js 20+（仅构建前端时需要；发布机可只放构建产物）
- 建议以独立系统用户 `cedar` 运行，并通过 sudoers 限定可切换的目标用户

## 快速安装

```bash
sudo ./packaging/install.sh
```

脚本会：

1. 安装 Python 依赖到 `/opt/cedar/venv`
2. 构建前端（若本机有 Node）或使用已有 `frontend/dist`
3. 写入 `/etc/cedar/cedar.env`
4. 安装 systemd 单元 `cedar.service`
5. 默认监听 `0.0.0.0:8080`

访问：`http://<主机>:8080`

首次登录：

- 用户名：`admin`
- 密码：环境变量 `CEDAR_ADMIN_PASSWORD`，未设置时为 `changeme`
- **登录后立刻修改密码**

## 手动开发运行

```bash
# 后端
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CEDAR_DATA_DIR=../data
python -m app.main

# 前端（另一终端）
cd frontend
npm install
npm run dev
```

开发时 Vite 将 API 代理到 `http://127.0.0.1:8080`。

## 配置

复制 `packaging/cedar.env.example` 为 `/etc/cedar/cedar.env`。重要项：

| 变量 | 含义 |
| --- | --- |
| `CEDAR_HOST` | 监听地址，生产可改为内网 IP |
| `CEDAR_PORT` | 发布端口 |
| `CEDAR_SECRET_KEY` | JWT 签名密钥，必须更换 |
| `CEDAR_ADMIN_PASSWORD` | 初始管理员密码 |
| `CEDAR_DATA_DIR` | 数据库与作业产物目录 |
| `CEDAR_ALLOW_USER_SWITCH` | 是否允许 `sudo -u` 切换 Linux 用户 |

## systemd

```bash
sudo systemctl enable --now cedar
sudo systemctl status cedar
journalctl -u cedar -f
```

## 维测脚本

`scripts/` 下提供日常启停与运维入口（自动识别 systemd 或 pid 文件模式）：

```bash
./scripts/start.sh      # 启动并等待健康检查
./scripts/stop.sh       # 优雅停止
./scripts/restart.sh    # 重启
./scripts/status.sh     # 状态 + 健康检查 + 端口监听
./scripts/logs.sh       # 跟踪日志
./scripts/backup.sh     # 备份数据库与配置
```

详见 [scripts/README.md](../scripts/README.md)。

## 防火墙（firewalld）

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

## 权限建议

`/etc/sudoers.d/cedar` 示例（按实际用户收紧）：

```
cedar ALL=(ALL) NOPASSWD: /usr/bin/systemctl, /usr/bin/zypper
Defaults:cedar !requiretty
```

用户切换依赖 `sudo -u <user>`。若 Cedar 不以 root 运行，需要为 `cedar` 配置对应 sudo 规则。
