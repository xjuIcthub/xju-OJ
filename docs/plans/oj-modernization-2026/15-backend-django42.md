# Step 15：Django 4.2 兼容检查点

## 目标

用 Django 4.2.30 在 Python3.10、Step21 fresh target/restore staging 中消化 deprecation，作为可回滚的中间点；不把 4.2 作为长期生产版本，也不要求先切换生产 PostgreSQL。

## 依赖与前置

- Step 14 的 URL/JSONField/legacy blocker 清理通过。
- WSL/huawei1 隔离演练：Step 21 的 fresh target/restore 已通过即可，Step 22 不是开发前置。
- Phase 5 生产 promotion：Step 22 必须按生产窗口完成并观察稳定，或本 Step 只停留在 staging image。
- 旧 Django3.2 + psycopg2 image 仍保留。
- Redis DB1/DB4 职责不变。

## 变更范围

- `backend/pyproject.toml`/`uv.lock`：只升级 Django 到 4.2.30，并锁兼容依赖。
- 代码：只修 Django 4.2 产生的 deprecation/removed API。
- 测试：补齐 warnings、migration、API/Session/CSRF、Worker。

不同时做：

- psycopg2→psycopg3
- Dramatiq major、redis-py major
- schema migration、app label/db_table 改名
- frontend 或 Judge toolchain 升级

## 计划命令

```bash
cd backend
uv add 'Django==4.2.30'
uv lock
uv sync --locked --group test --group lint
python -Wd manage.py check
python -Wd manage.py test
python -Wd manage.py makemigrations --check --dry-run
```

生产/迁移命令必须使用 `uv run --locked --no-sync` 或构建好的同一 `.venv`；禁止现场 resolve。

## 验收

- `RemovedInDjango50Warning` 中由项目代码产生的 warning 清零；第三方未解决项有书面豁免。
- fresh DB 可重放全部历史 migration，生产克隆无意外 schema 变化。
- API wrapper、分页、Session/CSRF、`/admin/`、`/public/` 全通过。
- Worker enqueue/retry/result/TTL、Redis DB1/DB4、Judge dispatch 全通过。
- 4.2 image 与 3.2 image 都可在兼容窗口部署。

## 停止条件

- 迁移图不一致、JSONField loader 失败、意外 migration。
- API/Session/CSRF、队列或判题结果改变。
- 4.2 只有通过同时升级多个未验证依赖才能启动。
- 计划把 4.2 镜像长期留在生产而没有 5.2 时间窗。

## 回滚

在没有新 schema/data/message 格式写入时直接切回 Django3.2 digest。若已有 migration，先按 Step 22 的 PostgreSQL 数据回滚规则处理，不能只换镜像。

## 完成标志

提交格式建议：

```text
build(backend): establish Django 4.2 compatibility checkpoint
```

该 checkpoint 是后续 Psycopg3 和 Django5.2 的基线。
