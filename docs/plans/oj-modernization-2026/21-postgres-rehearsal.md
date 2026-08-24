# Step 21：PostgreSQL 10 → 18.6 恢复演练

## 目标

在不切生产写入的前提下，用 PG18 fresh cluster 和真实脱敏 dump 完成至少两次恢复演练；PG17.11 只作为 PG18 blocker 的批准备选。

## Phase 执行模式

- Phase 2：先对 fixture/脱敏 clone 建立 fresh restore、校验脚本和兼容 target，供 backend/Compose 开发。
- Phase 4/5：使用 protected/production clone 至少两次恢复并记录容量、时长和业务核账；这才构成生产 Step22 的批准证据。

## 进入条件

- 当前环境对应的 Step 19 PG dump、globals、runtime snapshot 可恢复；Phase 2 不要求生产 dump。
- Redis/Worker 不需要在本 Step 同时切换。
- 旧 PG10 数据目录和服务仍可独立启动。

## 选择原则

主方案：`postgres:18.6-bookworm` + verified digest。报告曾推荐 PG17；若 PG18 在真实 restore、扩展、collation、Django/driver smoke 发现 blocker，记录证据后改用 `postgres:17.11-bookworm`，不要临时混用两个版本。

PG10 data directory 不直接挂给 PG18；默认采用 fresh cluster + `pg_restore`，不把 `pg_upgrade --link` 作为本项目首选。

## 恢复步骤

1. 新建独立 PG18 volume 和临时网络。
2. 先恢复 globals/roles/ACL，再创建数据库。
3. `pg_restore --exit-on-error -j N` 恢复 directory dump。
4. 执行 `ANALYZE`，记录 restore、index、analyze 时长。
5. 比较 schema/object/row counts、JSONB、索引/约束、sequence、collation、timezone、owner/ACL。
6. 用 Django3.2 + 当前 driver 做 check、ORM CRUD、API、Session/CSRF、文件和 Judge smoke。
7. 运行完整 migration dry-run，确认不需要改历史 migration。
8. 至少重复一次，使用相同或更新的生产 clone。

## 校验重点

- `django_migrations` 完整且一致。
- 关键表 row count、状态分布、固定 PK 样本。
- JSONB 语义、NULL/默认值、编码。
- sequence 不落后于最大 PK。
- indexes/constraints/triggers/functions 和扩展。
- UTC、历史 timestamp epoch、locale/collation。
- 数据库角色、owner、权限和连接限制。

## 计划命令

```bash
pg_restore --exit-on-error -j "${PG_RESTORE_JOBS:-4}" \
  --dbname="$TARGET_DATABASE" "$BACKUP_DIR/postgres/database"
psql "$TARGET_DATABASE" -v ON_ERROR_STOP=1 -c 'ANALYZE;'
python backend/manage.py check
python backend/manage.py showmigrations --plan
python backend/manage.py makemigrations --check --dry-run
```

连接认证必须通过受控 Secret file；命令样例不包含实际凭据。

## 验收

- 两次 fresh restore 均成功，日志、时长、hash 可追溯。
- Django3.2/当前 driver 在 PG18 上可完成只读和测试写入 smoke。
- 没有 DROP/rename/type rewrite/JSON rewrite 或 migration history 差异。
- 空间、停机窗口和并行恢复参数有实测值。

## 停止条件

- restore 报错、扩展缺失、ACL/sequence/collation/JSONB 不一致。
- 只能通过修改历史 migration、表名或删除数据来启动。
- 备份未真实恢复过，或恢复时间超过业务批准窗口且无方案。
- PG18 与当前旧应用组合不兼容且没有可解释修复。

## 回滚

演练环境删除临时 PG18 volume；保留原始 dump。生产 PG10 不变，不执行任何切换。

## 完成标志

提交格式建议：

```text
ops: rehearse PostgreSQL target restore
```

通过后才允许 Step 22 生产切换。
