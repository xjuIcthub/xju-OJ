# Step 14：Django 兼容债务清理

## 目标

在仍可运行的 Django 3.2 环境中先消除 Django 4.2/5.2 blocker，降低后续 major 升级的同时变更量。

## 进入条件

- Step 13 的 Python3.10 镜像通过。
- Step 01 的 URL/API/schema golden 可运行。
- 任何 migration 修改都必须经过专项审查。

## URLConf

全量替换 `from django.conf.urls import url`：

- 使用 `django.urls.re_path` 保留原 regex。
- 保留可选尾斜杠、route name、include 顺序、`/api/` 和 `/api/admin/`。
- 不趁机改变 URL 结构或 response。

范围至少包括：

```text
backend/oj/urls.py
backend/account/urls/**
backend/announcement/urls/**
backend/conf/urls/**
backend/contest/urls/**
backend/problem/urls/**
backend/submission/urls/**
backend/utils/urls.py
```

## JSONField 与数据库设置

- `backend/utils/models.py` 的 current model alias 改为 `django.db.models.JSONField`。
- 历史 migration 中的 `jsonfield.fields.JSONField` 和旧 PostgreSQL JSONField 默认不改。
- `production_settings.py`/`dev_settings.py` 的 engine alias 改为 `django.db.backends.postgresql`，先证明无 DDL。
- 保留 `DEFAULT_AUTO_FIELD = AutoField`。
- 先为日期、数字、locale 输出建立 golden，再处理 `USE_L10N`。

## Legacy 依赖分项

- Raven → sentry-sdk：保留 DSN 空/启用两条路径。
- otpauth → PyOTP：旧 secret、TOTP vector、URI issuer/label golden。
- Envelopes → Django Email API：保留 HTML、TLS、显示名、异常行为。
- `jsonfield`：直到 fresh DB migration 证明不再需要前，保留在生产迁移环境。
- `python-dateutil`、`qrcode`：当前有直接 import，不能误删。
- django-cas-ng、dbconn-retry：先核对真实启用方式，不凭静态“似乎未引用”删除。

## 验收

```bash
cd backend
python -Wd manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

另跑 URL、JSON、邮件、OTP、图片、API/CSRF、fresh DB migration smoke。`makemigrations` 产生新的字段改变或 DDL 时停止。

## 停止条件

- app label、db_table、migration graph 或 API 路径变化。
- current JSONField 切换产生未解释的 AlterField/DDL。
- 历史 migration loader 失败却试图直接重写旧 migration。
- legacy 替换造成 TOTP、邮件、错误上报或序列化差异。

## 回滚

每一类 URL/legacy 改动单独提交；可恢复旧 import/依赖，不触碰数据库数据。若已创建新 migration，先检查是否已应用，再决定 validated reverse/forward-fix。

## 完成标志

提交格式建议分批：

```text
refactor(backend): remove Django 4 compatibility blockers
refactor(backend): replace legacy service adapters
```

通过后才进入 Django 4.2 checkpoint。
