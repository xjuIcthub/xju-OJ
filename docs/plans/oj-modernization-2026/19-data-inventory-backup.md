# Step 19：数据盘点与可恢复备份

## 目标

在任何 PostgreSQL/Redis major 操作前建立脱敏 inventory、可恢复备份、业务 manifest 和容量/停机证据。

## Phase 执行模式

- Phase 2：先实现工具并对 fixture、空 fresh DB 或脱敏 clone 验证；真实生产 clone 暂不可用时记录 `release-gate pending`，不阻塞 WSL 全栈。
- Phase 4：在 huawei1 隔离项目重复 protected clone/restore 能力。
- Phase 5：必须对真实生产数据生成 final backup、hash、manifest 和 restore 证据，缺失时 hard stop。

## 进入条件

- Step 03 Ubuntu `>=22.04` 目录、权限和备份路径通过；非生产模式不要求生产 Secret。
- Step 01 已定义 schema/Redis/Judge 合同。
- 运维已批准 staging clone；生产读取命令必须只读或按 runbook 执行。

## PostgreSQL inventory

记录：

- server version、encoding、timezone、locale/collation、checksum、数据库大小。
- extensions、roles、owners、ACL、tablespaces/global objects。
- schema/object/row counts、完整 `django_migrations`。
- JSON/JSONB 列、固定 PK 样本、索引/constraint/trigger/function。
- sequence `last_value/is_called`、owned column、最大 PK。
- 手工 SQL、外部导入和 runtime 文件关联。

## Redis inventory

### DB1

- `INFO`、persistence、DBSIZE、key type/TTL 分布。
- Session/cache namespace。
- `waiting_queue` type、LLEN、完整 JSON、submission/problem 映射和 SHA-256 manifest。

### DB4

- queue、ready/delayed/ACK/result/DLQ 等实际 namespace。
- message ID、actor、submission/problem 映射。
- 不以 `DBSIZE` 相等代替业务核账。

## 文件/runtime inventory

- `backend/public`、`backend/test_case`、上传和配置资源。
- Judge `/judger` scratch、`/log`、数据量和 ownership。
- 旧 PG/Redis 卷、备份、空闲空间和 inode。
- Secret 只记录路径、权限、版本指纹；不记录内容。

## 备份要求

- PostgreSQL globals + directory-format database dump；使用目标 PG client 验证。
- Redis RDB/AOF 或一致 snapshot；保留原卷，生成 key/queue manifest。
- runtime/public/test_case 文件快照；至少一份离开活动卷。
- 每个 artifact 生成 SHA-256、时间、来源、工具版本。
- 必须在隔离环境真实 restore；命令成功不等于备份可用。

## 计划命令

示意，实际连接参数通过 Secret file/受控环境注入：

```bash
pg_dumpall --globals-only > "$BACKUP_DIR/postgres/globals.sql"
pg_dump -Fd --format=directory --file="$BACKUP_DIR/postgres/database" "$DATABASE_NAME"
sha256sum "$BACKUP_DIR/postgres/globals.sql"

redis-cli -n 1 --rdb "$BACKUP_DIR/redis/db1.rdb"
redis-cli -n 4 --rdb "$BACKUP_DIR/redis/db4.rdb"
sha256sum "$BACKUP_DIR/redis"/*
```

不要把密码写入 URL、shell history 或日志；生产需使用官方支持的认证文件/Secret 方式并由 runbook 记录。

## 验收

- PG、DB1、DB4、runtime 均有 manifest、hash 和 restore 记录。
- 能在隔离 staging 还原一个真实脱敏 clone。
- 备份、旧卷、新卷和 restore 临时空间同时可用。
- waiting_queue 与未完成 Dramatiq message 可映射到业务对象。

## 停止条件

- 备份只能生成不能恢复。
- waiting_queue/DB4 未完成项不可核账。
- 空间不足以保留 old/new/backup。
- 方案要求覆盖唯一旧卷、`FLUSHDB` 或 `pg_upgrade --link` 后删除源卷。

## 回滚

本 Step 不改变服务版本；删除错误的脱敏 manifest，保留已验证备份和旧卷。

## 完成标志

提交格式建议：

```text
ops: add data platform inventory and restore evidence
```

没有可恢复备份，后续 Redis/PG Step 自动阻塞。
