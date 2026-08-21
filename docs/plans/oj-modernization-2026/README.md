# xju-OJ 2026 现代化迁移总计划

> 状态：**仅规划，尚未执行本轮现代化改造**。
>
> 本计划依据 `docs/research/01-*.md` 至 `07-*.md` 制定，并继承
> `docs/plans/oj-unification/` 已完成的三模块目录迁移成果。
>
> 目标是把现有 OJ 逐步升级为可长期维护、可回滚、可重复构建的系统；不是一次性重写。

## 1. 调研证据映射

- [01-version-baseline.md](../../research/01-version-baseline.md)：生命周期、候选版本和总迁移顺序。
- [02-frontend-modernization.md](../../research/02-frontend-modernization.md)：pnpm/Vite/Vue3、双入口、Nginx、编辑器和浏览器合同。
- [03-backend-modernization.md](../../research/03-backend-modernization.md)：uv、Django 分跳、历史 migration、JSONField、Psycopg3 和 Worker。
- [04-data-platform-upgrade.md](../../research/04-data-platform-upgrade.md)：PostgreSQL/Redis ladder、备份、队列 drain、切换和数据回滚。
- [05-server-judger-modernization.md](../../research/05-server-judger-modernization.md)：JudgeServer/Judger、工具链、Seccomp、权限和多架构。
- [06-container-build-strategy.md](../../research/06-container-build-strategy.md)：Docker 分层、BuildKit cache、Bake、digest 和供应链。
- [07-compose-deploy-design.md](../../research/07-compose-deploy-design.md)：Compose 拓扑、Secrets、healthcheck 和 `deploy.sh`。

报告之间有版本冲突时，以本 README 的“统一决策”和 Step 00 的实施日复核结果为准；不能把调研报告中的未来候选直接写入生产配置。

## 2. 不可变部署基线

以下两项是用户明确给出的硬约束，覆盖调研报告中关于其他宿主或 Python 版本的建议：

- 生产宿主：**Ubuntu 24.04 LTS**。
- backend、JudgeServer 及其 Python 构建链：**Python 3.12.x，`>=3.12,<3.13`**。
- Judge 容器启动保持 root；Judger 自行降权到固定 UID/GID 并加载 Seccomp。
- server 不得使用 `privileged`、Docker socket、`SYS_ADMIN`。
- 只有 frontend 可以发布宿主端口；backend/server 只在 Compose 内网通信。

宿主 OS 与容器基础 OS 是不同层次：计划允许经过验证的 Debian slim/Bookworm/Trixie 容器，但不能把它写成宿主要求。所有容器基础镜像、系统包和 Python/Node patch 在 Step 00 重新核实并锁 digest。

## 3. 调研冲突的统一决策

| 议题 | 本计划决策 | 处理方式 |
|---|---|---|
| Python | 3.12.x | 不执行 3.12→3.13/3.14；在 Step 00 锁定 micro 与 digest |
| Node | 24.x LTS，报告候选 24.19.0 | Node 26 不进入本轮生产基线 |
| pnpm | 11.x，候选 11.22.0 | 报告另有 11.21.0；Step 00 以官方稳定版和 lock 重建结果定案，禁止 pnpm 12 RC |
| Vite | Vue 2 桥接 7.3.6，最终 8.2.1 | Vite 8 单独发布，不和 Vue 3 首次上线绑定 |
| Django | 4.2.30 仅兼容检查点，5.2.17 最终目标 | 4.2 不作为长期生产落点 |
| DRF | 3.17.2 作为 bridge，3.18.0 后置 | 3.18 不和 Django 5.2 首发同批 |
| uv | 0.12.5 候选 | Step 00 重核并提交 `uv.lock` |
| PostgreSQL | **18.6 主方案，17.11 备用** | 报告对 17/18 有分歧；先用 PG18 fresh restore 演练，若出现 blocker 才切 PG17 |
| Redis | 6.2.23 → 7.4.10 → 8.2.8 | 每一跳独立窗口；不切 Valkey，不直接复用旧 data directory |
| Judge 工具链 | Python 3.12、GCC 14.2、JDK 21、Go 1.26.x、Node 24、libseccomp 2.6.x | 每种语言单独升级和回归；amd64 先生产，arm64 先 experimental |

所有“候选版本”必须在实施时通过官方发布页、包元数据、兼容矩阵和实际构建重新确认。没有 digest 的版本不能进入生产 Compose。

## 4. 最终目标拓扑

