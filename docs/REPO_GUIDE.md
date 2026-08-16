# 代码仓维护指导手册

本手册说明如何用 Git 维护 Cedar，以及日常开发、发版、回滚应遵循的约定。

## 仓库结构

```
.
├── backend/          Python FastAPI 后端
├── frontend/         Vue 3 前端
├── docs/             架构与运维文档
├── packaging/        systemd 与安装脚本
├── Makefile          常用入口
└── README.md
```

不要把运行时数据（`data/`、上传包、SQLite 文件）提交进仓库。

## 分支模型

| 分支 | 用途 |
| --- | --- |
| `main` | 可部署的稳定线，只接受评审后的合并 |
| `feat/<topic>` | 新功能 |
| `fix/<topic>` | 缺陷修复 |
| `docs/<topic>` | 仅文档 |
| `chore/<topic>` | 构建、依赖、仓库卫生 |

单人开发也可直接在 `main` 上按功能做小步提交，但每个提交必须只做一件事。

## 提交信息

使用约定式提交，中英均可，但类型字段用英文：

```
<type>(<scope>): <简短说明>

可选正文：为什么改，而不是改了哪些文件。
```

常用 type：

- `feat` 新能力
- `fix` 缺陷
- `docs` 文档
- `refactor` 不改行为的结构调整
- `test` 测试
- `chore` 工具与依赖
- `build` 打包与安装脚本

scope 建议与模块同名：`auth`、`scripts`、`playbooks`、`files`、`process`、`terminal`、`system`、`ui`。

示例：

```
feat(playbooks): 支持步骤失败后继续或中止

批处理在生产排障时需要「尽量跑完」，因此为每个步骤增加 on_error 策略。
```

## 开发流程

1. 从 `main` 拉最新代码。
2. 只改一个模块（或一层：先后端、再前端）。
3. 本地验证：
   - 后端：`make backend-dev`
   - 前端：`make frontend-dev`
   - 有测试时：`make test`
4. 提交。不要把无关格式化、无关文件混进同一 commit。
5. 推送并（如有团队）开 Merge Request。

## 模块边界检查

提交前自问：

- API 层是否只做参数校验和调用 service？
- 新模块是否走 `LinuxExecutor`，而不是直接 `os.system`？
- 写操作是否记了审计？
- 前端是否只通过 `src/api` 访问后端？

违反边界的改动应在评审中打回。

## 版本号

采用语义化版本 `MAJOR.MINOR.PATCH`，写在：

- `backend/app/core/config.py` 的 `app_version`
- `frontend/package.json` 的 `version`
- Git tag：`v1.0.0`

发版步骤：

1. 更新版本号与 `docs/CHANGELOG.md`。
2. 提交 `chore(release): vX.Y.Z`。
3. `git tag -a vX.Y.Z -m "Cedar vX.Y.Z"`。
4. 按 [DEPLOYMENT.md](./DEPLOYMENT.md) 打包安装。

## 回滚

- 应用回滚：检出上一个 tag，重新执行安装脚本或 `systemctl restart cedar`。
- 数据：SQLite 文件在 `data/cedar.db`，发版前可复制一份。schema 变更必须可向前兼容或提供迁移脚本。

## Code Review 清单

- 权限：未登录不能打到敏感接口。
- 路径：文件接口做了规范化。
- 超时：外部命令有 timeout。
- 日志：不打印密码、密钥。
- UI：新增页面走现有布局与设计令牌，不引入新的视觉体系。

## 日常卫生

每周或每个迭代结束：

```bash
git fetch --all --prune
make lint
```

删除已合并的功能分支。不要 force push `main`。
