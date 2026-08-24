# Phase 5：生产数据切换与最终发布

## 目标

在 Phase 4 隔离演练通过后，使用真实生产 Secret、final backup、维护窗口和 GO/NO-GO，把数据平台与应用分开切换，并完成 Step30 回滚验收。

这是唯一把生产 Secret 缺失、真实 restore、queue drain 和生产端口视为前置 hard gate 的 Phase。

## Step 映射

1. Step 19 最终 inventory、PG/Redis/runtime backup、hash、restore 证据。
2. Step 20 生产 Redis ladder；每一代独立窗口/volume/checkpoint。
3. Step 22 PostgreSQL fresh restore cutover；不同时升级应用 major。
4. 观察数据平台稳定。
5. Step 30 使用 Phase3/4 已接受的应用 digest 执行 release、smoke 和 image rollback。

Step 27–29 的 artifact 在本 Phase 只消费，不临时重构。

## 必需前置

- 外部系统已提供生产 Secret 文件；路径、owner、`0600`、非空通过，不打印内容。
- PG、Redis DB1/DB4、runtime/public/test_case 有 final backup、hash 和独立 restore 记录。
- old/new/backup/restore 空间可并存；旧 PG/Redis volume、旧 images、旧 Compose 可用。
- producer 可冻结；`waiting_queue=0`、PG PENDING/JUDGING=0、DB4 ready/delayed/ACK 可核账。
- 明确维护窗口、观察窗口、GO/NO-GO、target 写入后回滚决策人。
- Phase4 的同一 digest/manifest 已在 huawei1 隔离项目通过。

## 发布窗口拆分

### Window A：Redis

- 4→6.2→7.4→8.2 每一跳新 volume、snapshot、manifest、应用 smoke。
- 只有一套 Worker 消费权；新版本消费后不能直接挂回旧 queue volume。

### Window B：PostgreSQL

- PG10 final dump→fresh PG18（批准时 PG17）restore→read-only validation→GO 后开放写入。
- target 写入前可回旧 PG10；写入后必须停写并选择 reconciliation/PITR/forward-fix。

### Window C：应用

- 数据平台观察通过后，部署 Phase3/4 immutable frontend/backend/server/toolchain digest。
- 执行 migration gate、`up --wait`、完整 smoke、current/previous metadata。
- 无不兼容写入时演练 image rollback；有不兼容写入时按数据回滚决策，不假装只换 image。

## 最终验收

- frontend 双入口、浏览器、API、Session/CSRF、public/upload/editor 全通过。
- Python3.10/Django5.2/Psycopg3/Worker、PG/Redis manifest、fresh migration 全通过。
- Judge protocol、六语言、资源限制、攻击负向、UID/GID、Seccomp、只读 test_case、网络隔离通过。
- 只有 frontend 发布生产宿主端口。
- deploy.sh 首装演练、普通升级、config-only、失败保留现场和 rollback 通过。
- 发布记录包含 source SHA、四类 image digest、config hash、PG state、Redis manifest、时间和回滚点。
- 观察窗口内旧 volume/image/runtime/backup 不删除。

## Hard stop

README 定义的四类 hard stop 在本 Phase 全部严格执行，尤其：

- final backup/restore/hash/queue 核账任一失败；
- producer/旧 Worker 仍活动；
- target 未验证就开放写入；
- Secret 泄漏或 deploy.sh 生成/覆盖生产 Secret；
- 需要删除旧卷、修改历史 migration、弱化 Judge 安全边界或暴露内部端口；
- 旧 rollback artifact 已不存在。

普通网络、registry、构建或 smoke bug 可在窗口前修复；进入生产写窗口后，任何无法解释的错误默认 NO-GO/停写，不盲目继续。

## 提交与记录

Redis、PostgreSQL、应用 release 分别记录，不合并为一个回滚单元。每个窗口更新 execution-log 和 deployment metadata；代码/计划变更独立 commit/push，生产操作事实记录不得含 Secret。

## 完成标志

Step30 全矩阵与观察窗口通过，旧数据和旧 images 按批准周期保留后，才可声明现代化生产迁移完成。
