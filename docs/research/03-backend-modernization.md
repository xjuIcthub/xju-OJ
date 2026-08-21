# xju-OJ Backend 从 Django 3.2/pip 迁移到 uv + Django 5.2 LTS 专项调研报告

**研究基线**

* 仓库：`xjuIcthub/xju-OJ`
* 分支：`main`
* 固定提交：`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`；GitHub 已核实该提交存在，提交信息为 `chore: separate backend runtime services`。
* 调研截点：**2026-08-20**
* 本报告范围：**backend**
* 本次仅做联网调研和架构设计；**未修改代码、未创建分支、未创建 PR，也未实际执行仓库的 119 个测试或生产数据库迁移**。
* 文中“目标版本”指建议的生产落点，不代表某项目具有 LTS 属性；除 Django 外，不把没有官方 LTS 制度的组件称为 LTS。

---

# 一、执行摘要

## 已核实事实

1. 当前 backend 确实仍是单个 `requirements.txt`，生产依赖、测试/静态检查依赖混在一起；Django 为 3.2.25、DRF 3.14.0、Dramatiq 1.16.0、django-dramatiq 0.11.6、django-redis 5.4.0、redis-py 4.6.0、Gunicorn 21.2.0、Pillow 10.2.0、psycopg2 2.9.9，并包含 Raven、Envelopes、otpauth、jsonfield 等旧依赖。

2. 当前镜像是 `python:3.12-alpine`，依赖通过 pip 安装；源码复制发生在依赖安装之后，因此已有一定 Docker layer 隔离，但 `pip install --no-cache-dir` 与 BuildKit pip cache mount 的组合不能充分利用依赖下载缓存。

3. **当前 Python 3.12 + Django 3.2.25 本身已经不属于 Django 官方支持矩阵。** Django 3.2 官方支持到 Python 3.10；Django 3.2 LTS 已于 **2024-04-01 EOL**。Django 4.2 LTS 最终版 4.2.30 已于 **2026-04-07 EOL**。Django 5.2 是当前应选择的 LTS，扩展支持至 **2028-04**；截至截点最新安全版本是 **5.2.17，2026-08-04 发布**。

4. **建议经过 Django 4.2 跳板，但不能把 4.2 作为 2026 年新的长期生产落点。** Django 官方升级原则要求逐个检查当前版本之后直至目标版本的每个 final release 的不兼容变化和弃用项。3.2→5.2 跨越 4.0、4.1、4.2、5.0、5.1、5.2，直接跳会同时暴露大量删除项和第三方依赖变化。

5. Python 应当**继续保持 3.12 完成 Django 框架升级，再单独切换 3.13**。Django 4.2.8+ 支持 Python 3.12；Django 5.2 支持 Python 3.10–3.14，其中 Python 3.14 自 Django 5.2.8 起支持。最终首选生产 Python **3.13.15**；Python **3.14.7** 先作为 CI 兼容矩阵，不建议与 Django 5.2 首次上线同时切换。Django 官方同样强调只正式支持各 Python 系列的最新 micro release。

6. 当前路由确实使用 `django.conf.urls.url`。它在 Django 4.0 已删除，因此必须在进入 4.2 前改为 `path()`/`re_path()`，保持 `/api` 等 URL 行为不变。

7. 当前业务 JSONField 被集中封装在 `utils.models.JSONField`，但该入口仍指向 `django.contrib.postgres.fields.JSONField`。因此运行时迁移可以集中完成，不需要逐个业务模型改字段定义。

8. 历史 `problem/0001_initial.py` 从 2017 年开始并直接 import `jsonfield.fields.JSONField`；因此即使当前模型迁到 Django 原生 JSONField，**生产/migrate 环境暂时仍需要能加载外部 `jsonfield` 历史类，否则空数据库无法从 0001 开始重放 migration。**

9. 当前 PostgreSQL `ENGINE` 仍写成 `django.db.backends.postgresql_psycopg2`。这是需要在框架升级前修正为 `django.db.backends.postgresql` 的兼容项；这项配置修复本身不得被做成表结构变化。

## 最终推荐落点

建议第一轮稳定生产目标为：

* **Python 3.13.15**
* **Django 5.2.17 LTS**
* **DRF 3.17.2**，待 Django 4.2 回滚窗口正式关闭后再独立升 3.18.0
* **psycopg 3.3.4，建议 `psycopg[c]`**
* **django-redis 7.0.0**
* **redis-py 7.4.1**
* **django-dramatiq 0.15.0**
* **Dramatiq 2.2.0**，但放在 Django 5.2 稳定之后单独升级
* **Gunicorn 26.0.0**，而不是截点前仅发布 2 天的 26.1.0
* **Pillow 12.3.0**
* **django-cas-ng 5.1.1**
* **sentry-sdk 2.68.0** 替代 Raven
* **PyOTP 2.10.0** 替代 otpauth
* Django `EmailMessage` / `EmailMultiAlternatives` 替代 Envelopes
* **jsonfield 3.2.0 只作为历史 migration 兼容依赖**
* **uv 0.12.5**
* Docker 从 Alpine 转向 **Debian slim**，最终基于固定 Python 3.13 slim 镜像并 pin digest。

最重要的实施原则是：

> **不要在同一不可回滚提交中同时升级 Django、Python、psycopg、Dramatiq、Redis 客户端和操作系统基础镜像。**

---

# 二、当前仓库事实

## 已核实事实

### 2.1 依赖管理

基线 `backend/deploy/requirements.txt` 共混合运行时和开发依赖，例如 `coverage`、flake8 系列与 Django、数据库驱动、Gunicorn 全部处于同一文件。

当前没有 `pyproject.toml` 和 `uv.lock`。

### 2.2 Django 兼容债务

`oj/urls.py`：

```python
from django.conf.urls import include, url
```

所有 API 路由仍采用 `url(...)`。

`oj/settings.py` 仍有：

* `USE_L10N = True`
* Raven Django integration
* `STATIC_URL = '/public/'`
* `DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'`
* cache/session 使用 Redis DB 1
* Dramatiq broker/result 使用 Redis DB 4。

因此升级不能顺便改变 Redis DB、Session backend、静态资源路径或 AutoField 行为。

### 2.3 数据库配置

生产配置当前：

```python
'ENGINE': 'django.db.backends.postgresql_psycopg2'
```

并保持 PostgreSQL 环境变量配置。

### 2.4 JSONField 与 migration

业务模型统一通过：

```python
from utils.models import JSONField
```

使用 JSONField。

实际实现目前为：

```python
from django.contrib.postgres.fields import JSONField
```

而 2017 年的历史 migration 又直接包含：

```python
import jsonfield.fields
...
jsonfield.fields.JSONField()
```

