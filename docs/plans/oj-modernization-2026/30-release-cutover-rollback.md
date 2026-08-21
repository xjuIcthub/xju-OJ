# Step 30：发布、切换与回滚演练

## 目标

在 Ubuntu 24.04 staging 和批准的生产窗口中验证完整发布链、N/N-1 兼容、镜像回滚、数据回滚边界和最终验收；这是计划的收口 Step。

## 进入条件

- Step 10 frontend、Step 18 backend、Step 20 Redis、Step 22 PostgreSQL、Step 26 server、Step 29 deploy 全部有独立验收记录。
- 所有镜像有 Git SHA、toolchain tag、digest、SBOM/provenance。
- PG/Redis 旧卷、备份、runtime/public/test_case、Secret 和旧 Compose 仍可用。
- 生产变更窗口、观察窗口、回滚负责人已确定。

## 四类演练

### 首次安装

- 空 runtime + 测试 Secret。
- build 或 pull 三业务镜像。
- PG/Redis healthy → bootstrap → migrate → create-once 初始化 → 全栈 smoke。
- 记录耗时和所有镜像 digest。

### 普通业务升级

- 保留 current release。
- 拉取/构建新 digest。
- 先验证 schema/消息兼容，再执行允许的 migration。
- `up --wait`、完整 smoke、写入 current/previous。
- 失败保留旧 release 和数据，不自动清理。

### 仅配置变更

- 修改域名/宿主 HTTP 端口/非秘密 runtime config。
- `compose config` + recreate 必要容器 + smoke。
- 证明不触发 frontend build，不改变 Vite bundle/API 基址。

### 镜像回滚

- 把 frontend/backend/server/toolchain 指向 previous digest。
- `docker compose up -d --remove-orphans --wait`。
- 验证 API/Session/CSRF/Worker/Judge/静态资源。
- 如果新版本已执行不可逆 schema 或写入旧代码不识别的数据，禁止“只换镜像”假装回滚。

## 最终验收矩阵

### Frontend

- 双入口、所有 deep link、admin redirect、API、Session/CSRF、public、上传、编辑器 corpus、图表、比赛/排名。
- Chromium/Firefox/WebKit（按 SLA）、N/N-1 assets、cache/runtime-config。

### Backend/data

- Python3.12、Django5.2、Psycopg3、DRF目标版本、Redis8.2、Dramatiq目标版本。
- 全量测试、fresh DB migration、生产克隆校验、API/admin/public、worker/retry/result。
- PG row/schema/JSONB/sequence/index/ACL/timezone；Redis DB1/DB4/waiting_queue manifest。

### Server

- `/ping`、`/judge`、`/compile_spj`、heartbeat、Token、结果字段/码。
- 六语言正向、资源限制、攻击负向、UID/GID、Seccomp、rootfs、`/test_case:ro`、网络隔离。
- amd64 production；arm64 状态与证据明确。

### Supply chain/deploy

- clean/warm build、cache 命中、digest、SBOM、provenance、CVE 门禁。
- 只有 frontend 宿主端口；Compose `config --quiet`；deploy.sh 幂等、失败非零、失败不删数据。

## 硬停止条件

- API/Session/CSRF、表名/app label/migration、Redis DB1/DB4、Judge 协议或安全边界改变。
- PG/Redis restore、queue drain、备份或回滚演练失败。
- 生产运行 digest 无法确认，或镜像有未批准 Critical CVE。
- server 需要 privileged/SYS_ADMIN/公开8080/可写 test_case。
- deploy.sh 生成/打印/覆盖 Secret 或自动删除卷/数据库。

## 发布原则

- 每个 Step 一个提交/标签；发布单记录 commit、镜像 digest、配置 hash、数据库状态、Redis manifest、回滚点。
- 观察窗口内不删除旧 PG/Redis 卷、旧镜像和旧 runtime。
- 数据 major、框架 major、工具链 major 不能在一个回滚单元内合并。
- 完成后把 `docs/plans/oj-modernization-2026/execution-log.md` 更新为实际证据，而不是把计划文本当完成事实。

## 回滚

- 无数据/schema/message 变化：切旧 immutable image/Compose manifest。
- 已有数据写入：先停写并核账，再选择 PITR、快照恢复或 forward-fix。
- PG18 不能用 PG10 data directory 启动；新 Redis 消费后不能直接挂回旧队列。
- 回滚失败时保留现场，禁止连续盲目尝试。

## 完成标志

提交格式建议：

```text
release: complete Ubuntu 24.04 modernization acceptance
```

最终完成不是“服务能启动”，而是所有合同、数据恢复、判题安全、构建可复现和回滚证据都齐全。
