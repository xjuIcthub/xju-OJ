# 阶段 05：统一 Compose、CI、镜像发布与仓库文档

## 目标

让仓库根目录以一个明确、可本地构建的部署入口编排 `frontend`、`backend-api`、`backend-worker`、`server`、PostgreSQL 和 Redis；同步把零散模块 CI 合并为根工作流，并让 README、环境变量和运维说明反映新三模块结构。

## 进入条件

- `frontend/Dockerfile` 已独立构建。
- `backend/Dockerfile` 已能分别启动 migrate/API/worker。
- `server/Dockerfile` 已能构建并通过核心协议/沙箱测试。
- 阶段 00 的数据备份与回滚资源仍可用。
- 还未删除根旧 `docker-compose.yml` 或远程 `1.6.1` 镜像引用；它们将作为兼容回退，在阶段 06 清理。

## 步骤 05.1：确定 Compose 文件与服务命名

推荐采用：

```text
deploy/compose.yaml           # 新的生产/类生产本地编排
deploy/compose.dev.yaml       # 源码挂载、调试端口和开发便利项
deploy/compose.legacy.yaml    # 当前远程镜像拓扑的只读回退快照
deploy/env.example            # 变量名、是否必填、无秘密示例
deploy/README.md              # 启动、备份、切换、故障排除
a compose wrapper 或根 README # 统一调用方式
```

目标服务名建议固定为：

```text
frontend
backend-migrate
backend-api
backend-worker
server
oj-postgres
oj-redis
```

服务名是内部协议的一部分，必须同步使用：

| 用途 | 目标值 |
|---|---|
| frontend `/api` 上游 | `backend-api:8000` |
| server heartbeat BACKEND_URL | `http://backend-api:8000/api/judge_server_heartbeat/` |
| server 上报 service_url | `http://server:8080` |
| backend PostgreSQL host | `oj-postgres` |
| backend Redis host | `oj-redis` |
| frontend 静态根 | frontend 镜像内 dist |

可在外部反向代理场景改端口映射，但内部 DNS 名称、API 路径和 JudgeServer 协议不应随意变化。

## 步骤 05.2：编排网络、卷和权限

### 网络

- 仅 `frontend` 映射宿主机 `80/443`（开发 profile 可以映射其他端口）；
- `backend-api`、`backend-worker`、`server`、PostgreSQL、Redis 不直接发布公网端口；
- 使用一个内部网络即可起步，但 server 只需与 backend 和数据卷通信；如 Compose 支持，标记数据网络为 internal；
- `server` 继续 `read_only: true`、`tmpfs: /tmp`，并保留安全 capability drop；
- 不把 Docker socket、host PID、特权模式或额外 CAP 交给 server。

### 卷

```text
${RUNTIME_ROOT}/postgres            -> oj-postgres 数据目录
${RUNTIME_ROOT}/redis               -> oj-redis 数据目录
${RUNTIME_ROOT}/backend             -> backend /data（读写）
${RUNTIME_ROOT}/backend/public      -> frontend /data/public（只读）
${RUNTIME_ROOT}/backend/test_case   -> server /test_case（只读）
${RUNTIME_ROOT}/judge-server/log    -> server /log（读写）
${RUNTIME_ROOT}/judge-server/run    -> server /judger（读写）
```

绝不使用：

```text
frontend <- runtime/backend 整体挂载
server   <- runtime/backend/config
server   <- runtime/backend/public
backend  <- runtime/judge-server/run
```

建立运行目录前用 `umask 077` 保护秘密，再由 bootstrap 明确放宽 public/test-case 必需权限。挂载路径必须逐个在容器内验证，而不是只看 Compose YAML。

## 步骤 05.3：迁移服务与启动顺序

`depends_on` 只表示创建顺序，不等于数据库/Redis 已就绪。实现以下序列：

1. `oj-postgres` 和 `oj-redis` 有健康检查；
2. `backend-migrate` 等待二者可用，然后执行 bootstrap/check/migrate；
3. `backend-api` 和 `backend-worker` 只在 migration 成功后启动；
4. `server` 可与 backend-api 同时启动，但 heartbeat 重试与 API readiness 必须明确；
5. `frontend` 等待 backend-api 可访问，或在早期返回受控 502；
6. 生产发布脚本在关闭旧流量前运行一次 migration/health preflight。

