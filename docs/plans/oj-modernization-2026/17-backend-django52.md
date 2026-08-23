# Step 17：Django 5.2 LTS 落地

## 目标

在 Django4.2/Psycopg3、PostgreSQL目标集群和 Python3.10 已稳定后，单独落地 Django5.2.17；本次发布必须 schema-neutral。

## 进入条件

- Step 14 blocker 已清理。
- Step 15 Django4.2 deprecation gate 通过。
- Step 16 Psycopg3 全量回归通过。
- Step 20 Redis ladder、Step 21 PostgreSQL restore rehearsal 和 Step 22 PostgreSQL 生产切换已完成或获得明确的 staging/生产批准。
- `jsonfield` historical loader、fresh DB 和生产克隆均通过。

## 目标组合

- Python3.10.x `<3.11`。
- Django5.2.17 LTS。
- DRF 暂留 3.17.2 bridge。
- Psycopg3.3.4。
- Session/cache DB1、Dramatiq DB4 不变。

## 禁止同批变更

- app label、db_table、migration 名称/依赖图。
- `DEFAULT_AUTO_FIELD`、`STATIC_URL=/public/`、Session backend、CSRF middleware。
- Redis server/client、Dramatiq major、DRF3.18。
- 前端 API 结构或 Judge protocol。
- 意图性 schema migration；若 Django 生成 migration，先停。

## 实施检查

```bash
cd backend
uv add 'Django==5.2.17'
uv lock
uv sync --locked --group test --group lint
uv run --locked --no-sync python manage.py check
uv run --locked --no-sync python manage.py makemigrations --check --dry-run
uv run --locked --no-sync python manage.py test
```

fresh DB 需在隔离环境完整 replay；生产克隆需比较 migration state、schema、JSONB、index、sequence、ACL、timezone。

## 验收矩阵

- anonymous/authenticated Session、CSRF cookie/header、错误 CSRF。
- `/api` status/content-type/error-data/pagination。
- `/admin/`、`/public/`、上传、账户/题目/比赛/提交。
- Dramatiq enqueue/retry/result/TTL、DB1/DB4 key namespace。
- Judge heartbeat、dispatch、结果字段和 Token。
- 全量 backend test、worker smoke、Psycopg smoke、Docker cold/warm build。

## 停止条件

- 任何意外 migration、table/type rewrite、history 不一致。
- 历史 JSONField import 失败，或需要直接重写已应用 migration。
- API、Session/CSRF、Redis DB、Worker 或 Judge contract 改变。
- `django-dramatiq` startup/admin/migrate/worker 在目标组合下不稳定。

## 回滚

在没有新 schema/data/message 格式写入时切回 Django4.2/Psycopg3 image。若已经写入不可逆 schema 或新数据，必须按数据快照/PITR/forward-fix 决策，不由镜像回滚假装解决。

## 完成标志

提交格式建议：

```text
build(backend): land Django 5.2 LTS on Python 3.10
```

Django5.2 是最终框架目标；之后只做独立生态依赖升级。