```text
Internet :HTTP/:HTTPS
       |
       v
frontend (Nginx; 唯一宿主端口)
  |-- /、/admin/       -> 两个静态 SPA
  |-- /api              -> backend-api:8000
  `-- /public/          -> backend public 只读挂载

edge network: frontend <-> backend-api
core network: backend-api, backend-worker, judge-server, postgres, redis

backend-api    <- backend 镜像，以 api 角色运行
backend-worker  <- backend 镜像，以 worker 角色运行
backend-migrate/bootstrap <- backend 镜像，一次性角色
judge-server   <- server 镜像；内部监听 8080，不发布宿主
postgres       <- 独立数据服务
redis          <- 独立数据服务；DB1 与 DB4 职责不变
```

三项业务镜像是 `frontend`、`backend`、`server`。backend API、Worker、迁移和初始化复用同一个 backend 镜像，不把 API 与 Worker 塞回 Supervisor。`judge-toolchain` 是可发布的重型基础镜像，不是第四个长期业务服务。

## 5. 必须保持的合同

1. 浏览器继续同源访问 `/api`，不引入跨域 Cookie。
2. 保持 Django Session、`csrftoken`、`X-CSRFToken`、Referer/Origin 语义。
3. 保持 `/admin/` history fallback、`/admin` → `/admin/`、`/public/`。
4. 保持 API `{"error": ..., "data": ...}`、分页参数和结果键。
5. 不改 Django app label、`db_table`、已应用 migration 名称、依赖图或 `DEFAULT_AUTO_FIELD`。
6. Redis DB1 继续承载 Session/cache/`waiting_queue`；DB4 继续承载 Dramatiq broker/result。
7. 保持 Judge `/judge`、`/compile_spj`、`/ping`、heartbeat、Token SHA-256 header、Judge 的 `err/data` 包装和结果字段。
8. `/test_case` 对 JudgeServer 只读；UID/GID、资源限制和 Seccomp 不得弱化。
9. 密码、Django Secret、Judge Token、管理员密码、证书和运行数据不进入 Git、镜像层、命令行或普通日志。

## 6. 按 Step 执行规则

- 一次只实施一个 Step；完成该 Step 的验收、提交和记录后才进入下一个。
- 每个 Step 只改变一个主要风险轴；不得把数据库 major、框架 major、工具链 major 合并。
- 每个 Step 文档不超过 300 行；文档中的命令是计划命令，不代表已执行。
- Step 失败时停在当前提交，保留日志、镜像 digest、数据快照和测试结果。
- 任何数据写入或消息格式变化，都必须先扩展兼容窗口并重新评审回滚。
- `docs/research/` 是调研证据，不是自动批准版本；实现时如果官方状态变化，先更新 Step 00 的版本锁。

## 7. Step 索引与依赖

| Step | 文档 | 依赖 | 交付物 |
|---:|---|---|---|
| 00 | [决策门与版本锁](00-decision-gates.md) | 无 | 版本锁、硬约束、停止门 |
| 01 | [行为合同与特征测试](01-contract-characterization.md) | 00 | API/Session/CSRF/Judge golden |
| 02 | [现状盘点与构建基线](02-inventory-build-baseline.md) | 00 | inventory、构建/数据指标 |
| 03 | [Ubuntu 24.04 运行前置](03-ubuntu24-runtime-preflight.md) | 00 | 宿主 preflight、目录与工具链门 |
| 04 | [Frontend pnpm 锁定](04-frontend-pnpm-lock.md) | 01,02 | pnpm lock、隐式依赖清单 |
| 05 | [Vite 7 双入口桥接](05-frontend-vite-bridge.md) | 04 | Vue2 + Vite 双入口 |
| 06 | [Frontend 桥接镜像与 Nginx](06-frontend-bridge-image.md) | 03,05 | 独立 frontend 镜像、同源网关 |
| 07 | [Vue 3 核心迁移](07-frontend-vue3-core.md) | 06 | Vue3、Router、i18n、Vuex4 |
| 08 | [Frontend UI 组件迁移](08-frontend-ui-migration.md) | 07 | Element Plus/UI POC 与页面回归 |
| 09 | [Frontend 编辑器迁移](09-frontend-editor-migration.md) | 08 | CodeMirror/Tiptap adapter 与 corpus |
| 10 | [Frontend 最终平台清理](10-frontend-final-cleanup.md) | 09 | Vite8、Pinia、旧链路删除 |
| 11 | [Backend uv 元数据](11-backend-uv-metadata.md) | 01,02 | pyproject、首版 lock |
| 12 | [Backend uv 安装器与镜像](12-backend-uv-image.md) | 03,11 | locked 安装与角色运行镜像 |
| 13 | [Backend Python 基础镜像](13-backend-base-image.md) | 12 | Python3.12 slim/兼容性证据 |
| 14 | [Django 兼容债务清理](14-backend-compat-prep.md) | 13 | URL/JSONField/legacy 门 |
| 15 | [Django 4.2 检查点](15-backend-django42.md) | 14,22 | 4.2 deprecation 清零 |
| 16 | [psycopg3 独立迁移](16-backend-psycopg3.md) | 15,22 | Psycopg3 driver release |
| 17 | [Django 5.2 落地](17-backend-django52.md) | 16,20,22 | Django5.2 生产候选 |
| 18 | [Worker 与 Redis 客户端](18-backend-worker-ecosystem.md) | 17,20 | django-redis/Dramatiq/DRF 分批升级 |
| 19 | [数据盘点与备份](19-data-inventory-backup.md) | 01,02,03 | PG/Redis/runtime 可恢复备份 |
| 20 | [Redis 逐级迁移](20-redis-ladder.md) | 19 | Redis 6.2/7.4/8.2 |
| 21 | [PostgreSQL 恢复演练](21-postgres-rehearsal.md) | 19 | PG18 fresh restore 证据 |
| 22 | [PostgreSQL 生产切换](22-postgres-cutover.md) | 21 | PG18（或批准的 PG17）切换 |
| 23 | [Server 构建边界](23-server-build-boundary.md) | 02,03 | 根 context、toolchain stages |
| 24 | [Server 工具链迁移](24-server-toolchain.md) | 23 | Python3.12/GCC/JDK/Go/Node |
| 25 | [Server 协议与健康](25-server-protocol-health.md) | 23,24 | liveness/heartbeat/协议回归 |
| 26 | [Server 安全与多架构](26-server-hardening-multiarc.md) | 24,25 | hardening、amd64 gate、arm64实验 |
| 27 | [BuildKit、Bake 与供应链](27-buildkit-bake-supply-chain.md) | 06,12,26 | cache、digest、SBOM、provenance |
| 28 | [Compose 拓扑与 Secrets](28-compose-topology-secrets.md) | 06,12,25,26,27 | 生产 Compose、env、网络、卷 |
| 29 | [deploy.sh 与全栈 Smoke](29-deploy-script-smoke.md) | 18,20,22,27,28 | 幂等部署入口与验收 |
| 30 | [发布、切换与回滚演练](30-release-cutover-rollback.md) | 10,18,22,26,29 | 最终发布和回滚证据 |

Frontend Step 04–10、backend Step 11–18、数据 Step 19–22 和 server Step 23–26 可分别在合同基线后推进；Step 17 必须等待目标 PG/Redis 稳定，Step 29 之前不得宣称“一键部署”完成。

## 8. 全局命令与发布规则

所有命令默认在仓库根目录执行：

```bash
git status --short --branch
git diff --check

