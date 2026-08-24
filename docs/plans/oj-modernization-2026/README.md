# xju-OJ 2026 现代化迁移总计划

> 当前状态：**Phase 0 已完成，下一次从 Phase 1 开始**。
>
> 本 README 是唯一执行入口。`00-*.md` 至 `30-*.md` 保留为技术检查清单；执行顺序、失败分类、提交和跨环境规则以本 README 与 `phases/` 为准。
>
> 首要目标不是逐条“打卡”，而是尽快让升级版先在本机 WSL、再在 `huawei1` 端到端运行；生产数据和生产 Secret 只在最后一个 Phase 启用。

## 1. 新对话启动方式

下一次对话直接使用：

```text
严格按 docs/plans/oj-modernization-2026/README.md 的 Phase 模型执行，
从当前未完成的 Phase 1 开始。先在 WSL 跑通，再在 huawei1 跑同一组 immutable image digest。
普通构建、依赖、代理、测试和环境问题按 soft failure 在 Phase 内修复或记录后继续独立 lane；
只有 README 定义的 hard stop 才停止。每个 Phase 验收后更新 execution-log、检查 diff、提交并 push main。
```

开始时只需核验：

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

然后读取当前 Phase 文档；不必重新遍历已完成 Step 00–03。

## 2. 不可变部署基线

- 生产宿主：受支持 Ubuntu `>=22.04`。
- backend、JudgeServer 和 Python 构建链：Python `>=3.10,<3.11`。
- Node 24 LTS、pnpm 11；最终 frontend 为 Vue 3/Vite 8/Pinia。
- 最终 backend 为 Django 5.2/Psycopg 3；具体 patch 以版本锁为准。
- PostgreSQL 18 主方案、17 备用；Redis 4→6.2→7.4→8.2。
- Judge 容器可由 root 启动，但 Judger 必须降权并加载 Seccomp。
- server 禁止 `privileged`、Docker socket、`SYS_ADMIN`；`/test_case` 只读。
- 只有 frontend 可发布宿主端口；backend/server/PG/Redis 仅在 Compose 内网。
- 正式镜像按 digest 部署，不使用 `latest`、`main` 或可变 `stable` 回滚。

已核定版本和 digest 见 `docs/contracts/modernization-version-lock.md`。候选 patch 不可用是 soft failure：在相同 feature line 或已批准 fallback 中重新锁定；不得静默改变 Python 3.10 等硬约束。

## 3. 最终目标拓扑

```text
Internet
   |
frontend (Nginx，唯一宿主端口)
  |-- /、/admin/  -> 两个 SPA
  |-- /api/       -> backend-api:8000
  `-- /public/    -> backend public 只读挂载

