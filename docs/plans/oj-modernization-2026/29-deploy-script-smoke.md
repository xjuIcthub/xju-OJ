# Step 29：deploy.sh 与全栈 Smoke

## 目标

提供根目录 `./deploy.sh`，覆盖 preflight、build/pull、基础设施 readiness、bootstrap、migration、初始化、启动、smoke 和失败保留现场；不生成或泄露秘密。

## 进入条件

- Step 28 Compose `config --quiet` 和隔离全栈启动通过。
- Step 27 有可消费的 image digest/cache 方案。
- 迁移命令和初始化命令已有明确 owner/幂等语义。
- Phase 2/4 可使用隔离数据和测试 Secret，不要求 Step22 或生产 Secret；Phase 5 生产调用才要求 final backup、生产 Secret 和切换批准。

## deploy.sh 固定行为

脚本必须：

1. `set -eu`，定位仓库根目录。
2. 检查 Docker daemon、Compose v2、必要的 buildx/registry 能力。
3. 加载 `.env`，检查 `${VAR:?message}`、绝对路径和 Secret 文件权限。
4. 执行 `docker compose config --quiet`。
5. 创建必要空目录，不生成/回显 Secret。
6. `DEPLOY_MODE=build` 调 buildx bake/build；`pull` 只拉不可变 image reference。
7. 启动 PG/Redis，等待 healthy。
8. 运行 backend bootstrap-runtime（生产 Secret 缺失即失败）。
9. 运行 migrate；迁移失败非零退出。
10. create-once 初始化 Judge token、管理员；已有值不覆盖。
11. 启动 backend-api、worker、judge-server、frontend，使用 `up -d --remove-orphans --wait`。
12. 执行 HTTP/API/Session/CSRF/public/Judge/Redis/Worker smoke。
13. 只有全部成功才写 `deployments/current.json`，并把上一成功版本保存为 `previous.json`。
14. 每个 build/compose/smoke 步骤的 stdout/stderr 必须实时显示在终端，同时完整写入本次 `runtime/deployments/history/attempt-*` 日志；默认无输出超过 60 秒时显示等待心跳，可用 `DEPLOY_HEARTBEAT_SECONDS` 调整（10–3600 秒）；通过独立状态文件保留原始退出码，不能因 `tee` 丢失失败状态。

## 明确禁止

- `docker compose down -v`。
- 删除 runtime、volume prune、system prune --volumes。
- DROP/重建数据库。
- 重置管理员、Judge token、Django Secret。
- 把 Secret 作为命令行参数、echo、日志或镜像 ARG。
- 域名/端口配置变化时自动 build frontend。

## Smoke 清单

- `GET /`、`/admin/`、`/admin` redirect、deep link。
- `/api/website/`、登录、Session refresh/logout。
- CSRF 合法/非法请求。
- `/public/` 读取、静态缓存 headers。
- backend worker enqueue/result。
- Judge `/ping`、heartbeat、至少一组 `/judge` 和 `/compile_spj`。
- 端口审计：只有 frontend 绑定宿主。
- Redis DB1/DB4 runtime smoke。

## 配置变更路径

只改 `.env` 的域名/端口/upstream 时：

```bash
./deploy.sh --config-only
# 或由脚本识别 config hash 后执行：
docker compose config --quiet
docker compose up -d --remove-orphans --wait
```

不执行依赖下载和业务 build；完成后重新 smoke。

## 前端快速发布路径

为保持前端迭代与后端/判题运行时低耦合，`deploy.sh --frontend-only` 是受限的独立发布模式：

1. 只接受 `BUILD_TARGETS=frontend`（未设置时自动收敛为 `frontend`）。
2. 要求存在上一份成功 `current.json`，并保留上一 release 的 Postgres、Redis、backend、toolchain、server 镜像引用。
3. 比较上一 release source commit 与当前提交/工作树；发现 `frontend/` 以外变更时 fail closed，必须改用完整 `./deploy.sh`。
4. 跳过 Secret provisioning/check、数据库 bootstrap/migration、Judge token/admin 初始化、全栈 `up`、Worker/Judge smoke。
5. 只执行 backend-api 可达检查、`docker compose up -d --no-deps --force-recreate --wait frontend`，以及 frontend root/admin/runtime-config/API 反向代理 smoke。
6. 成功后仍写入完整 release metadata 与 `previous.json`；失败保留现场，不停止其他服务，不删除旧 image/volume/runtime。

镜像复用判断必须将干净工作树视为成功：不要直接把 `git status | grep -q .` 的非零结果作为函数退出码，否则前端/后端变更会误触发 PostgreSQL、Judge 等未变化镜像的重建和外部依赖下载。

推荐命令：

```bash
BUILD_TARGETS=frontend ./deploy.sh --frontend-only --dry-run
BUILD_TARGETS=frontend ./deploy.sh --frontend-only
```

前端-only 模式不能用于首次安装、Compose/环境变更、backend/OIDC/migration 变更或无上一成功 release 的主机；这些情况必须走完整部署门。

## 计划命令

```bash
shellcheck deploy.sh
sh -n deploy.sh
git diff --check
./deploy.sh --help
./deploy.sh --dry-run
```

`--dry-run` 只校验，不读取/打印 Secret 内容。脚本开发和首次验收只在 WSL/huawei1 隔离 staging 运行；通过 Phase 4 后，同一已验收脚本才可在 Phase 5 批准的生产窗口执行。

## 验收

- 首次部署、普通升级、仅配置变更、pull 模式、build 模式均有记录。
- 失败返回非零，保存 `docker compose ps`、无 Secret 日志和当前 deployment metadata。
- 成功后 current/previous/history 含 release tag、commit、完整 image digest、时间。
- smoke 失败不会自动删除旧服务/卷/Secret。

## 停止条件

- 任何 Secret 进入日志/命令/镜像。
- 迁移/初始化失败仍继续启动业务。
- 失败路径自动删卷、删库或重置账号。
- smoke 没覆盖 Session/CSRF、Judge、DB1/DB4 或端口隔离。

## 回滚

脚本本身失败时保留现场，人工按 Step30 选择旧 Compose/旧 digest。脚本不得自动执行不可逆数据回滚。

## 完成标志

提交格式建议：

```text
feat(deploy): add fail-closed compose deployment entrypoint
```