这意味着存在三个不同问题，不能混为一谈：

* **当前运行时模型字段**
* **Django 自己旧 PostgreSQL JSONField 的历史 migration**
* **第三方 `jsonfield` 的历史 migration**

### 2.5 Docker

当前 backend：

* `FROM python:3.12-alpine`
* pip requirements
* 编译 psycopg2/Pillow 所需 Alpine build dependencies
* non-root `backend` 用户
* API/Worker/migrate 仍复用同一 image，通过 entrypoint role 启动。

“同一 backend image 多角色运行”本身没有必要取消。要求是 frontend/backend/server 各自产出镜像，而不是要求 backend API、Worker 和 migrate 变成三个不同镜像。继续复用**一个 immutable backend image**反而能避免迁移进程和应用进程依赖不一致。

---

# 三、官方支持与版本矩阵

## 3.1 Django / Python 核心矩阵

| 组件     | 版本          | 状态（2026-08-20）             | Python                   | 支持结束        | 判断        |
| ------ | ----------- | -------------------------- | ------------------------ | ----------- | --------- |
| Django | 3.2.25      | **LTS / EOL**              | 官方最高 Python 3.10         | 2024-04-01  | 立即退出      |
| Django | 4.2.30      | **LTS / EOL**              | 3.8–3.12，3.12 自 4.2.8 起  | 2026-04-07  | 只作迁移跳板    |
| Django | **5.2.17**  | **LTS / Extended Support** | 3.10–3.14；3.14 自 5.2.8 起 | **2028-04** | 最终目标      |
| Python | 3.12.x      | Security                   | Django 4.2/5.2 可用        | 2028-10     | 升级桥接版本    |
| Python | **3.13.15** | Bugfix/Maintenance         | Django 5.2 支持            | 2029-10     | 首选生产目标    |
| Python | 3.14.7      | Bugfix                     | Django 5.2.8+ 支持         | 2030-10     | 第一阶段只做 CI |

Django 官方版本表明确列出 3.2、4.2 的 EOL 时间和 5.2 LTS 的生命周期。 Django 5.2 release notes 明确支持 Python 3.10–3.14，并注明 3.14 从 5.2.8 开始支持。

截至截点，5.2.17 是 2026-08-04 发布的安全版本，应直接使用最新 patch，而非早期 5.2.x。

### 架构建议

Python 的切换顺序应为：

**3.12 + Django 3.2 → 3.12 + Django 4.2 → 3.12 + Django 5.2 → 3.13 + Django 5.2**

而不是：

**Python 3.12→3.14 + Django 3.2→5.2 同时发生。**

Python 3.14 在 Django 自身没有问题，但部分本项目关键第三方包的已发布兼容声明对 3.13 更成熟。因此 3.14 应先成为 CI lane。

---

# 四、每个当前直接依赖的处置表

“支持结束时间”若项目没有官方生命周期制度，统一记作“**未公布固定 EOL，滚动维护**”，不能自行制造 LTS/EOL 日期。