edge: frontend <-> backend-api
core: backend-api, backend-worker, judge-server, postgres, redis
```

发布镜像：`frontend`、`backend`、`server`、`judge-toolchain`。backend API、Worker、migration 和 bootstrap 复用同一个 backend 镜像，通过角色区分。

## 4. 必须保持的合同

1. 浏览器继续同源访问 `/api`；Session、Cookie、CSRF、Origin/Referer 语义不变。
2. 保持 `/admin/`、`/admin`→`/admin/`、deep link 和 `/public/`。
3. 保持 API `{"error": ..., "data": ...}`、分页参数和结果键。
4. 不改 app label、`db_table`、已应用 migration 名称/依赖图、`DEFAULT_AUTO_FIELD`。
5. Redis DB1 保持 Session/cache/`waiting_queue`；DB4 保持 Dramatiq broker/result。
6. 保持 Judge `/ping`、`/judge`、`/compile_spj`、heartbeat、Token SHA-256、`err/data` 和结果字段。
7. UID/GID、资源限制、Seccomp、只读 test_case 和 workspace 隔离不得弱化。
8. Secret、密码、Token、证书私钥和运行数据不得进入 Git、镜像层、命令行或普通日志。

合同 golden 与特征测试位于 `docs/contracts/`、`backend/tests/contracts/`、`frontend/tests/e2e/` 和 `server/judge-server/tests/`。

## 5. Phase 总览

| Phase | 详细文档 | Step 清单 | 主要结果 | 环境 |
|---:|---|---|---|---|
| 0 | [基线与前置](phases/00-foundation.md) | 00–03 | 版本锁、合同、盘点、宿主预检 | 已完成 |
| 1 | [组件桥接与可重复构建](phases/01-component-bridge.md) | 04–06、11–14、23–27 | 三业务镜像和 toolchain 可独立构建 | WSL |
| 2 | [WSL 目标数据与全栈](phases/02-wsl-full-stack.md) | 19–21（演练）、28–29 | 隔离 PG/Redis、Compose、deploy.sh 全栈 smoke | WSL |
| 3 | [最终应用升级](phases/03-final-application.md) | 07–10、15–18；重跑 27/29 | Vue3/Vite8、Django5.2/Psycopg3/Worker 最终组合 | WSL |
| 4 | [huawei1 隔离演练](phases/04-huawei-rehearsal.md) | 重跑 03、19–21、26–29 的宿主部分 | 同一 digest 在 Ubuntu 主机完整运行 | huawei1 隔离项目 |
| 5 | [生产数据与发布](phases/05-production-release.md) | 19 最终、20 生产、22、30 | 数据切换、应用发布、回滚验收 | huawei1 生产窗口 |

Phase 1 的 frontend/backend/server lane 可并行；Phase 3 的 frontend/backend lane 可并行。Phase 2 只依赖 Phase 1 的可运行镜像，Phase 5 才依赖真实生产 Secret 和真实数据切换批准。

## 6. Phase 执行规则

### 6.1 执行单位

- **Phase 是推进、验收、日志和必需提交的单位**；Step 是 Phase 内部技术清单，不再要求一项小检查失败就停止整个计划。
- 独立 lane 互不阻塞：例如 frontend 构建失败时，backend/server lane 继续。
- 同一 lane 保持必要顺序；数据库 major、框架 major、队列 major、Judge toolchain major 仍保留独立 checkpoint 和回滚点。
- Phase 未通过最终验收时不得标记完成，但可以保留未完成项并继续不依赖它的工作。

### 6.2 Soft failure：记录、修复、重试或降级，不终止计划

通常包括：

- 编译、依赖安装、lock、镜像构建、registry/cache、代理/DNS/镜像源问题。
- 单测、E2E、浏览器、healthcheck、性能、bundle/image size 未达标。
- WSL 的文件权限、inotify、cgroup、端口、网络或 Docker 差异。
- 候选 patch 不存在或包组合不兼容；PG18 隔离演练失败时评估已批准 PG17 fallback。
- arm64、SBOM、provenance、scanner 暂不可用，但相应 artifact 不得晋级生产。
- 缺少真实数据 clone 或生产 Secret：Phase 1–4 使用 fixture/脱敏 clone 和测试 Secret 继续，缺口登记为 Phase 5 release gate。

处理方式：保留错误和 artifact，定位根因后重试。相同假设连续三次修复失败时，停止盲试，选择已记录 fallback、把该 lane 标为 deferred，或提出一个诊断问题；不要阻塞其他 lane，也不能把失败伪装成通过。

### 6.3 Hard stop：立即停止受影响 Phase/发布

只有四类：

1. **破坏性数据风险**：无可恢复备份却要执行 major/cutover；覆盖唯一旧卷；要求 `down -v`、volume prune、`FLUSHDB`、自动 DROP、删除 runtime；queue/ACK/producer 无法核账。
2. **兼容合同破坏**：API/Session/CSRF/路由、DB identity/migration、Redis DB1/DB4/消息、Judge 协议或历史 editor 数据发生未批准语义变化。
3. **安全边界破坏**：Secret 泄漏；生产 Secret 被自动生成/覆盖；Judge 需要 privileged/Docker socket/SYS_ADMIN/公开 8080/可写 test_case；非 frontend 服务必须发布宿主端口；正式 digest 或 Critical CVE 无法确认。
4. **无法回滚**：新 schema/data/message 已写入且 N-1 不可读，又无 PITR/snapshot/forward-fix；旧 image/Compose/volume/snapshot 已丢失；恢复演练证明回滚路径不可用。

Hard stop 只停止受影响 lane/Phase；先保留现场和旧数据，不连续执行破坏性“修复”。

## 7. 环境作用域与 Secret 规则

- WSL 和 huawei1 隔离演练可使用专用的、Git ignored、可销毁测试 Secret；可以由测试 helper 生成，但 **deploy.sh 不生成 Secret**。
- Phase 1–4 不要求生产 Secret，不允许因 `/srv/xju-oj/secrets` 为空阻塞开发和隔离 smoke。
- Phase 2/3 的 PostgreSQL 前置是 Step 21 的 fresh target/fixture restore，不是 Step 22 生产切换。
- Phase 2/3 的 Redis 前置是隔离 Redis ladder/目标实例，不是生产 Redis cutover。
- Phase 4 必须使用与 WSL 相同的 image digest；不得在 huawei1 用 mutable tag 临时重建另一套 artifact。
- 生产 Secret、真实 final backup、queue drain、GO/NO-GO 和维护窗口只在 Phase 5 成为 hard gate。

## 8. 提交、日志与回滚单位

- 每个 Phase 至少一次独立验收提交，并立即 `git push origin main`。
- Phase 内允许按 frontend/backend/server/data checkpoint 提交；不再强制每个 Step 都单独 push。
- 数据 major、Django/Psycopg/Worker major、Judge toolchain/security 必须保留可识别 checkpoint；Phase 5 的 Redis、PostgreSQL、应用发布不能合并为一个回滚单元。
- 每次 Phase promotion 更新 [execution-log.md](execution-log.md)，记录实际命令、测试、image digest、数据证据、soft failures、deferred 项和回滚点。
- 失败日志不能包含 Secret；旧 image、Compose、volume、runtime snapshot 在观察窗口内不删除。

建议提交格式：

```text
phase 1: build reproducible component bridge
phase 2: run isolated WSL full stack
phase 3: complete application modernization
phase 4: validate immutable stack on huawei1
phase 5: complete production cutover and rollback acceptance
```

## 9. Step 技术索引

原 Step 文档仍负责文件范围、具体测试和回滚细节：

- Frontend：[04](04-frontend-pnpm-lock.md)–[10](10-frontend-final-cleanup.md)
- Backend：[11](11-backend-uv-metadata.md)–[18](18-backend-worker-ecosystem.md)
- Data：[19](19-data-inventory-backup.md)–[22](22-postgres-cutover.md)
- Server：[23](23-server-build-boundary.md)–[26](26-server-hardening-multiarc.md)
- Delivery：[27](27-buildkit-bake-supply-chain.md)–[30](30-release-cutover-rollback.md)

若 Step 文档的“进入条件/停止条件”与 Phase 模型冲突：

- 执行顺序和环境作用域以 Phase 文档为准；
- 本 README 的 hard stop、不可变合同和数据安全边界不可被覆盖；
- Step 22 永远只代表生产 PostgreSQL cutover，不是本地开发前置；
- Step 20 在 Phase 2 做隔离 rehearsal，在 Phase 5 才做生产 cutover。

## 10. 全局完成标准

- WSL 能从 clean checkout/lock 构建并启动最终全栈。
- 同一 source SHA 和 image digest 能在 huawei1 隔离项目通过完整 smoke。
- frontend 双入口、API、Session/CSRF、public、上传、编辑器与浏览器合同通过。
- backend 在 Python3.10/Django5.2/Psycopg3/目标 Redis/Worker 组合通过。
- PG/Redis 有真实 restore、manifest、queue 核账和生产切换证据。
- Judge 协议、语言 corpus、UID/GID、Seccomp、资源限制、只读 test_case、网络隔离通过。
- Compose 仅 frontend 发布宿主端口；deploy.sh 首装、升级、配置变更、失败保留现场和 image rollback 通过。
- Phase 5 完成前只能称为“升级版已在 WSL/huawei1 跑通”，不能称为生产迁移完成。

下一次执行从 [Phase 1](phases/01-component-bridge.md) 开始。