若目标 Docker Compose 版本不支持 `service_completed_successfully`，不要伪造条件依赖。改用一个可审计的部署命令：

```bash
docker compose -f deploy/compose.yaml run --rm backend-migrate
docker compose -f deploy/compose.yaml up -d backend-api backend-worker server frontend
```

将实际部署方式写入 `deploy/README.md`，并由 CI 的 integration job 使用同一流程。

## 步骤 05.4：定义环境变量与秘密边界

`deploy/env.example` 仅列变量名、用途和安全的占位符，不能提供真实密码：

| 变量 | 必需 | 用途 |
|---|---:|---|
| `RUNTIME_ROOT` | 是 | 运行数据根目录，不提交 Git |
| `POSTGRES_DB` | 是 | 数据库名 |
| `POSTGRES_USER` | 是 | 数据库账户 |
| `POSTGRES_PASSWORD` | 是 | 数据库密码/秘密管理引用 |
| `JUDGE_SERVER_TOKEN` | 是 | backend/server 共享原始 token，不输出 |
| `POSTGRES_HOST`/`POSTGRES_PORT` | 否 | 覆盖内部默认服务名 |
| `REDIS_HOST`/`REDIS_PORT` | 否 | 覆盖内部默认服务名 |
| `OJ_DATA_DIR` | 否 | backend `/data` 覆盖 |
| `GUNICORN_WORKERS`/`GUNICORN_THREADS` | 否 | API 并发 |
| `DRAMATIQ_PROCESSES`/`DRAMATIQ_THREADS` | 否 | Worker 并发 |
| `FORCE_HTTPS` | 否 | frontend/TLS 部署策略 |
| `STATIC_CDN_HOST` | 否 | 首轮通常不设置，避免路径双重改写 |
| `INITIAL_ADMIN_*` | 新安装时 | 一次性 bootstrap，不用于升级 |

要求：

- `.env`、`.env.local`、runtime 和密钥文件继续被 `.gitignore` 覆盖；
- CI 使用 secret store，日志中屏蔽值；
- backend 仅将 `JUDGE_SERVER_TOKEN` 写入数据库的既有 SysOptions 兼容字段，server 仅从环境读取；
- frontend 镜像和浏览器 bundle 不拥有任何数据库/判题秘密；
- `ALLOWED_HOSTS`、Sentry DSN 等生产配置逐步移到环境变量；本轮至少不要把现有值复制进新配置。

## 步骤 05.5：Compose 验证矩阵

每次改 Compose 先执行静态验证：

```bash
docker compose --env-file deploy/.env.local -f deploy/compose.yaml config
docker compose --env-file deploy/.env.local -f deploy/compose.dev.yaml config
docker compose -f deploy/compose.legacy.yaml config
```

然后执行构建和生命周期验证：

```bash
docker compose --env-file deploy/.env.local -f deploy/compose.yaml build
docker compose --env-file deploy/.env.local -f deploy/compose.yaml up -d oj-postgres oj-redis
docker compose --env-file deploy/.env.local -f deploy/compose.yaml run --rm backend-migrate
docker compose --env-file deploy/.env.local -f deploy/compose.yaml up -d backend-api backend-worker server frontend
docker compose --env-file deploy/.env.local -f deploy/compose.yaml ps
docker compose --env-file deploy/.env.local -f deploy/compose.yaml logs --tail=200 backend-api backend-worker server frontend
```

测试不要用硬编码秘密。可在受控环境生成一次短期测试 Token，并在销毁环境后撤销。

## 步骤 05.6：统一 CI 为根工作流

当前前/后端/JudgeServer 的 release workflow 分散在模块内，目录移动后 build context 会错误。创建根 `.github/workflows/`，建议至少有以下 jobs：

### `repository-hygiene`