docker compose config --quiet

git diff --name-only <previous-step-tag>..HEAD
```

正式镜像使用 `image@sha256:<digest>`，同时保留不可覆盖的 Git SHA tag。生产部署记录 frontend/backend/server/toolchain 四类 digest、源码 SHA、配置版本和时间；禁止依赖 `latest`、`main` 或可变 `stable` 回滚。

数据库迁移、Redis ladder 和 Judge toolchain 各自拥有独立发布窗口。`docker compose down -v`、`volume prune`、删除 runtime root、自动生成/覆盖 Secret、自动 reset 管理员和自动 DROP 数据库均为禁止动作。

## 9. 全局完成标准

- Ubuntu 24.04 宿主上可从锁文件和 digest 重建三业务镜像。
- frontend 两个 SPA 的路由、API、Session/CSRF、上传和 `/public` 通过浏览器回归。
- backend 在 Python 3.12、Django 5.2、Psycopg3、Redis8/Dramatiq 目标组合下通过全量测试。
- PG 与 Redis 有真实 snapshot 的 restore 演练记录，DB1/DB4 和 waiting_queue 可核账。
- Judge 协议字段、结果码、Token、UID/GID、资源限制、`/test_case:ro` 和 Seccomp corpus 通过。
- Compose 只让 frontend 发布宿主端口；`./deploy.sh` 对首次部署、普通升级、配置变更、镜像回滚均可验证。
- 每个 Step 有独立提交、验收记录和回滚说明；旧版本仍可在兼容窗口内恢复。

下一次开始实施时只执行 [Step 00](00-decision-gates.md)，不要直接跳到代码迁移。
