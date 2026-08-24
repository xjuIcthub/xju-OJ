# Phase 3：WSL 最终应用升级

## 目标

在 Phase 2 已运行的目标 PG/Redis/Compose 上并行完成 frontend 与 backend 最终现代化，然后重建并重新执行全栈 smoke。生产 PostgreSQL cutover 不是本 Phase 前置。

## Step 映射

| Lane | Step | 顺序 |
|---|---|---|
| Frontend | 07–10 | Vue3 core → UI → editor → Vite8/Pinia/旧链清理 |
| Backend | 15–18 | Django4.2 → Psycopg3 → Django5.2 → Redis/Worker/DRF 分批 |
| Integration | 重跑 27、29 | 每个关键 checkpoint 重建；Phase 末完整 smoke |

Step 14 已在 Phase 1 完成。Frontend/backend lane 可并行；各自内部顺序不可倒置。

## 环境作用域修正

- Step 15/16/17 在 WSL 只要求 Step21 的 fresh target/fixture PG 通过，不要求 Step22 生产切换。
- Step 17/18 只要求隔离目标 Redis 和 DB1/DB4 manifest，不要求生产 Redis 已切换。
- Step 20/22 的生产动作留在 Phase 5。
- historical migration、schema identity 和兼容合同仍是 hard gate。

## 内部 checkpoints

### Frontend

1. Vue3/Router/i18n/store 核心启动。
2. Element/UI 页面迁移。
3. editor adapter 与历史 HTML/upload corpus。
4. Vite8、Pinia 和旧链清理。

保留 Vue2 bridge immutable image 到 Phase 5 观察窗口；不因 Step06/10 提前失去 N-1。

### Backend

1. Django4.2 schema-neutral checkpoint。
2. Psycopg3 独立 checkpoint。
3. Django5.2 schema-neutral checkpoint。
4. django-redis/redis-py、Dramatiq、django-dramatiq、DRF 分批 checkpoint。

虽然同属一个 Phase，每个 major/checkpoint 仍单独 image/commit/test，避免把框架、driver、queue 和 API 变成一个回滚单元。

## Phase 验收

- WSL fresh/fixture 全栈运行最终 frontend/backend/server/data 组合。
- Vue3、最终 UI/editor、Vite8、Pinia 双入口和 browser corpus 通过。
- Python3.10、Django5.2、Psycopg3、目标 DRF/Redis/Worker 组合通过。
- `makemigrations --check --dry-run` 无意外 migration；fresh DB replay 与历史 JSONField loader 通过。
- API/Session/CSRF/admin/public/upload、worker queue/retry/result、Judge dispatch/protocol 全部通过。
- frontend/backend/server/toolchain 重新生成 immutable digest；deploy.sh 升级、config-only 和 image rollback 通过。
- N-1 只在没有不兼容 schema/data/message 写入时直接回滚；否则明确 forward-fix/restore 边界。

## Soft failure 处理

- Vue 插件、UI、editor、Django third-party 或 driver 不兼容：在 adapter/owning layer 修复并继续另一 lane。
- browser/performance/bundle/image regression：记录并修复，不停止 backend/server 工作。
- 某个生态 major 暂不兼容：保持已通过 bridge checkpoint，标 deferred；Phase 最终组合未达标前不晋级 huawei release candidate。
- 测试失败不伪装通过；相同假设三次失败后选 fallback 或提出一个诊断问题。

## Hard stop

- 需要修改已应用 migration、app label、db_table 或历史数据才能启动。
- API/Session/CSRF、editor 历史内容、Redis message/ACK/retry/result 或 Judge contract 未批准改变。
- 新旧 Worker 同时有消费权，或需要清空 DB1/DB4 才能继续。
- 新写入已使 N-1 不可读，且无 restore/PITR/forward-fix。

## 回滚

按 checkpoint 回退，不跨越已产生不兼容写入的边界。保留 Phase 2 bridge image、目标 data fixture、current/previous metadata 和所有测试证据。

## 完成标志

最终升级版在 WSL 完整跑通并产生 release-candidate digest。随后进入 [Phase 4](04-huawei-rehearsal.md)。