- `git diff --check`；
- 确认 `.env`、运行时数据、私钥、node_modules、测试构建输出未被 Git 跟踪；
- 检查 root 只存在 `frontend/backend/server` 三个业务模块；
- 确认许可证文件和 `server/LICENSES.md` 存在；
- Markdown link check（包括本计划）。

### `frontend-build`

- 固定与 `.nvmrc` 一致的 Node/Yarn；
- `yarn install --frozen-lockfile`；
- lint、`build:dll`、build；
- 上传 `dist` 作为 CI artifact；
- 不需要数据库、不读取 secrets。

### `backend-test`

- 使用与 Dockerfile 一致的 Python；
- 启动临时 PostgreSQL/Redis；
- `check`、migration plan、`makemigrations --check --dry-run`、flake8、原有 app 测试；
- 在日志中不打印连接密码或 Token。

### `server-test`

- 构建 `server/Dockerfile`；
- 运行 Judger CMake/binding/Seccomp 测试；
- 启动临时 server，运行 `/ping`、Token 拒绝和 JudgeServer client 测试；
- 用独立测试数据卷，不接触生产数据。

### `integration-compose`

- 使用新 `deploy/compose.yaml` 构建；
- bootstrap、启动所有服务；
- 验证 frontend 路由、`/api/website/`、heartbeat、一次 submission；
- 失败时上传 Compose log、Django/Server/Judger log（脱敏）。

### `release-images`

- tag 触发，明确版本策略；
- 分别构建/push `frontend`、`backend`、`server` 镜像；
- 使用显式 Dockerfile/context；
- 输出不可变 digest；
- 不因发布 job 跳过测试；
- 生产 Compose 固定使用发布 tag/digest，避免同 tag 被覆盖。

旧模块内 `.travis.yml` 和子目录 GitHub workflow 可在根 workflow 连续成功后删除或改为迁移说明；删除前保存其覆盖范围到 CI inventory。

## 步骤 05.7：更新文档

更新顺序：

1. 根 `README.md`、`README.en.md`：三模块概览、快速开发、部署入口、无需再 clone 上游 `OnlineJudgeDeploy`；
2. `frontend/README.md`：Node/Yarn、开发 proxy、构建、路由；
3. `backend/README.md`：Python、API/Worker/migration、数据目录、测试；
4. `server/README.md`：安全前提、语言 runtime、测试、仅内网暴露；
5. `deploy/README.md`：环境、首次安装、升级、备份、回滚、故障排查；
6. `docs/operations/backup-and-recovery.md`：PostgreSQL + Redis + test_case + public + config 的一致性备份；
7. `docs/operations/observability.md`：API、Worker、JudgeServer、Nginx 的健康与日志；
8. `docs/contracts/`：链接回本计划的兼容约束。

移除或标注过时内容：默认 `root/rootroot`、旧 `OnlineJudgeDeploy` clone 指令、后端下载前端 release、失效 JudgeServer 子模块操作、`oj-backend:8080` 旧前端上游。

## 建议提交点

```text
feat(deploy): compose frontend backend and server services
ci: validate all three modules and compose integration
 docs: document unified development deployment and recovery
```

## 验收门槛

- [ ] 新 Compose 只使用 `frontend/`、`backend/`、`server/` 作为源码 build context。
- [ ] 只有 frontend 对外开放 HTTP/HTTPS；server 和 Redis/PostgreSQL 无公网端口。
- [ ] API/Worker/Migrate/Server 进程、网络、卷和权限按目标边界运行。
- [ ] `compose config`、单模块 build、全栈 build 和 integration 测试通过。
- [ ] CI 对三模块和整合路径都有可重复、无秘密的检查。
- [ ] 文档不再把本仓库描述成“需要自行拼装的四个上游模块”。

## 停止条件与回滚

Compose 构建上下文包含 runtime/秘密、frontend 可以读取 test_case、server 暴露到公网、migration 无法保证一次性执行、CI 需要真实生产 secret 或新编排未通过端到端测试时停止。保留 `compose.legacy.yaml`、旧镜像 tag/digest 和阶段 00 数据备份，直到阶段 06 演练通过后再清理。