| 当前依赖                      | 推荐目标                                             | 发布/支持状态与兼容证据                                                                  | 处置方式                                | 支持结束              | 来源（访问 2026-08-20）                                                                                                    |
| ------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------------- | ----------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------- |
| Django 3.2.25             | 4.2.30 → **5.2.17**                              | 3.2/4.2 均 EOL；5.2 为 LTS，支持 Py3.10–3.14                                        | 分两跳                                 | 5.2 至 2028-04     | [Django 官方支持表](https://www.djangoproject.com/download/?utm_source=chatgpt.com)                                       |
| DRF 3.14.0                | **3.17.2**；后续 3.18.0                             | 3.18.0 为 Stable，但已丢弃 Django 4.2；3.17.2 更适合跨 4.2→5.2 回滚窗口                      | 先 3.16/3.17，关闭 4.2 回滚后升 3.18        | 未公布               | [DRF PyPI](https://pypi.org/project/djangorestframework/?utm_source=chatgpt.com)                                     |
| Dramatiq 1.16.0           | **2.2.0**                                        | 当前 2.x 支持现代 Python；2.x 属 major change                                         | Django 稳定后独立升级；保留 DB4/result key 行为 | 未公布               | [Dramatiq PyPI](https://pypi.org/project/dramatiq/?utm_source=chatgpt.com)                                           |
| django-dramatiq 0.11.6    | **0.15.0**                                       | 维护者 changelog：0.14 增加 Django 5.2，0.15 增加 Python 3.14；当前 master 也声明 Django 5.2 | 升级并做硬性 worker/admin/migrate 验收      | 未公布               |                                                                                                                      |
| django-redis 5.4.0        | **7.0.0**                                        | 7.0 要求 Django 5.2+、Python 3.10+                                               | Django 5.2 成功后再升                    | 未公布               | [django-redis PyPI](https://pypi.org/project/django-redis/?utm_source=chatgpt.com)                                   |
| redis 4.6.0               | **7.4.1**                                        | 支持现代 Python；8.1.0 截点前仅数周且又是新 major                                            | 7.4.1 作为保守生产点；8.x 后续                | 未公布               | [redis-py PyPI](https://pypi.org/project/redis/?utm_source=chatgpt.com)                                              |
| Gunicorn 21.2.0           | **26.0.0**                                       | 26.1.0 于 2026-08-18 才发布                                                       | 不在截点后两天追最新 patch；26.1 独立验证          | 未公布               | [Gunicorn PyPI](https://pypi.org/project/gunicorn/?utm_source=chatgpt.com)                                           |
| Pillow 10.2.0             | **12.3.0**                                       | Mature，Py>=3.10，现代 manylinux wheels                                           | 常规升级；验证图片编码/解码                      | 未公布               | [Pillow PyPI](https://pypi.org/project/pillow/?utm_source=chatgpt.com)                                               |
| psycopg2 2.9.9            | **psycopg[c] 3.3.4**                             | Django 5.2 支持 psycopg>=3.1.8，并推荐最新 psycopg；psycopg2 未来可能弃用                    | Django 升级独立提交切换；初期不开连接池             | 未公布               | [Django PostgreSQL 文档](https://docs.djangoproject.com/en/5.2/ref/databases/?utm_source=chatgpt.com#postgresql-notes) |
| django-cas-ng 5.0.1       | **5.1.1**                                        | 项目仍维护，声明 Django 4.2+、Python 3.10+；已有 Django 5.2 支持                            | 保留，升级；CAS/SLO 是硬验收项                 | 未公布               | [django-cas-ng PyPI](https://pypi.org/project/django-cas-ng/?utm_source=chatgpt.com)                                 |
| django-dbconn-retry 0.1.7 | **0.3.1 临时** → 目标评估移除                            | 0.3.1 于 2026 年仍发布，但状态为 Beta                                                   | 不是“死包”；先升级兼容，再通过故障注入决定是否删除          | 未公布               | [django-dbconn-retry PyPI](https://pypi.org/project/django-dbconn-retry/?utm_source=chatgpt.com)                     |
| raven 6.10.0              | **sentry-sdk[django] 2.68.0**                    | Raven 属旧 SDK；Sentry 官方推荐新 Python SDK                                          | 替换                                  | 未公布               | [Sentry SDK PyPI](https://pypi.org/project/sentry-sdk/?utm_source=chatgpt.com)                                       |
| otpauth 1.0.1             | **PyOTP 2.10.0**                                 | PyOTP 支持 HOTP/TOTP/RFC4226/6238；注意 otpauth 项目本身并非已经 EOL，当前也有新版                | 替换原因是 API/生态标准化，而不是错误声称 otpauth 已死  | 未公布               | [PyOTP PyPI](https://pypi.org/project/pyotp/?utm_source=chatgpt.com)                                                 |
| Envelopes 0.4             | Django `EmailMessage` / `EmailMultiAlternatives` | Envelopes 0.4 是 2013 年时代依赖；Django 自带维护中的邮件 API                                | 完全删除第三方依赖                           | 随 Django 5.2 生命周期 | [Django Email 文档](https://docs.djangoproject.com/en/5.2/topics/email/?utm_source=chatgpt.com)                        |
| jsonfield 3.1.0           | **3.2.0，仅 migration compatibility**              | 3.2.0 项目状态 Inactive，但声明覆盖 Django 5.2/Python 3.13                              | 禁止新业务使用；暂留生产/migrate image          | 项目无未来维护承诺         | [jsonfield PyPI](https://pypi.org/project/jsonfield/?utm_source=chatgpt.com)                                         |
| coverage 6.5.0            | **7.15.4**                                       | Stable/Production；支持现代 Python                                                 | 移到 `test` dependency group          | 未公布               | [coverage PyPI](https://pypi.org/project/coverage/?utm_source=chatgpt.com)                                           |
| flake8 7.0.0              | **7.3.0**                                        | 当前稳定 lint 工具                                                                  | 移到 `lint` group                     | 未公布               | [flake8 PyPI](https://pypi.org/project/flake8/?utm_source=chatgpt.com)                                               |
| flake8-quotes 3.3.2       | **3.4.0**                                        | 当前版                                                                           | lint-only                           | 未公布               | [flake8-quotes PyPI](https://pypi.org/project/flake8-quotes/?utm_source=chatgpt.com)                                 |
| flake8-coding 1.3.2       | 暂留 1.3.2 或删除                                     | 最新仍较老；只属于 lint concern                                                        | 先放 lint group；规则迁走后删除               | 未公布               | [flake8-coding PyPI](https://pypi.org/project/flake8-coding/?utm_source=chatgpt.com)                                 |
| entrypoints 0.4           | **优先删除直接声明**                                     | 仓库静态代码搜索无引用命中                                                                 | 用 `uv tree` + 测试确认后删除；若仅传递依赖不手工 pin | 未公布               | [entrypoints PyPI](https://pypi.org/project/entrypoints/?utm_source=chatgpt.com)                                     |
| python-dateutil 2.8.2     | 删除直接声明；若确认使用则 **2.9.0.post0**                    | 仓库静态搜索无引用命中                                                                   | 先确认动态/传递引用                          | 未公布               | [python-dateutil PyPI](https://pypi.org/project/python-dateutil/?utm_source=chatgpt.com)                             |
| qrcode 7.4.2              | 删除直接声明；若确认使用则 **8.2**                            | 仓库静态搜索无引用命中                                                                   | 同上                                  | 未公布               | [qrcode PyPI](https://pypi.org/project/qrcode/?utm_source=chatgpt.com)                                               |
| XlsxWriter 3.1.9          | **3.2.9**                                        | 当前维护版本                                                                        | 保留；对导出文件做 golden test               | 未公布               | [XlsxWriter PyPI](https://pypi.org/project/XlsxWriter/?utm_source=chatgpt.com)                                       |

### django-dramatiq 官方资料冲突

这是本次调研中需要明确记录的冲突。

维护者 CHANGELOG 明确写明：

* 0.14.0：**Add support for Django 5.2**
* 0.15.0：**Support for Python 3.14**

当前维护者 `master` 的 `setup.py` 则明确要求：

```text
django>=4.2,!=5.0.*,!=5.1.*
```

并列出 Django 4.2、5.2、6.0 和 Python 3.10–3.14 classifiers。

但已发布 PyPI 元数据中的 classifiers 曾存在没有同步列出 5.2 的情况。

**保守方案：**

使用已发布 **0.15.0**，但把 Django 5.2 下的：

* Django startup
* `migrate`
* `rundramatiq`
* actor discovery
* DB connection middleware
* result backend
* django-dramatiq 自身 migrations/admin

全部列入 **release blocker**，而不是单靠 metadata 判断兼容。

---

# 五、推荐目标及不选其他候选的原因

## 5.1 为什么必须经过 Django 4.2

**建议：是。**

但其含义是“代码兼容性检查点”，不是“2026 年再部署一个长期 4.2 平台”。

Django 官方要求跨大版本升级时检查每一个 final release 的 backwards incompatible changes/deprecations。

4.2 跳板的价值在于：

1. 先处理 Django 4.0 删除项。
2. 暴露全部 `RemovedInDjango50Warning`。
3. 让 psycopg3 可以在 Django 5.2 之前独立验证。
4. DRF、CAS、Dramatiq 集成可以分批升级。
5. 可以明确区分“Django 4.x 引入的问题”和“Django 5.x 引入的问题”。

但 Django 4.2 已于 2026-04-07 EOL，所以它只能短暂停留于 CI/staging/迁移验证环境。

## 5.2 为什么首选 Python 3.13，而不是立即 3.14

Django 自身已经支持 3.14。

不立即采用 3.14 的原因是本项目的生产风险来自**整个依赖图**而非 Django 一项：

* django-cas-ng 等外围包对 3.13 的已发布证明更成熟；
* `jsonfield` 作为历史 migration 依赖更适合在 3.13 上完成最后的兼容周期；
* Gunicorn 等生产组件的正式 classifier/CI 覆盖对 3.13 更成熟；
* Python 3.13 生命周期到 2029-10，已经覆盖 Django 5.2 的 2028-04 EOL。

因此：

> **3.13 是生产落点；3.14 是 Day-1 CI lane 和后续独立升级。**

## 5.3 为什么不直接 DRF 3.18.0

DRF 3.18 已发布且是 Stable，但它已把最低 Django 提高到 5.2。

如果 Django 5.2 首次上线就同时进入 DRF 3.18，则失去把应用快速回滚到 Django 4.2 compatibility checkpoint 的能力。

所以：

* Django 5.2 landing：DRF **3.17.2**
* 4.2 回滚窗口关闭后：独立升级 **3.18.0**

## 5.4 为什么 redis-py 不是立即 8.1

8.1.0 截止 2026-08-20 尚很新，而且又是新的 major line。

Redis 在本项目同时承担：

* Session
* cache
* waiting_queue
* Dramatiq broker
* Dramatiq result

因此首轮使用成熟的 **7.4.1** 比“追最新 major”更合理。

---

# 六、分阶段迁移路径

以下每个编号应是**独立、可审核、可测试、可回滚的提交/PR 单元**。

## B0：冻结兼容合同

不升级任何版本。

记录：

* 119 个现有测试的 baseline
* `showmigrations`
* PostgreSQL schema dump
* Django app labels
* 关键 `db_table`
* `/api` golden responses
* pagination golden responses
* Session/cookie/CSRF 行为
* Redis DB1/DB4 keys/TTL
* Dramatiq 正常、失败、重试和 result 行为
* CAS、OTP、邮件、图片和 Excel 关键用例。

**禁止 schema change。**

## B1：只引入 uv 元数据

建立：

* `backend/pyproject.toml`
* `backend/uv.lock`

但**第一版锁文件保持当前版本集合不变**。

把：

* runtime deps → `[project.dependencies]`
* coverage → `test`
* flake8 系 → `lint`
* `dev` → include test + lint

完成从“requirements 是 source of truth”到“pyproject+uv.lock 是 source of truth”。

## B2：只切安装器 pip → uv

仍保持：

* Python 3.12
* Alpine
* Django 3.2.25
* 当前应用依赖版本

Docker 改为 `uv sync --locked`。

这一提交只回答一个问题：

> uv 是否能完全复现旧运行环境？

## B3：在 Django 3.2 下提前消除 Django 4.0 blockers

分别提交：

### B3.1 URL

`django.conf.urls.url` → `re_path`/`path`。

必须保持 `/api` URL 的 regex 匹配结果完全一致。Django 4.0 已删除 `django.conf.urls.url()`。

### B3.2 JSONField runtime

`utils.models.JSONField` 从：

```python
django.contrib.postgres.fields.JSONField
```

改为：

```python
django.db.models.JSONField
```

业务模型继续从 `utils.models` 引入，以降低一次性改动面积。

### B3.3 PostgreSQL backend alias

改为：

```text
django.db.backends.postgresql
```

不改变数据库。

### B3.4 USE_L10N

先做页面/API 日期数字格式 golden test，再删除 `USE_L10N`。

它已在 Django 4.x 弃用，并在 Django 5.0 删除。

## B4：逐个处理 legacy dependencies

每项单独提交。

* B4.1 Raven → sentry-sdk
* B4.2 otpauth → PyOTP
* B4.3 Envelopes → Django Email API
* B4.4 django-cas-ng → 5.1.1
* B4.5 django-dbconn-retry → 0.3.1；通过 DB restart/failover 注入后再决定是否移除
* B4.6 `entrypoints`、`dateutil`、`qrcode` 做 direct-use audit

不要把身份认证、OTP、邮件和数据库 retry 放在一个提交里。

## B5：进入 Django 4.2 compatibility checkpoint

版本：

* Python **3.12**
* Django **4.2.30**
* DRF 可先进入 3.16.x

完成：

```text
python -Wd manage.py check
```

并跑完整 119 tests。

**4.2 已 EOL，因此不能在此长期停留。**

## B6：DRF bridge

升级到 **3.17.2**。

这样既支持 Django 5.2，又保留较好的 4.2 compatibility/rollback 路径。

## B7：Alpine → Debian slim

框架版本保持不动。

建议先：

**Python 3.12 + Debian slim**

而不是同时进入 Python 3.13。

## B8：psycopg2 → psycopg3

在：

* Django 4.2
* Python 3.12
* Debian slim

这一已知环境里单独切：

```text
psycopg2==2.9.9
    ↓
psycopg[c]==3.3.4
```

**不要启用 Django connection pool。**

## B9：Django 5.0 deprecation gate

继续在 4.2 上运行：

```text
python -Wd
```

要求项目代码产生的目标 Django deprecation warnings 清零。

## B10：Django 4.2.30 → 5.2.17

只升级 Django 这一主轴。

仍保持：

* Python 3.12
* psycopg3 已验证
* DRF 3.17.2
* 相同 PostgreSQL
* 相同 Redis topology
* 相同业务 API。

**禁止在这一提交引入 intentional schema migration。**

## B11：django-redis

Django 5.2 稳定以后：

```text
django-redis 5.4 → 7.0.0
```

Redis DB 仍必须是 **1**。

## B12：Worker/Redis modernization

建议再拆：

* Dramatiq 1.16 → 1.18 compatibility step
* Dramatiq → 2.2.0
* redis-py 4.6 → 7.4.1

尤其 Dramatiq major upgrade必须验证：

* message serialization
* ack/retry
* result storage
* result key format
* worker restart
* timeout
* duplicate execution。

DB4 不允许改变。

## B13：Python 3.12 → 3.13.15

此时才改变 Python。

保持：

* Django 5.2.17
* DRF 3.17.2
* PostgreSQL driver
* Redis stack

不变。

## B14：DRF 3.18

正式确认 Django 4.2 不再是 production rollback target 后：

```text
DRF 3.17.2 → 3.18.0
```

## B15：Python 3.14

先增加：

```text
Python 3.14.7 + Django 5.2.17
```

CI lane。

只有关键生产依赖和全部验收通过后，再作为独立 release promotion。

## B16：migration 历史整理

**不属于本轮框架现代化。**

只有 migration 已稳定多个发布周期后才讨论 squash。

鉴于本项目明确要求“保持已有 migration graph/history”，本轮实际上应当：

> **不 squash。**

---

# 七、JSONField 和历史 migration 专项方案

## 7.1 运行时模型

Django 3.2 已存在通用 `django.db.models.JSONField`。

因此应在进入 Django 4.2 前，将 `utils.models.JSONField` 的实现切换到通用 JSONField。

由于业务模型通过公共入口使用 JSONField，这个改动范围天然受控。

必须执行：

```text
manage.py makemigrations --check --dry-run
manage.py sqlmigrate ...
```

如果 Django 自动认为字段状态发生改变，不得因为“只是 JSONField”就直接应用 DDL。

## 7.2 已有生产数据库

安全优先级：

1. **保留历史兼容包**
2. 有真实 state/schema 差异时创建**新的 repair migration**
3. 依赖已无法继续安装时创建**最小 historical shim**
4. migration 完全稳定后才考虑 squash
5. **直接重写已应用 migration 最不推荐**

核心原则：

> 已经在生产执行过的 migration 是数据库历史的一部分，不应为了让代码“看起来新”而修改其 schema 语义。

Django 官方 migration 文档明确要求历史 migration 引用到的函数、类、字段仍应保持可导入；squash 也要求旧、新 migration 在过渡周期共同存在。[Django Migration 官方文档](https://docs.djangoproject.com/en/5.2/topics/migrations/?utm_source=chatgpt.com)

只有极少数官方明确允许的 historical-model/import 修正才可直接处理旧 migration；不能把这个例外推广成“可以重写 2017 schema migration”。

## 7.3 空数据库

这里要求更严格。

最终 production backend image 必须能够从：

```text
0001 → ... → latest
```

完整执行。

例如 `problem/0001_initial.py` 明确执行 import：

```python
import jsonfield.fields
```

所以在 squash 正式完成之前，`jsonfield` 不是简单的“开发依赖”，而是：

> **migration-time production dependency**

建议锁 **jsonfield 3.2.0**，明确注释为 historical migrations only。

## 7.4 shim 什么时候用

只有满足以下情况才使用：

* 原兼容包未来不能安装到目标 Python；
* 又必须支持空数据库 replay；
* 不允许重写 migration history。

shim 只实现历史 migration 反序列化所需的最小 API。

不能把 shim 再暴露给新模型。

## 7.5 `SeparateDatabaseAndState`

这是最后手段而不是默认方案。

如果：

* 数据库已经是正确 schema
* Django migration state 却需要改变

可以考虑 `SeparateDatabaseAndState`。

但 Django 官方警告 database state 和 Django state 不一致可能导致 migration framework 出错乃至数据损失，因此必须同时使用 `sqlmigrate`、数据库 schema inspection 和 `makemigrations --dry-run` 验证。[Migration operations 官方文档](https://docs.djangoproject.com/en/5.2/ref/migration-operations/?utm_source=chatgpt.com)

---

# 八、psycopg2 → psycopg 3

## 推荐方式

目标：

```text
psycopg[c]==3.3.4
```

而不是继续把 psycopg2 作为长期目标。

Django 5.2 支持 psycopg >=3.1.8，同时说明 psycopg2 未来可能被弃用，并建议采用最新 psycopg。[Django PostgreSQL 官方说明](https://docs.djangoproject.com/en/5.2/ref/databases/?utm_source=chatgpt.com#postgresql-notes)

## 8.1 为什么不是跟 Django 5.2 一起切

如果 Django 和数据库 driver 同时改变：

* ORM regression
* transaction regression
* cursor behavior regression
* adapter/type conversion regression

将很难归因。

psycopg 应当在 Django 4.2 compatibility checkpoint 上独立完成。

## 8.2 事务差异

需要重点审计 raw driver 使用。

psycopg3 与 psycopg2 的一个容易踩坑的差异：

```python
with conn:
    ...
```

在 psycopg3 中结束 transaction 后还会关闭 connection，而 psycopg2 的历史习惯不同。

同时即便是 SELECT，默认也可能启动 transaction，因此长任务必须排查 `idle in transaction`。

验收必须覆盖：

* `transaction.atomic()`
* nested atomic/savepoints
* `IntegrityError` 后 rollback
* raw cursor
* JSON
* timezone/datetime
* server-side cursor（若有）
* bulk operations
* worker 长事务。

## 8.3 Connection Pool

Django 5.1+ 可以使用 psycopg pool。

**第一阶段不要开启。**

理由：把：

* driver change
* framework change
* connection lifecycle change
* connection pooling

组合到同一个 release 没有必要。

如果生产已经有 PgBouncer，更不应未经专项测试再叠一层 Django-side pool。

## 8.4 测试数据库

必须同时验证：

* fresh test DB create/drop
* `--keepdb`
* migration replay
* DB user CREATE DATABASE 权限
* PostgreSQL connection termination
* interrupted test cleanup。

---

# 九、uv 组织方案

截至截点建议 pin **uv 0.12.5**。uv 没有官方 LTS 概念，不应称 LTS。

官方 Docker 指南已经明确提供：

* `uv sync --locked`
* `UV_NO_DEV`
* BuildKit cache mount
* `UV_LINK_MODE=copy`
* `--no-install-project`
* 先复制 lock/metadata、后复制源代码
* runtime 可以完全不包含 uv

的标准模式。[uv Docker 官方指南](https://docs.astral.sh/uv/guides/integration/docker/?utm_source=chatgpt.com)

## 9.1 `backend/pyproject.toml`

建议逻辑结构：

```toml
[project]
name = "xju-oj-backend"
version = "0.0.0"
requires-python = ">=3.13,<3.14"

dependencies = [
  "Django==5.2.17",
  "djangorestframework==3.17.2",
  "dramatiq[redis]==2.2.0",
  "django-dramatiq==0.15.0",
  "django-redis==7.0.0",
  "redis==7.4.1",
  "gunicorn==26.0.0",
  "psycopg[c]==3.3.4",
  "Pillow==12.3.0",
  "django-cas-ng==5.1.1",
  "sentry-sdk[django]==2.68.0",
  "PyOTP==2.10.0",
  "jsonfield==3.2.0",
  "XlsxWriter==3.2.9",
]

[dependency-groups]
test = [
  "coverage==7.15.4",
]

lint = [
  "flake8==7.3.0",
  "flake8-quotes==3.4.0",
]

dev = [
  { include-group = "test" },
  { include-group = "lint" },
]
```

注意这是**最终结构示例**，不能作为第一个 uv commit 直接落地；B1 应首先锁定当前依赖版本，实现 installer migration 和 dependency upgrade 解耦。

`python-dateutil`、`qrcode`、`entrypoints` 是否进入最终 dependencies，需要实际 direct-import/`uv tree` 审计。

## 9.2 `backend/uv.lock`

必须：

* commit 到 Git
* production build 使用 `--locked`
* CI 检查 lock 与 pyproject 是否一致
* 禁止容器启动时重新 resolve。

## 9.3 命令规范

开发首次：

```bash
uv sync
```

CI/生产：

```bash
uv sync --locked
```

只运行目标命令、禁止隐式改变环境：

```bash
uv run --locked --no-sync python manage.py check
uv run --locked --no-sync python manage.py migrate --no-input
uv run --locked --no-sync python manage.py test
uv run --locked --no-sync gunicorn ...
uv run --locked --no-sync python manage.py rundramatiq
```

生产 image 安装时排除 dev/test/lint groups。

## 9.4 `uv export`

**只作为过渡/第三方互操作。**

例如仍有某个安全扫描器只接受 requirements 时，可以从 `uv.lock` 导出。

禁止长期维护：

```text
requirements.txt
+
uv.lock
```

两套独立 source of truth。

正确方向是：

```text
pyproject.toml
      ↓
   uv.lock
      ↓
临时 export artifact
```

而不是反过来。

---

# 十、Docker builder/runtime 分层

## 10.1 是否应该 Alpine → Debian slim

**建议切换。**

不是因为 Alpine 不能运行 Django，而是本 backend 同时包含：

* psycopg/libpq
* Pillow
* 未来可能存在其他 C extension
* amd64/arm64 多架构要求。

Alpine 使用 musl，Python 生态的大量标准 binary wheel 主要围绕 manylinux/glibc 发行。Debian slim 能减少：

* source build fallback
* gcc/musl compilation
* 架构差异
* libpq/Pillow native dependency 差异

从而提高生产构建可预测性。

### 推荐顺序

先：

```text
Python 3.12 Alpine
→ Python 3.12 Debian slim
```

验证无行为变化后，再：

```text
Python 3.12 slim
→ Python 3.13.15 slim
```

实际 Dockerfile 应 pin image digest，而不是只依靠 floating tag。

## 10.2 Builder

Builder 包含：

* pinned uv
* compiler/build-essential
* `libpq-dev`
* 必需 image/library headers。

先只 copy/bind：

```text
pyproject.toml
uv.lock
```

再：

```text
uv sync --locked --no-dev --no-install-project
```

并使用 BuildKit：

```text
--mount=type=cache,target=/root/.cache/uv
```

多架构时 cache ID 应至少区分 architecture。

然后才 copy application source。

这样普通 Python 业务文件改动不会使依赖层失效。

## 10.3 Runtime

Runtime 仅包含：

* Python runtime
* `.venv`
* source
* `libpq` 等运行时 shared libraries
* non-root account。

不包含：

* compiler
* build-essential
* `libpq-dev`
* pip build cache
* uv 本身也可不包含。

## 10.4 backend image 角色

继续保持一个 backend image：

```text
backend:<immutable-tag>
```

运行成：

* `api`
* `worker`
* `migrate`
* bootstrap/admin one-shot

是正确方向。

这样能确保：

> migrate 运行的代码、ORM、driver、migration dependencies 与 API/Worker 完全来自同一个 immutable artifact。

---

# 十一、破坏性变更与高风险项

| 风险                                            |     等级 | 处理                            |
| --------------------------------------------- | -----: | ----------------------------- |
| `django.conf.urls.url` 删除                     |      高 | Django 4.2 前修                 |
| `django.contrib.postgres.fields.JSONField` 删除 |      高 | Django 3.2 阶段迁 current models |
| 历史 `jsonfield.fields.JSONField` import        | **极高** | 继续保留历史兼容依赖                    |
| 修改已应用 migration                               | **极高** | 原则禁止                          |
| PostgreSQL ENGINE alias                       |      高 | 框架升级前独立修                      |
| `USE_L10N` 删除                                 |      中 | 格式 golden tests               |
| psycopg2→3 transaction semantics              | **极高** | 独立 release                    |
| psycopg pool                                  |      高 | 第一阶段关闭                        |
| DRF 3.18 删除 Django 4.2 支持                     |      高 | 关闭 rollback 后才升级              |
| Dramatiq 1→2                                  | **极高** | Django5.2 后独立                 |
| Redis client major                            |      高 | 不与 Dramatiq major 同步          |
| Raven→Sentry                                  |      中 | error/privacy smoke           |
| CAS                                           | **极高** | 登录/logout/SLO/session blocker |
| OTP library                                   |      高 | RFC vectors + URI golden      |
| Alpine→Debian                                 |      中 | 独立 image release              |
| Python3.13/3.14                               |      高 | Django5.2 后独立                 |

---

# 十二、测试和验收标准

## 12.1 验收矩阵

| 场景             | Django/Python    | 必验内容                       | 通过标准                          |
| -------------- | ---------------- | -------------------------- | ----------------------------- |
| 基线             | 3.2.25 / 当前环境    | 119 tests                  | 记录 baseline                   |
| 4.2 checkpoint | 4.2.30 / 3.12    | 119 tests + warnings       | **119/119**；目标 deprecation 清零 |
| 5.2 landing    | 5.2.17 / 3.12    | 全套                         | **119/119**                   |
| Python target  | 5.2.17 / 3.13.15 | 全套                         | **119/119**                   |
| Python future  | 5.2.17 / 3.14.7  | CI compatibility           | 首轮非生产 blocker，转生产前必须全绿        |
| 空数据库           | target           | 从 2017 migration 起 migrate | 0 ImportError；全部 applied      |
| 生产克隆库          | target           | 就地 migrate                 | 无意外 DDL/数据变化                  |
| API            | target           | contracts                  | 字节/JSON 语义兼容                  |
| Worker         | target           | broker/result/retry        | 无丢任务/异常重复                     |
| Docker         | target           | amd64+arm64                | reproducible                  |

## 12.2 空数据库

必须：

1. 创建全新 PostgreSQL。
2. `migrate` 从最早历史 migration 开始。
3. 所有 migration 成功。
4. `django_migrations` 完整。
5. app label 不变。
6. table 名不变。
7. `makemigrations --check --dry-run` 无意外 drift。
8. 最终 schema 与生产克隆升级后的 schema 做结构比较。

这是判断 `jsonfield` 能否删除的核心测试。

## 12.3 生产克隆库

使用脱敏生产 snapshot：

升级前记录：

* migration state
* table/column/index/constraint
* 关键表 row count
* JSONField 非空数量
* 部分关键数据 checksum。

升级后必须确认：

* 无表 rename
* 无 app label 变化
* 无 JSONField rewrite
* 无 unexpected `DROP`
* 无不必要 type conversion
* migration lock duration 在批准窗口内。

## 12.4 119 个现有测试

硬门槛：

```text
Python3.12 + Django4.2.30   119/119
Python3.12 + Django5.2.17  119/119
Python3.13 + Django5.2.17  119/119
```

如果原 baseline 已经存在已知失败，只允许事先登记的相同失败，不允许升级过程自行把新失败解释成“历史问题”。

## 12.5 API smoke

至少覆盖：

* GET/POST `/api/...`
* anonymous/authenticated Session
* `csrftoken`
* `X-CSRFToken`
* CSRF reject/accept
* login/logout
* `/admin/` history route
* `/public/`
* `{"error": ..., "data": ...}`
* pagination schema
* content type/status code
* cookie SameSite/Secure/HttpOnly 行为。

## 12.6 Worker smoke

覆盖：

* enqueue
* successful job
* business failure
* exception
* retry
* max retries
* time limit
* worker SIGTERM/restart
* message still executable after worker restart
* result retrieve/expiration
* DB reconnect。

必须证明：

```text
Redis DB1 = session/cache/waiting_queue
Redis DB4 = dramatiq broker/result
```

升级后仍成立。

## 12.7 psycopg smoke

至少：

* ORM CRUD
* atomic
* nested savepoint
* `IntegrityError`
* manual cursor
* connection context
* JSON
* datetime/timezone
* long-running worker transaction
* DB restart
* fresh test DB
* keepdb。

## 12.8 Build/cache

必须进行两组构建：

### Cold build

清空 BuildKit cache，记录耗时和 native compilation。

### Warm build

只改一个普通 Python view/serializer 文件。

要求：

> dependency sync layer 命中缓存，不重新下载/编译整个依赖图。

同时对 amd64、arm64 验证。

---

# 十三、停止条件

出现以下任意条件，当前阶段停止，不进入下一阶段：

1. 空数据库不能完整重放 2017 至今 migrations。
2. 出现 migration `InconsistentMigrationHistory`。
3. current-model JSONField 切换产生未经解释的 DDL/data rewrite。
4. 生产克隆出现非计划 DROP/rename/type conversion。
5. app label 或 table 名变化。
6. mandatory test lane 未达到 119/119，且不是预登记 baseline failure。
7. `/api` contract、pagination、error/data wrapper 变化。
8. Session、`csrftoken`、`X-CSRFToken` 行为变化。
9. `/admin/` 或 `/public/` 路由改变。
10. Redis DB1/DB4 发生交叉使用。
11. Dramatiq 出现消息丢失、非预期重复、retry/ack/result 行为变化。
12. django-dramatiq 0.15 + Django5.2 的 worker/admin/migrate 任一无法通过。
13. CAS login/logout/SLO/session 失败。
14. OTP 已有 secret 在 PyOTP 下不能产生相同有效结果。
15. psycopg3 出现 transaction leak、连接生命周期或 raw SQL regression。
16. migration 锁表/耗时超过获批维护窗口。
17. 任一正式支持 CPU 架构出现计划外大量源码编译或构建无法复现。
18. runtime 启动需要联网 resolve/install dependency。
19. `uv.lock` 被 production startup 改写。
20. Python 3.14 存在关键依赖兼容缺口——此时只停止 **3.14 promotion**，不阻断已经稳定的 3.13+Django5.2 平台。

---

# 十四、回滚原则

## 14.1 每阶段 immutable

每个阶段保存：

* Git commit
* `uv.lock`
* backend image digest
* migration state
* deployment configuration version。

禁止使用无法追溯内容的 `latest` 作为唯一 rollback identifier。

## 14.2 schema-neutral release

对于：

* uv installer
* Debian image
* Django patch/minor compatibility
* Python runtime

若没有产生新 schema/data/serialization，原则上可以直接切回上一 image。

前提是 Session/cache/task serialization 双向兼容。

## 14.3 数据库回滚边界

这是整个项目必须明确的边界：

> **一旦新版本执行了破坏性或不可逆 migration，或者已经写入旧版本无法理解的新数据/schema/task/result 格式，回滚不再是“换回旧 Docker 镜像”。**

此时只有：

1. migration 明确可 reverse；或
2. 使用经过验证的 PostgreSQL snapshot/PITR restore；或
3. forward-fix

三种选择。

因此：

* framework/runtime upgrade 与 destructive migration **永远不在同一发布单元**
* mixed-version deployment 期间只能使用 additive/backward-compatible schema
* 数据删除、column rename/type rewrite 必须等新应用稳定后再独立执行
* 上线前必须实际做一次 restore drill，仅“有 backup”不等于有 rollback。

## 14.4 Dramatiq 回滚边界

升级 worker 时还需要单独定义 message compatibility window。

如果新 Dramatiq/serializer/result backend 已经产生旧 worker 不能理解的：

* message
* result
* Redis key

则旧 worker image 不允许直接重新消费相同 queue。

因此 Dramatiq major upgrade必须保持现有 key/serialization 格式，或采用先 drain queue 再切换的升级窗口。

---

# 十五、待本仓库实测的问题

以下属于本次联网调研无法替代实际执行的部分：

1. **119 个测试是否当前真的全部通过。**
2. `django.db.backends.postgresql_psycopg2` 在实际 production settings 下为何能与当前 Django 3.2 共存，需要运行环境确认。
3. 全仓库所有 migration 中具体有多少处：

   * `jsonfield.fields.JSONField`
   * `django.contrib.postgres.fields.JSONField`
   * 自定义 field/function import。
4. `entrypoints` 是否完全无直接/动态使用。
5. `python-dateutil` 是否为历史遗留 direct pin。
6. `qrcode` 是否通过动态 import 或业务路径间接使用。
7. 是否存在直接 `import psycopg2`。
8. 是否使用 psycopg2 custom adapters、JSON adapters、manual transactions、server cursors。
9. PostgreSQL 实际生产 major version；Django 5.2 要求 PostgreSQL 14+。
10. 是否部署 PgBouncer。
11. `django-dbconn-retry` 当前究竟解决 startup race、连接中断还是业务 query retry。
12. CAS 服务端版本和 Single Logout 的实际依赖行为。
13. otpauth 当前已有 secret/issuer/provisioning URI 的精确格式。
14. Envelopes 是否使用 HTML、attachment、BCC、custom headers 等行为。
15. Dramatiq result backend 当前真实 Redis key/serialization。
16. DB4 是否存在升级时必须保留的长 TTL result。
17. DB1 waiting_queue 是否直接依赖 redis-py 特定数据类型/编码行为。
18. Alpine→Debian 后 amd64/arm64 image 的实际大小差异。
19. `psycopg[c]` 与 `psycopg[binary]` 在目标 CI/多架构平台的 wheel/build 时间差异。
20. 空库完整 migrate 是否能在 Python3.13 + Django5.2 下无 shim 完成。
21. 生产克隆升级后的 schema 是否与 clean install 最终 schema 相同。

---

# 十六、最终决策

## 建议批准

**Django：**

```text
3.2.25
  ↓
4.2.30 compatibility checkpoint
  ↓
5.2.17 LTS
```

4.2 是必要的迁移跳板，但因为已经 EOL，不能成为新的长期生产版本。

**Python：**

```text
当前 3.12
  ↓  保持 3.12 完成 Django 4.2/5.2
3.13.15
  ↓
3.14.7 先 CI，后独立决定是否生产
```

**数据库：**

```text
psycopg2 2.9.9
  ↓ 独立 release
psycopg[c] 3.3.4
```

首轮不启用 Django connection pool。

**migration：**

```text
不重写已应用历史 migration
优先保留兼容依赖
真实修复使用新 migration
shim 只作为最后兼容手段
本轮不 squash
```

**JSONField：**

```text
current models → django.db.models.JSONField
historical jsonfield imports → jsonfield 3.2.0 暂留
```

**依赖管理：**

```text
pyproject.toml + uv.lock
uv sync --locked
uv run --locked --no-sync
uv export 仅互操作/过渡
```

**Docker：**

```text
Alpine
  ↓ 独立阶段
Debian slim
```

采用：

```text
dependency metadata
   ↓
BuildKit uv cache
   ↓
dependency layer
   ↓
application source
   ↓
minimal runtime
```

**最终建议首个稳定生产组合：**

```text
Python 3.13.15
Django 5.2.17 LTS
DRF 3.17.2
psycopg[c] 3.3.4
django-dramatiq 0.15.0
django-redis 7.0.0
redis-py 7.4.1
Gunicorn 26.0.0
Pillow 12.3.0
Debian slim
uv 0.12.5
```

Dramatiq 2.2.0、DRF 3.18.0 和 Python 3.14 均应作为**Django 5.2 稳定后的独立升级项**，而不是为了“版本更新”塞进同一现代化发布。

---

# 十七、官方来源清单

所有来源访问日期：**2026-08-20**。

### Django

* [Django 官方 Download / 生命周期表](https://www.djangoproject.com/download/?utm_source=chatgpt.com)
* [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/?utm_source=chatgpt.com)
* [Django 5.2.8 / Python 3.14 支持](https://docs.djangoproject.com/en/5.2/releases/5.2.8/?utm_source=chatgpt.com)
* [2026-08-04 Django 5.2.17 Security Release](https://www.djangoproject.com/weblog/2026/aug/04/security-releases/?utm_source=chatgpt.com)
* [2026-04-07 Django 4.2 EOL 公告](https://www.djangoproject.com/weblog/2026/apr/07/security-releases/?utm_source=chatgpt.com)
* [Django Release Notes / 跨版本升级原则](https://docs.djangoproject.com/en/5.2/releases/?utm_source=chatgpt.com)
* [Django Migration 官方文档](https://docs.djangoproject.com/en/5.2/topics/migrations/?utm_source=chatgpt.com)
* [Migration Operations](https://docs.djangoproject.com/en/5.2/ref/migration-operations/?utm_source=chatgpt.com)
* [Django PostgreSQL / psycopg 官方说明](https://docs.djangoproject.com/en/5.2/ref/databases/?utm_source=chatgpt.com#postgresql-notes)
* [Django Email API](https://docs.djangoproject.com/en/5.2/topics/email/?utm_source=chatgpt.com)

### Python

* [Python 官方 Downloads / 生命周期入口](https://www.python.org/downloads/?utm_source=chatgpt.com)
* [Python Developer Guide Versions Status](https://devguide.python.org/versions/?utm_source=chatgpt.com)

### uv

* [uv 官方项目依赖管理](https://docs.astral.sh/uv/concepts/projects/dependencies/?utm_source=chatgpt.com)
* [uv Locking / Syncing](https://docs.astral.sh/uv/concepts/projects/sync/?utm_source=chatgpt.com)
* [uv Docker Integration](https://docs.astral.sh/uv/guides/integration/docker/?utm_source=chatgpt.com)
* [uv Export](https://docs.astral.sh/uv/concepts/projects/export/?utm_source=chatgpt.com)

### psycopg

* [Psycopg 3 Installation](https://www.psycopg.org/psycopg3/docs/basic/install.html?utm_source=chatgpt.com)
* [Psycopg 3 Transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html?utm_source=chatgpt.com)
* [Psycopg 2 → 3 Differences](https://www.psycopg.org/psycopg3/docs/basic/from_pg2.html?utm_source=chatgpt.com)

### 直接依赖发布/维护证据

* [Django REST framework PyPI](https://pypi.org/project/djangorestframework/?utm_source=chatgpt.com)
* [Dramatiq PyPI](https://pypi.org/project/dramatiq/?utm_source=chatgpt.com)
* [django-dramatiq 维护者仓库](https://github.com/Bogdanp/django_dramatiq?utm_source=chatgpt.com)
* [django-redis PyPI](https://pypi.org/project/django-redis/?utm_source=chatgpt.com)
* [redis-py PyPI](https://pypi.org/project/redis/?utm_source=chatgpt.com)
* [Gunicorn PyPI](https://pypi.org/project/gunicorn/?utm_source=chatgpt.com)
* [Pillow PyPI](https://pypi.org/project/pillow/?utm_source=chatgpt.com)
* [psycopg PyPI](https://pypi.org/project/psycopg/?utm_source=chatgpt.com)
* [django-cas-ng PyPI](https://pypi.org/project/django-cas-ng/?utm_source=chatgpt.com)
* [django-dbconn-retry PyPI](https://pypi.org/project/django-dbconn-retry/?utm_source=chatgpt.com)
* [jsonfield PyPI](https://pypi.org/project/jsonfield/?utm_source=chatgpt.com)
* [PyOTP PyPI](https://pypi.org/project/pyotp/?utm_source=chatgpt.com)
* [Sentry SDK PyPI](https://pypi.org/project/sentry-sdk/?utm_source=chatgpt.com)
* [Envelopes PyPI](https://pypi.org/project/Envelopes/?utm_source=chatgpt.com)
* [otpauth PyPI](https://pypi.org/project/otpauth/?utm_source=chatgpt.com)
* [coverage PyPI](https://pypi.org/project/coverage/?utm_source=chatgpt.com)
* [flake8 PyPI](https://pypi.org/project/flake8/?utm_source=chatgpt.com)
* [flake8-quotes PyPI](https://pypi.org/project/flake8-quotes/?utm_source=chatgpt.com)
* [flake8-coding PyPI](https://pypi.org/project/flake8-coding/?utm_source=chatgpt.com)
* [entrypoints PyPI](https://pypi.org/project/entrypoints/?utm_source=chatgpt.com)
* [python-dateutil PyPI](https://pypi.org/project/python-dateutil/?utm_source=chatgpt.com)
* [qrcode PyPI](https://pypi.org/project/qrcode/?utm_source=chatgpt.com)
* [XlsxWriter PyPI](https://pypi.org/project/XlsxWriter/?utm_source=chatgpt.com)

**最终风险评级：中高，但可控。**

风险主要不是 Django 5.2 本身，而是 **十年 migration 历史 + JSONField 双重历史依赖 + psycopg 事务变化 + Worker/Redis 状态兼容**。按上述分阶段路径实施，可以把这些风险拆成彼此独立的验证和回滚边界；若直接把 Django、Python、psycopg、Dramatiq、Redis 与基础镜像一次性升级，则不符合本仓库生产级现代化要求。
