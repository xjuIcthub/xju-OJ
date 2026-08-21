# Step 16：psycopg2 到 Psycopg 3

## 目标

在 Django4.2、Python3.12、目标 PostgreSQL 集群已稳定后，单独切换数据库 driver；不同时升级 Django、PostgreSQL、连接池或 Dramatiq。

## 进入条件

- Step 15 全量测试和 deprecation checkpoint 通过。
- PostgreSQL 目标集群已经过 restore/业务校验。
- 旧 psycopg2 image、PG 备份和回滚路径仍可用。

## 目标

```text
psycopg2==2.9.9
→ psycopg[c]==3.3.4（具体 patch 以 Step00 复核）
```

首轮不启用 Psycopg connection pool，不改变 PgBouncer/连接复用策略。

## 文件范围

- `backend/pyproject.toml`、`uv.lock`
- `backend/oj/settings.py`/数据库 backend 配置
- raw cursor/connection 使用处
- worker/task 连接生命周期
- 数据库集成测试和 Dockerfile

## 必测场景

- ORM CRUD、JSON/JSONB、datetime/timezone、bulk 操作。
- `atomic()`、嵌套 savepoint、`IntegrityError` 后 rollback。
- raw cursor/connection context manager。
- worker 长事务、`idle in transaction`、超时和 SIGTERM。
- DB restart/reconnect、连接终止和 interrupted cleanup。
- fresh test DB、`--keepdb`、并发测试。
- PostgreSQL 关键查询计划和索引使用情况。

## 计划命令

```bash
cd backend
uv add 'psycopg[c]==3.3.4'
uv lock
uv sync --locked --group test
uv run --locked --no-sync python manage.py check
uv run --locked --no-sync python manage.py test
```

再用隔离 Compose 注入 DB 重启和连接断开；不得在生产命令中暴露连接串密码。

## 验收

- 全量 backend 测试、API smoke、migration dry-run、Worker smoke 通过。
- 事务、savepoint、异常恢复和连接释放与 psycopg2 golden 一致。
- 无长期 `idle in transaction`、连接泄漏或 worker 重连风暴。
- 旧 psycopg2 image 可在 schema/data 不变时直接恢复。

## 停止条件

- 需要同时改变 Django、PG schema、连接池或队列消息格式。
- raw API 差异无法通过 owning layer 修复和测试解释。
- 新 driver 只能在生产关闭事务/限制条件后工作。

## 回滚

无新 schema/data/message 写入时切回 psycopg2 image；若应用已经产生新数据行为，先停写并执行数据库业务核账，不能盲目降级。

## 完成标志

提交格式建议：

```text
build(backend): migrate database driver to psycopg 3
```

完成后才允许 Django5.2 landing。
