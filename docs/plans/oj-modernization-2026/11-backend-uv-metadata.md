# Step 11：Backend uv 元数据

## 目标

把 backend 的依赖真源从混合 `requirements.txt` 转为 `pyproject.toml + uv.lock`，但第一版只表达当前可运行版本，不升级 Django 或数据库驱动。

## 进入条件

- Step 01 已记录实际测试收集数、migration graph、API/Redis/Worker contract。
- Step 02 已完成 requirements 和直接 import 盘点。
- Python 3.10 micro 已由 Step 00 锁定。

## 文件范围

新增：

- `backend/pyproject.toml`
- `backend/uv.lock`

修改/过渡：

- `backend/deploy/requirements.txt`（只允许标注为 generated/transition）
- `backend/README.md`
- CI 配置

## pyproject 规则

- `requires-python = ">=3.10,<3.11"`。
- runtime、test、lint 分组；不要把生产依赖和测试工具混成一个无边界列表。
- 第一版保持 Django3.2.25、DRF3.14、Dramatiq1.16、django-dramatiq0.11、django-redis5.4、redis4.6、psycopg2 2.9.9 的实际行为。
- `jsonfield==3.2.0` 暂时进入 production/migrate 依赖，直到全部历史 migration 可在空库重放且不再需要它。
- 明确保留当前直接 import 的 `python-dateutil` 和 `qrcode`。
- legacy 依赖先登记处置状态，不在本 Step 替换。

## source of truth

- `pyproject.toml + uv.lock` 成为唯一真源。
- `requirements.txt` 如继续存在，只能由 lock 导出的过渡产物，禁止手工双维护。
- 生产启动不 resolve、不改写 lock。

## 计划命令

```bash
cd backend
uv --version
uv init --bare --python 3.10
# 按现有 requirements/直接 import 生成声明
uv lock
uv sync --locked --group test --group lint
uv run --locked --no-sync python manage.py check
uv run --locked --no-sync python manage.py test
uv run --locked --no-sync python manage.py makemigrations --check --dry-run
```

命令应在干净 Python3.10 环境运行。不要用 `uv add` 无约束地把最新包引入；每个变更记录来源和原因。

## 验收

- `uv lock --check`/等效 locked 校验通过。
- `uv sync --locked` 能重建与现有 requirements 等价的测试环境。
- `manage.py check`、全量测试、migration dry-run、runtime smoke 与基线一致。
- `uv tree` 中没有未审查的传递依赖漂移。
- requirements 生成规则已写入 README/CI。

## 停止条件

- 首版 lock 已升级框架、驱动、Redis 或 Worker major。
- 历史 `jsonfield` migration 在 lock 环境无法加载。
- 需要网络 resolve 才能启动生产容器，或生产会修改 lock。
- `qrcode`/dateutil 等实际直接依赖被误删。

## 回滚

删除新 pyproject/lock，恢复 requirements 安装路径；不改变代码、migration 或数据库。

## 完成标志

提交格式建议：

```text
build(backend): add uv metadata without dependency upgrades
```

下一步只切 Docker 安装器，不切框架。
