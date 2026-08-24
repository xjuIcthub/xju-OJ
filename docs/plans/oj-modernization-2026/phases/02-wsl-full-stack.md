# Phase 2：WSL 目标数据与全栈运行

## 目标

用 Phase 1 镜像在 WSL 建立隔离 PG/Redis、最终 Compose 拓扑和 `deploy.sh`，尽快跑通首个端到端升级栈。此 Phase 是开发/演练环境，不触碰生产卷和生产 Secret。

## Step 映射

- Step 19：实现 inventory/backup/manifest 工具；先对 fixture 或脱敏 clone 运行。
- Step 20：在隔离 volume 演练 Redis 4→6.2→7.4→8.2；生产执行留到 Phase 5。
- Step 21：在 fresh PG18（阻塞时用已批准 PG17）执行 restore/校验；生产 cutover 不在此 Phase。
- Step 28：完成三镜像、多角色 backend、网络、卷、Secret-file Compose。
- Step 29：完成 deploy.sh、first-install、upgrade/config/pull/build 和全栈 smoke。

## 快速路径与发布路径

### 快速路径（必须先跑通）

- 使用可重复 seed/fixture、空 fresh DB 或可用脱敏 clone。
- 测试 Secret 放在 Git ignored 的临时目录，可由专用 test helper 创建；deploy.sh 只检查并消费，不生成。
- 目标是先证明 topology、migration、API、worker、Judge 和浏览器链路。

### 发布路径（可在本 Phase 后补证据）

- 真实 protected clone 的 PG/Redis/runtime backup 与 restore。
- 两次 fresh restore、容量和恢复时长。
- waiting_queue、DB4 message/ACK/result 与业务对象核账。

真实 clone 暂不可用时，把发布路径标为 `release-gate pending`，继续 Phase 3；不得伪造数据恢复完成。

## 执行顺序

1. 建立隔离 `COMPOSE_PROJECT_NAME`、runtime、volume、backup 和 test-secret 根。
2. 先启动目标 PG/Redis，运行 fresh/fixture restore 与 manifest。
3. 完成 Compose 网络、卷、health 和 `_FILE` 配置。
4. 实现 deploy.sh dry-run、build/pull 和首次安装。
5. 启动 frontend、backend-api、backend-worker、judge-server。
6. 运行完整 smoke；失败保留容器、日志和 metadata，不自动清理。
7. 验证 config-only、普通升级和 image rollback 的无数据版本。

## Phase 验收

- 只有 frontend 绑定 WSL host port；backend 8000、Judge 8080、PG5432、Redis6379 不对宿主发布。
- `/`、`/admin/`、deep link、`/api/website/`、Session login/logout、合法/非法 CSRF、`/public/` 通过。
- backend migration/bootstrap 幂等；worker enqueue→result、retry/stop/restart 通过。
- Redis DB1/DB4 namespace 与职责不变；fixture ladder 每一跳可重启、比较 manifest。
- Judge `/ping`、heartbeat、至少一组 `/judge` 和 `/compile_spj` 通过。
- deploy.sh 首装、build、pull、config-only、失败非零、current/previous metadata 通过。
- 测试 Secret、fixture、dump 和 runtime 不进入 Git、image 或普通日志。

## Soft failure 处理

- 本地端口冲突：改 WSL rehearsal bind，不改内部协议。
- Docker/WSL ownership、health timing、DNS、proxy、registry 问题：修复后重试。
- PG18 restore 不兼容：保留证据并评估版本锁中的 PG17 fallback。
- 真实 clone/production Secret 缺失：登记 Phase5 gate，不阻塞 fixture 全栈。
- 单个 smoke 失败：修 owning service；其他 smoke 和 lane 继续收集证据。

## Hard stop

- 测试流程会覆盖现有数据、复用唯一旧 volume、执行 `down -v`/prune/FLUSHDB/DROP。
- Compose 需要把非 frontend 服务暴露到宿主。
- deploy.sh 生成、打印或覆盖 Secret，或失败时删除数据。
- migration/schema、DB1/DB4、queue、Session/CSRF 或 Judge 合同发生未批准变化。

## 回滚

删除的只能是本 Phase 明确标记的隔离 project/fixture volume；不得使用全局 prune。保留 Phase 1 images、logs、metadata 和任何真实 clone backup。

## 完成标志

升级 bridge stack 在 WSL 端到端可运行。随后进入 [Phase 3](03-final-application.md)，不等待生产 Step22。
