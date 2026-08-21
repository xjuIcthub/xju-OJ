# xju-OJ：2026 生产版本基线与生命周期矩阵调研报告

**研究对象**：xjuIcthub/xju-OJ
**固定分支**：`main`
**固定提交**：`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`
**调研截点**：2026-08-20
**访问日期**：除特别说明外，官方资料均访问于 **2026-08-20**

---

## 一、执行摘要

### 1. 最终结论

对于该仓库，不建议采用“所有东西都升级到最新”的策略。最合理的 2026 生产基线是：

| 层               | 最终建议                                        |
| --------------- | ------------------------------------------- |
| Node.js         | **24.19.0 / 24.x Active LTS**               |
| pnpm            | **11.22.0 stable**                          |
| Vite            | **8.2.x**，明确固定在当前获得 regular patches 的 minor |
| Vue             | **3.5.41 stable**                           |
| Vue Router      | **5.2.0 stable**                            |
| Pinia           | **4.0.3 stable**                            |
| Vue I18n        | **11.4.8 stable**                           |
| Axios           | **1.19.0 stable**                           |
| Vitest          | **4.1.10 stable**                           |
| Playwright      | **1.62.1 stable**                           |
| Nginx           | **1.30.4 stable**                           |
| Python          | **3.13.15**                                 |
| Django          | **5.2.17 LTS**                              |
| uv              | **0.12.5**，提交 `uv.lock`                     |
| DRF             | **3.18.0**                                  |
| Gunicorn        | **26.1.0**                                  |
| Dramatiq        | **2.2.0**                                   |
| django-dramatiq | **0.15.0，但 Django 5.2 兼容性必须作为阻断测试项**        |
| django-redis    | **7.0.0**                                   |
| redis-py        | **8.1.0**                                   |
| psycopg         | **3.3.4 / Psycopg 3**                       |
| PostgreSQL      | **17.10**                                   |
| Redis Server    | **8.2.x，建议当前 8.2 patch；迁移必须独立实施并先完成许可审查**   |
| Redis 替代        | 若必须采用 BSD 风格许可，再独立评估 **Valkey 8.1.9**       |
| Debian          | **13 / Trixie**                             |
| Java            | **Temurin 21.0.12 LTS**                     |
| Judge Node      | **Node 24 LTS**                             |
| Judge Go        | **Go 1.26.7**                               |
| Judge GCC       | **Debian 13 的 GCC 14 系列**                   |

其中最重要的八个版本决策是：

1. **Node 24，而不是 Node 26。** 2026-08-20 Node 24 是 Active LTS，Node 26 仍是 Current，计划到 2026-10-28 才转 LTS。
2. **pnpm 11.22.0，而不是 pnpm 12。** 12 仍停留在 `12.0.0-rc.6`。
3. **Vite 固定 8.2.x。** 官方明确只有 `vite@8.2` 收 regular patches；8.1 只收重要修复/安全补丁。
4. **Python 3.13.15，而不是 3.14.7，作为本仓库第一生产落点。** 两者均处于 bugfix 生命周期，但 3.13 对旧 Django 生态、C 扩展和本仓库迁移风险更低。Python 3.14 可以进入 CI 兼容矩阵。
5. **最终明确选择 Django 5.2.17 LTS。** Django 4.2 已于 2026-04-07 EOL，只允许作为迁移跳板，不能重新成为生产目标。
6. **PostgreSQL 17.10，而不是 18.4。** 18 已稳定但发布时间更短；17 已经历更多生产周期，并支持到 2029-11-08。
7. **不建议 Redis 8.0；7.4 与 8.2 二选一时，长期目标建议 8.2。** Redis 8.0 将于 2026-12-01 EOL；7.4 到 2029-12-01；8.2 到 2030-09-01。Redis 8 同时恢复 AGPLv3 这一 OSI 开源选项。
8. **不能把 Vue/Vite/pnpm/Python/PostgreSQL/Valkey/nginx/Go/GCC 等称为 LTS。** 它们各自使用 stable、GA、bugfix/security、supported releases 等不同维护模型。

**本仓库最终建议采用“保守生产组合”为主体，再单独把 Redis 落在 8.2，而不是整体采用激进组合。**

---

# 二、当前仓库事实

## 2.1 固定基线已核实

截至本报告截点，GitHub `main` HEAD 正好就是指定提交：

`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`

提交信息为 `chore: separate backend runtime services`。

一级目录包含 `frontend`、`backend`、`server`，根目录存在 `docker-compose.yml`。

### frontend

当前依赖仍然属于明显的上一代前端生态：

* Vue `^2.5.16`
* Vue Router `^3.0.1`
* Vuex `^3.0.1`
* Vue I18n `^7.7.0`
* Axios `^0.18.0`
* Webpack `^3.6.0`。

`.nvmrc` 锁定 **Node 14.21.3**。

因此 Vue 2→3、Webpack 3→Vite 8、Vuex→Pinia、Axios 0.18→1.x 都不是简单依赖刷新，而属于明确的迁移项目。

### backend

固定提交中的主要 Python 依赖包括：

* Django 3.2.25
* DRF 3.14.0
* django-dramatiq 0.11.6
* Dramatiq 1.16.0
* django-redis 5.4.0
* redis-py 4.6.0
* Gunicorn 21.2.0
* psycopg2 2.9.9。

代码中已经存在必须保留的核心行为：

* `SessionMiddleware`
* `CsrfViewMiddleware`
* `/public/`
* `AUTH_USER_MODEL = "account.User"`
* Redis DB 1 作为默认 cache/session
* Dramatiq broker/result 使用 Redis DB 4
* `DEFAULT_AUTO_FIELD = AutoField`。

生产配置仍使用 PostgreSQL，并保留 `django.db.backends.postgresql_psycopg2`；Redis 和运行目录已有部分环境变量化。

### server

JudgeServer 是 Flask 服务，其协议已经形成稳定兼容面：

* POST `/judge`
* POST `/ping`
* POST `/compile_spj`
* `X-Judge-Server-Token`
* JudgeServer 自身返回 `{"err": ..., "data": ...}`。

注意这里的 `err` 与浏览器业务 API 要保留的 `error` 是**两个不同协议**，现代化时不能误统一。

Judger 当前固定：

* `/judger/run`
* `/test_case`
* compiler/code/spj 独立用户
* 明确 UID/GID 角色。

JudgeServer Dockerfile 已经使用 `debian:trixie-slim` 和 BuildKit apt cache，但运行工具链仍硬编码：

* Python 3.12
* Go 1.22
* Temurin 21
* GCC/G++ 13
* NodeSource Node 20

同时 Flask/Gunicorn 等 Python 依赖没有严格版本锁。

这形成一个当前构建隐患：**Trixie 基础镜像正在前进，而 Dockerfile 继续请求上一代发行版中的具体包名。**

### 根 docker-compose

根 compose 与源代码现代化程度明显脱节，目前仍包含：

* `redis:4.0-alpine`
* `postgres:10-alpine`
* 远程 `oj-image/judge:1.6.1`
* 远程 backend 镜像

Judge 服务已经具有：

* `read_only: true`
* capability drop
* `/test_case` 只读 mount。

这些 Judge 安全设置必须作为迁移不变量。

---

# 三、2026 生产版本基线与生命周期总表

> “无 LTS”不是“不维护”，而是该项目官方没有使用 LTS 这一产品术语。
> 无固定 EOL 的库以“当前受支持稳定线”管理，并通过 Renovate/Dependabot/定期升级窗口维护。

| 组件                 | 当前版本                    | 候选版本                            | 推荐版本                    | LTS/状态                      | 支持结束                              | 最低系统/兼容要求                              | 迁移跳板                           | 主要风险                             | 官方来源                  |
| ------------------ | ----------------------- | ------------------------------- | ----------------------- | --------------------------- | --------------------------------- | -------------------------------------- | ------------------------------ | -------------------------------- | --------------------- |
| Node.js / frontend | 14.21.3                 | 24.19.0 / 26.7.0                | **24.19.0 / 24.x**      | **Active LTS**；26 为 Current | 24: **2028-04-30**；26: 2029-04-30 | Vite 8 要求 Node >=20.19 或 >=22.12；24 满足 | 可先在旧 Vue 构建兼容测试                | Node 26 到 10/28 才 LTS            | Node Release WG       |
| pnpm               | Yarn Classic            | 11.22 / 12 RC                   | **11.22.0**             | Stable；**无 LTS**            | 无固定 EOL                           | 使用 Node 24 构建                          | Yarn→pnpm lock 独立提交            | node_modules 严格解析暴露隐式依赖          | npm tags              |
| Vite               | Webpack 3.6             | 8.0/8.1/8.2                     | **8.2.x**               | 当前 supported minor；无 LTS    | 滚动支持                              | Node >=20.19 或 >=22.12                 | 先替换 build system，再动业务框架亦可      | Vite 8 改为 Rolldown 核心            | Vite 官方               |
| Vue                | 2.5.16                  | 3.5.41 / 3.6 RC                 | **3.5.41**              | Stable；无 LTS                | 无固定 EOL                           | Vue 3 工具链                              | `@vue/compat` 可作为临时桥           | Options API、插件、render 行为         | Vue policy/npm        |
| Vue Router         | 3.0.1                   | 5.2.0                           | **5.2.0**               | Stable；无 LTS                | 无固定 EOL                           | Vue 3                                  | Route contract tests           | history/base/动态路由变化              | npm                   |
| Pinia              | Vuex 3                  | 4.0.3                           | **4.0.3**               | Stable；无 LTS                | 无固定 EOL                           | Vue 3                                  | Vuex 可暂时继续存在                   | store 初始化/持久化语义                  | npm                   |
| Vue I18n           | 7.7                     | 11.4.8                          | **11.4.8**              | Stable；无 LTS                | 无固定 EOL                           | Vue 3                                  | 单独迁移 locale API                | legacy API 差异                    | npm/维护者发布记录           |
| Axios              | 0.18                    | 1.19.0                          | **1.19.0**              | Stable；无 LTS                | 无固定 EOL                           | Node/browser                           | 单独升级                           | CSRF、interceptor、error semantics | 官方 release/npm        |
| Vitest             | 无                       | 4.1.10 / 5 RC                   | **4.1.10**              | Stable；无 LTS                | 无固定 EOL                           | Node >=20；与现代 Vite 配合                  | 先建立 contract tests             | Jest/API 差异                      | npm/官方发布              |
| Playwright         | 无                       | 1.62.1                          | **1.62.1**              | Stable；无 LTS                | 无固定 EOL                           | 官方支持当前 Node 22/24/26、Debian 12/13 等    | 无                              | Browser image/CI 体积              | npm/官方 requirements   |
| nginx              | 根部署体系隐含代理职责             | mainline 1.31.3 / stable 1.30.4 | **1.30.4 stable**       | Stable；**无 LTS**            | 无固定 EOL                           | Linux                                  | 无                              | stable/mainline 不等于 LTS/非 LTS    | nginx 官方              |
| Python             | backend image 已开始用 3.12 | 3.13.15 / 3.14.7                | **3.13.15**             | Bugfix；**无 LTS**            | **2029-10**                       | Django 5.2 支持                          | 3.12→3.13                      | native wheels、pickle、第三方包        | Python 官方             |
| Python 新线          | —                       | 3.14.7                          | CI 兼容，暂不主生产             | Bugfix；无 LTS                | **2030-10**                       | Django 5.2.8+                          | 生产稳定后再切                        | 生态成熟度较 3.13 低                    | Python/Django         |
| Django             | 3.2.25                  | 4.2.30→5.2.17                   | **5.2.17 LTS**          | **LTS**                     | **2028-04**                       | Python 3.10–3.14；PG14+                 | **4.2 只作开发迁移桥**                | 3.2→5.2 删除 API/默认行为              | Django 官方             |
| Django 4.2         | —                       | 4.2.30                          | 不作为生产目标                 | LTS **已 EOL**               | **2026-04-07**                    | —                                      | 仅用于消化 deprecation              | 已无安全支持                           | Django 官方             |
| DRF                | 3.14                    | 3.18.0                          | **3.18.0**              | Stable；无 LTS                | 无固定 EOL                           | Django 5.2/6.x；Python 3.10–3.14        | 可先升 Django 再升 DRF              | 3.18 有明确 breaking changes        | DRF 官方                |
| uv                 | 无                       | 0.12.5                          | **0.12.5**              | Stable；无 LTS                | 无固定 EOL                           | Python 项目                              | requirements→pyproject/uv.lock | uv minor/lock schema 演进          | Astral 官方             |
| Gunicorn           | 21.2                    | 26.1.0                          | **26.1.0**              | Production/Stable；无 LTS     | 无固定 EOL                           | Python >=3.10                          | 单独升级                           | HTTP/worker 行为变化                 | PyPI                  |
| Dramatiq           | 1.16                    | 2.2.0                           | **2.2.0**               | Stable；无 LTS                | 无固定 EOL                           | Python >=3.10；含 3.14 classifier        | 先保留 DB4 和 queue schema         | 1→2 行为/API 变化                    | PyPI                  |
| django-dramatiq    | 0.11.6                  | 0.15.0                          | **0.15.0，条件通过**         | Stable；无 LTS                | 无固定 EOL                           | Python >=3.10                          | 独立兼容阶段                         | classifier 只明确到 Django 5.1       | PyPI                  |
| django-redis       | 5.4                     | 7.0.0                           | **7.0.0**               | Stable；无 LTS                | 无固定 EOL                           | Python >=3.10；Django >=5.2             | Django 后迁移                     | session/pickle compatibility     | PyPI                  |
| redis-py           | 4.6                     | 8.1.0                           | **8.1.0**               | Stable；无 LTS                | 无固定 EOL                           | Redis 7.2→current                      | 单独升级 client                    | redis-py 8 默认 RESP3 wire         | PyPI                  |
| psycopg            | psycopg2 2.9.9          | psycopg 3.3.4                   | **3.3.4**               | Production/Stable；无 LTS     | 无固定 EOL                           | Python >=3.10；Django 5.2 支持 psycopg3   | psycopg2 保留到 DB/Django 稳定      | adaptation/autocommit 差异         | Psycopg/PyPI          |
| PostgreSQL         | **10**                  | 17.10 / 18.4                    | **17.10**               | Supported；无 LTS 标签          | **2029-11-08**                    | Django 5.2 要求 PG14+                    | DB 升级必须先于最终 Django             | 跨 7 个 major                      | PostgreSQL 官方         |
| PostgreSQL 18      | —                       | 18.4                            | 较新方案                    | Supported                   | **2030-11-14**                    | 同上                                     | —                              | 发布年限较短                           | PostgreSQL 官方         |
| Redis Server       | **4.0**                 | 7.4 / 8.0 / 8.2                 | **8.2.x**               | GA；OSS 官方不称 LTS             | **2030-09-01**                    | Redis clients；DB numbering 可继续         | Redis 单独迁移                     | persistence/client/licensing     | Redis 官方              |
| Redis 7.4          | —                       | 7.4.x                           | 保守过渡候选                  | GA                          | **2029-12-01**                    | —                                      | 可作过渡但无必要多跳一次                   | RSALv2/SSPLv1，非 BSD              | Redis 官方              |
| Redis 8.0          | —                       | 8.0                             | **不选**                  | GA                          | **2026-12-01**                    | —                                      | —                              | 距 EOL 仅数月                        | Redis 官方              |
| Valkey             | 无                       | 8.1.9 / 9.1.1                   | **8.1.9，仅作为独立替代方案**     | Stable；无 LTS                | 8.1 security 至 **2030-03-31**     | RESP2/3                                | 若从 Redis<=7.2 迁移最顺             | Redis7.4+ RDB/AOF 不兼容            | Valkey 官方             |
| Debian             | server source 已用 Trixie | 12 / 13                         | **13 Trixie**           | Stable，未来进入 Debian LTS      | LTS 至 **2030-06-30**              | —                                      | 无                              | 当前 Dockerfile 老包名需清理             | Debian                |
| Debian 12          | —                       | Bookworm                        | 不作为新镜像首选                | oldstable/LTS 阶段            | **2028-06-30** LTS                | —                                      | 可用于兼容镜像                        | 生命周期短于 Trixie                    | Debian                |
| Temurin Java       | 21                      | 21 / 25                         | **21.0.12 LTS**         | **LTS**                     | 至少 **2029-12**                    | Judge runtime                          | 保持 21 即可                       | Java 版本改变可能影响判题                  | Adoptium              |
| Temurin 25         | —                       | 25.0.4                          | 较新组合                    | **LTS**                     | 至少 **2031-09**                    | —                                      | 后续独立升级                         | 新 bytecode/runtime 行为            | Adoptium              |
| Node / Judge       | NodeSource 20           | 24 / 26                         | **24 LTS**              | Active LTS                  | **2028-04-30**                    | —                                      | 20→24                          | JS 判题结果/性能变化                     | Node 官方               |
| Go / Judge         | 1.22                    | 1.26.7 / 1.27.0                 | **1.26.7**              | Stable；无 LTS                | Go 使用“最近两条 major”支持政策             | —                                      | 逐语言更新                          | 1.27.0 于 **2026-08-19** 才发布      | Go 官方 release history |
| GCC / Judge        | 13                      | 14/15/16                        | **Debian 13 GCC 14 系列** | Supported release；无 LTS     | 无固定单一 EOL                         | 受 Debian 生命周期约束                        | 13→14                          | 编译器优化/诊断/资源使用差异                  | GCC 官方                |

---

# 四、需要重点澄清的生命周期问题

## 4.1 Node 24 vs Node 26

### 已核实事实

截至 2026-08-20：

* Node 24：**Active LTS / Krypton**
* Node 24 Maintenance 开始：2026-10-20
* Node 24 EOL：2028-04-30
* Node 26：**Current**
* Node 26 计划 LTS：2026-10-28
* Node 26 EOL：2029-04-30。

发布记录可核实：

* Node 24.19.0：2026-08-03
* Node 26.7.0：2026-08-05。

### 官方资料冲突

较旧的 Node Release README 曾将 Node 26 Maintenance Start 列为 **2027-10-27**；最新 `main/README.md` 与 `schedule.json` 已改为 **2027-10-20**。

**本报告采用更新的 canonical schedule：2027-10-20。**

### 架构建议

选择 **Node 24**。

Node 26 的优势只是多约一年生命周期，但它在截点仍是 Current。对一个同时需要从 Vue 2、Webpack 3、Yarn Classic 跨代迁移的项目而言，没有理由再额外引入 Current Node 的变化面。

---

## 4.2 pnpm 11 vs pnpm 12

### 已核实事实

截至截点：

* `11.22.0` = `latest`
* `12.0.0-rc.6` = `next-12`

即 pnpm 12 **仍然是 RC，不是 stable**。

### 建议

明确选择：

**pnpm 11.22.0**

并在 `packageManager`、Corepack/镜像构建脚本和 lockfile 中锁定。

不能因为 12 “马上正式”就在生产基线上提前押注 RC。

---

## 4.3 Vite 应锁哪个 minor

这是本次前端版本选择中最明确的官方信号之一。

Vite 官方截至截点明确列出：

* `vite@8.2`：**regular patches**
* `vite@8.1`：important fixes + security patches
* `vite@8.0`：security patches
* 更早版本逐渐退出支持。

因此不能只写：

> Vite 8

而应该写：

> **Vite 8.2.x**

并由 `pnpm-lock.yaml` 再锁定具体 patch。

Vite 官方也明确说明 pre-release 不适合生产。

---

## 4.4 Python 3.13 vs 3.14

### 已核实事实

截至截点：

* Python **3.13.15**，bugfix 生命周期，EOL 2029-10
* Python **3.14.7**，bugfix 生命周期，EOL 2030-10。

Django 5.2：

* 支持 Python 3.10–3.14
* Python 3.14 从 Django **5.2.8** 开始获得支持
* Django 官方原则上推荐最新 Python，但同时明确第三方应用可以有自己的兼容要求。

### 架构建议

对于一个全新 Django 项目，我会认真考虑 Python 3.14。

对于 **xju-OJ 这种 Django 3.2 老系统跨代迁移**，建议第一生产落点是：

**Python 3.13.15。**

原因不是 3.14 不稳定，而是此次迁移同时涉及：

* psycopg2→psycopg3
* redis-py
* django-redis
* Dramatiq
* django-dramatiq
* Pillow/C 扩展
* 老项目 pickle/session 数据
* JudgeServer native extension

减少一个最新 Python feature line，可以显著降低故障归因难度。

**Python 3.14.7 应直接进入 CI compatibility job。** Django 5.2 稳定一个发布周期后，再作为独立升级切换。

---

## 4.5 Django 是否明确选 5.2 LTS

**是。明确选择 Django 5.2.17 LTS。**

Django 5.2 extended support 到 **2028-04**。

Django 4.2 已于 **2026-04-07** 结束 extended support。

因此：

`3.2 → 4.2 → 5.2`

是合理的**开发迁移顺序**，但不是：

`3.2 production → 4.2 production → 5.2 production`

4.2 只能作为：

> deprecation scanner / 临时开发分支 / staging bridge

不能让已经 EOL 的 4.2 再成为长期线上版本。

Django 在 2026-08-10 宣布从 2028 年开始改变 release policy，但官方明确指出 **5.2 和 6.2 的既有支持承诺不变**。

---

## 4.6 PostgreSQL 17 vs PostgreSQL 18

### 已核实事实

| 版本            |  当前 patch |         首发 |            EOL |
| ------------- | --------: | ---------: | -------------: |
| PostgreSQL 17 | **17.10** | 2024-09-26 | **2029-11-08** |
| PostgreSQL 18 |  **18.4** | 2025-09-25 | **2030-11-14** |

PostgreSQL 官方为 major 提供约 **5 年**支持，并建议始终使用该 major 最新 minor。

### 建议

**本仓库选 PostgreSQL 17.10。**

18.4 并不是 RC，也不存在“不稳定”的问题；它属于完全可用于生产的 supported version。

不选它的原因在于：

> xju-OJ 当前还是 PostgreSQL 10。

一次从 10 跨到 17，本身已经是大型数据库迁移。没有必要为了多一年 EOL 再把目标推到一个生产沉淀相对较短的 major。

数据库版本后续从 17→18 的风险，远小于今天 10→17。

---

## 4.7 Redis 7.4 / 8 / Valkey

这里不能简单用“哪个版本新”决定。

### Redis OSS 生命周期

官方当前列出：

| Redis       | 状态 |            EOL |
| ----------- | -- | -------------: |
| 7.4         | GA |     2029-12-01 |
| 8.0         | GA | **2026-12-01** |
| 8.2         | GA | **2030-09-01** |
| 8.4/8.6/8.8 | GA |        EOL TBD |

因此 **Redis 8.0 是明确应该避开的过渡 minor**。

### 许可

Redis：

* <=7.2：BSD-3-Clause
* 7.4：RSALv2 或 SSPLv1
* 8+：RSALv2 / SSPLv1 / **AGPLv3**
* AGPLv3 是 OSI-approved open-source license。

因此从“是否开源”角度看，Redis 8 比 Redis 7.4 的情况反而更明确：Redis 8 提供 AGPLv3 选择。

### Valkey

Valkey 具有明确支持模型：

* 8.1 maintenance：2028-03-31
* 8.1 security：2030-03-31
* 9.1 maintenance：2029-05-19
* 9.1 security：2031-05-19。

8.1.9 与 9.1.1 均在 2026-07-21 发布。

但是有一个非常重要的迁移限制：

> Redis OSS <=7.2 与 Valkey 可直接使用兼容 RDB/AOF；Redis CE 7.4+ 生成的数据文件不再与 Valkey兼容。

### 最终建议

对于这个 OJ：

**目标 Redis 8.2.x。**

条件：

1. 完成 AGPL/RSAL/SSPL 使用场景的组织级许可确认；
2. Redis 升级必须成为独立基础设施阶段；
3. 绝不能与 Django、Python、psycopg 升级放进一个回滚单元。

如果项目治理明确要求 BSD/permissive Redis 系生态，则：

**单独启动 Valkey 8.1.9 迁移项目。**

不要因为“Valkey 更开源”顺手把 Redis→Valkey 塞进 Django 现代化 PR。

---

# 五、哪些项目实际上没有 LTS

## 明确有 LTS 概念

* **Node.js 24**
* **Django 5.2**
* **Eclipse Temurin 21 / 25**

Debian 则有 **LTS 维护阶段**，而不是类似 Java 的“某一个版本叫 LTS edition”。

## 不应称为 LTS

以下项目在本报告中只能称相应的官方状态：

* pnpm：stable
* Vite：supported stable minor
* Vue：stable
* Vue Router：stable
* Pinia：stable
* Vue I18n：stable
* Axios：stable
* Vitest：stable
* Playwright：stable
* Python：bugfix / security
* uv：stable
* DRF：supported stable
* Gunicorn：Production/Stable
* Dramatiq：stable
* django-dramatiq：stable
* django-redis：stable
* redis-py：stable
* Psycopg：Production/Stable
* PostgreSQL：supported major，5-year support policy
* Redis Open Source：GA + EOL
* Valkey：stable + maintenance/security window
* nginx：stable/mainline
* Go：stable + rolling support
* GCC：supported releases

特别需要避免一个容易产生的误区：

**Redis Cloud 文档确实把 8.2/7.4 标成 LTS、8.0 标成 STS，但这是 Redis Cloud 产品生命周期标签。**

不能反过来宣称：

> “自建 Redis OSS 8.2 是 LTS。”

Redis OSS 自己的 version-management 页面使用的是 **GA + EOL**。

---

# 六、推荐目标及不选其他候选的原因

## frontend

### 推荐

`Node 24 + pnpm 11 + Vite 8.2 + Vue 3.5`

### 不选择

**Node 26**：仍是 Current。

**pnpm 12**：仍是 RC。

**Vue 3.6**：截至截点 `3.6.0-rc.4`，Vue 官方明确禁止将 pre-release 用于 production。

**Vite 8.0/8.1**：虽然仍获得一定支持，但 8.2 才是 regular-patch minor。

---

## backend

### 推荐

`Python 3.13 + Django 5.2 LTS + uv`

而不是为了“更新”直接采用 Python 3.14 + Django 最新 feature release。

Django 5.2 的优势是：

* LTS 承诺明确
* 支持 Python 3.13
* PostgreSQL/Psycopg 路线成熟
* 给老系统提供更长的迁移和观察窗口。

一个需要特别标红的第三方生态风险是：

**django-dramatiq 0.15.0 的 PyPI classifier 只明确列 Django 4.2、5.0、5.1，没有列 Django 5.2。**

这不证明它无法运行在 5.2。

但在生产架构报告里也不能写成：

> “django-dramatiq 已官方支持 Django 5.2。”

因此它是**迁移阻断验证项**。

---

## infrastructure

### PostgreSQL

17 优先于 18，是为了成熟度与故障归因，不是因为 18 不稳定。

### Redis

8.2 优先于 8.0。

7.4 可以作为纯粹追求最小变化的候选，但从长期支持窗口和 Redis 8 AGPL 选项来看，若已经要从 Redis 4 做一次大迁移，多停一次 7.4 的收益有限。

### Debian

新镜像统一以 **Debian 13 / Trixie** 为基础更合理。

Debian 13 当前 stable，并计划：

* 2028-08-09 进入 LTS
* 2030-06-30 结束 LTS。

Bookworm 到截点已经属于 oldstable/LTS 路线。

官方资料在 Bookworm “Security Team→LTS Team”精确切换日上存在表述差异：

* LTS 页面：2026-06-11
* Debian releases 表：2026-07-11。

但这并不影响架构结论：

**到 2026-08-20，Bookworm 已不应作为新的长期基础镜像首选。**

---

# 七、分阶段迁移路径

## Phase 0：冻结兼容契约

任何框架升级前先建立 golden/black-box tests。

必须覆盖：

1. 浏览器请求仍为 same-origin `/api`
2. Session login/logout
3. `csrftoken`
4. `X-CSRFToken`
5. `/admin/` 直接访问、刷新、history fallback
6. `/public/` 静态文件
7. 成功与错误 API 的 `{"error": ..., "data": ...}`
8. pagination JSON
9. Django app labels
10. DB table names
11. migration graph
12. Redis DB1 与 DB4
13. waiting_queue
14. Judge `/judge`
15. `/compile_spj`
16. `/ping`
17. heartbeat
18. Token 校验
19. judge result schema
20. `/test_case` read-only
21. UID/GID
22. CPU/memory/process/file/output/time limits
23. Seccomp deny behavior。

没有这一步，后续不能开始 major migration。

---

## Phase 1：先现代化构建与部署骨架

**不要同时升级业务框架。**

先建立三个独立镜像：

* `frontend`
* `backend`
* `server`

其中 `backend` 可以保持**一个镜像，多种 command**：

* API service → Gunicorn
* worker service → Dramatiq

这样既满足“backend 独立镜像”，又避免 API/worker 复制两套 Python runtime。

根目录改为唯一部署入口：

`./deploy.sh`

职责顺序应该是：

**配置校验 → 环境/目录校验 → BuildKit 构建 → DB/Redis readiness → 初始化 → migration → compose up → smoke test**

deployment config 至少外置：

* bind address
* HTTP/HTTPS port
* domain
* runtime root
* data directories
* test-case directory
* image registry
* frontend/backend/server image tag
* PostgreSQL 参数
* Redis 参数。

---

## Phase 2：BuildKit 与基础镜像

### frontend

依赖层应只由：

* Node image
* pnpm version
* `package.json`
* `pnpm-lock.yaml`

决定。

典型缓存逻辑应是：

`lockfile → pnpm fetch/store → install → COPY source → build`

普通 Vue 源代码变化不应重新下载 npm 依赖。

最终 runtime 使用 nginx，而不是把 Node 构建环境带进生产镜像。

### backend

建议：

* Python 3.13 slim/Trixie base
* 固定 uv 0.12.5
* `pyproject.toml`
* 提交 `uv.lock`

Astral 官方明确建议在 Docker 中：

* pin uv version
* 可进一步 pin SHA256 digest
* `uv sync --locked`
* dependency 与 project 分层，以提高 Docker cache 命中率。

因此依赖层应类似：

`pyproject + uv.lock → uv sync deps → COPY backend source → install project`

业务 Python 文件变化不应触发所有 wheel 重新解析和安装。

### server

需要单独维护较重的“judge toolchain base”。

至少把：

* libseccomp
* CMake
* C compiler
* Java
* Go
* Node
* Python

与 JudgeServer Python 业务源代码分层。

**改 Flask Python 文件不应该重新编译 C Judger。**

当前 Dockerfile 已开始使用 BuildKit apt cache，这是正确方向，应保留。

CI/registry 进一步使用 BuildKit：

* `cache-to`
* `cache-from`
* architecture-specific cache

避免 amd64/arm64 缓存污染。

---

# 八、业务框架迁移顺序

## Frontend

推荐顺序不是：

> Vue2 + Webpack3 + Yarn → 一次性 Vue3 + Router5 + Pinia + Vite8 + pnpm + Axios1

而是：

### F1：测试基线

先让旧 Vue 2 页面进入 Playwright black-box coverage。

### F2：包管理与构建

引入：

* Node 24
* pnpm 11
* Vite 8.2

解决：

* aliases
* environment variables
* static asset paths
* Webpack loader/plugin 替代。

### F3：Vue 2→3

目标 Vue 3.5.41。

必要时使用 `@vue/compat` 作为临时迁移机制。

### F4：Router

单独升级 Vue Router。

重点验证：

* `/admin/`
* browser back/forward
* direct deep-link reload
* 404 fallback
* query/hash semantics。

### F5：状态和 i18n

分别：

`Vuex → Pinia`

`Vue I18n 7 → 11`

不要合并成一个无法定位行为变化的大提交。

### F6：Axios

Axios 0.18→1.19 单独实施。

重点比较：

* request interceptor
* error structure
* timeout
* serialization
* CSRF cookie/header
* credentials。

---

# 九、Backend 迁移顺序

推荐顺序：

## B1：先把依赖管理迁移到 uv

第一阶段尽量**复现旧 requirements 行为**，不顺带大升级 Django。

生成并提交 deterministic `uv.lock`。

---

## B2：PostgreSQL 10→17

必须作为**独立基础设施发布**。

Django 5.2 已要求 PostgreSQL 14+，因此数据库必须在最终 Django 5.2 落地之前解决。

推荐采用经过排练的 dump/restore 或明确受支持的跨 major 升级链，而不是现场第一次尝试。

迁移前必须完成：

* full backup
* restore rehearsal
* row counts
* FK/index verification
* sequence verification
* encoding/collation 检查
* extensions 检查。

---

## B3：Django 3.2→4.2

仅在开发/staging 中用于：

* `python -Wd`
* 修复 deprecation
* 识别 middleware/config/API removals。

不要重新上线长期运行 Django 4.2。

---

## B4：Django 4.2→5.2.17

之后才形成新的 production candidate。

必须明确保持：

* app labels
* `db_table`
* migration files
* `AutoField`
* session engine
* CSRF middleware
* `/public/`
* API formatter。

不得为了“干净”重新生成 migrations。

---

## B5：Python 3.13

Django 5.2 application tests 全绿后，再将 runtime 定在 Python 3.13.15。

这样出现故障时能够区分：

> Django migration 问题

与

> Python runtime 问题。

---

## B6：Psycopg 3

`psycopg2 → psycopg 3.3.4`

独立迁移。

不要和 PostgreSQL major upgrade 同一个回滚单元。

---

## B7：DRF

3.18.0 自己明确包含 breaking changes，包括停止 Django 4.2/5.0/5.1 支持。

因此必须经过 API golden tests。

---

## B8：Redis / Dramatiq Python ecosystem

分别处理：

* django-redis 7
* redis-py 8
* Dramatiq 2
* django-dramatiq 0.15

尤其 redis-py 8 默认在 wire 上改用 RESP3，同时保留兼容 response shape。

不能假设升级毫无行为差异。

---

# 十、Redis Server 独立迁移

Redis 4→8.2 应作为独立 maintenance window。

升级前记录：

### DB1

* sessions
* cache
* waiting_queue
* key patterns
* TTL
* serializers
* memory usage

### DB4

* Dramatiq queues
* result keys
* middleware keys
* TTL。

必须证明：

**DB1 仍然只承担 Session/cache/waiting_queue，DB4 仍然只承担 Dramatiq。**

不能借升级改成一个 Redis DB。

值得注意的是 django-redis 默认大量使用 Python pickle，并说明默认 `pickle.DEFAULT_PROTOCOL` 是为了跨 Python 升级兼容。

这进一步说明：

**不要同时升级 Python runtime 和 Redis server。**

---

# 十一、JudgeServer / Judger 迁移

Judge 模块的标准与普通 Web 服务不同：

> 安全边界和行为确定性优先于工具链“最新”。

## S1：先只重建基础镜像

保留：

* API
* Token
* UID/GID
* Seccomp
* resource limits
* file permissions
* `/test_case:ro`

不改变语言版本。

## S2：修正 Trixie toolchain packaging

当前 Dockerfile 是：

> Debian Trixie + Python3.12 package names + Go1.22 + GCC13 + Node20

这容易随着 Debian archive 演进失去可重复构建能力。

应统一到 Trixie 自身合理的工具链，或明确使用受控外部 toolchain repository/image。

## S3：语言一个一个升级

顺序建议：

* Node 20 → Node 24
* Go 1.22 → Go 1.26.7
* GCC 13 → GCC 14
* Java 21 → **继续 Java 21.0.12**

每次只改一种语言，再跑完整判题 corpus。

### 为什么不立即 Go 1.27

Go 1.27.0 在 **2026-08-19** 才发布。

调研截点是第二天。

把一个刚发布约一天的 compiler/runtime 作为生产 OJ 判题基线没有任何必要。

Go 1.26.7 同日在维护线上发布，更适合作为生产锁定点。

### 为什么 Java 保持 21

Temurin 21 和 25 都是 LTS。

但现有 Judge 已经运行 Java 21，21.0.12 至少支持到 2029-12。

为了增加“4 年生命周期”去改变 Java 判题环境，没有足够收益。

---

# 十二、破坏性变更与高风险项

| 风险                          | 等级               | 原因                                |
| --------------------------- | ---------------- | --------------------------------- |
| PostgreSQL 10→17            | **Critical**     | 跨七个 major，回滚依赖数据恢复                |
| Judge Seccomp/toolchain     | **Critical**     | 可能改变安全边界或判题语义                     |
| Vue2→3                      | High             | framework behavior 跨代             |
| Webpack3→Vite8              | High             | bundler architecture 完全变化         |
| Router3→5                   | High             | SPA history/deep-link             |
| Django3.2→5.2               | High             | 多代 deprecated API 删除              |
| Redis4→8.2                  | High             | server/client/persistence/许可一起变化  |
| psycopg2→3                  | High             | DB driver semantics               |
| DRF3.14→3.18                | High             | API behavior/validation           |
| Axios0.18→1.19              | High             | HTTP/CSRF/interceptor             |
| Dramatiq1→2                 | High             | worker/broker behavior            |
| django-dramatiq + Django5.2 | **High/Unknown** | 维护者 metadata 尚未明确声明 5.2           |
| Python3.13                  | Medium           | wheels/serialization/runtime      |
| Pinia                       | Medium           | store migration                   |
| Vue I18n                    | Medium           | API rewrite                       |
| Node24 build                | Low/Medium       | 本身为 LTS，主要风险来自旧 Webpack ecosystem |

---

# 十三、测试和验收标准

一次阶段迁移只有同时满足以下条件才能发布。

## Web contract

* `/api` same-origin
* 不引入依赖 CORS 的架构
* Session cookie 正常
* `csrftoken` 正常
* `X-CSRFToken` 正常
* login persistence 正常
* `/admin/...` URL 刷新正常
* `/public/...` 200
* API success/error wrapper byte-level/schema-level 等价
* pagination 等价。

## Django/database

* `showmigrations` migration graph 不被重写
* app label 相同
* table names 相同
* primary key 类型没有意外变化
* schema diff 只包含经过批准的变化
* record counts 对齐
* FK/index/sequence 对齐。

## Redis

* DB1 keyspace 正确
* DB4 keyspace 正确
* 不发生跨 DB key 漏放
* sessions 在滚动升级中继续可读
* waiting_queue 正常
* Dramatiq retry/result 正常
* TTL 行为一致。

## Judge

至少准备一套固定 judge corpus：

* AC
* WA
* TLE
* MLE
* RE
* CE
* output limit
* fork/process violation
* file access violation
* malicious syscall
* Java
* C
* C++
* Python
* Go
* JavaScript
* SPJ。

验证：

* `/ping`
* `/judge`
* `/compile_spj`
* heartbeat
* token reject/accept
* 所有结果字段
* CPU time
* real time
* memory
* exit signal
* error code。

还必须做负向安全测试：

* `/test_case` 写入应失败
* prohibited syscall 应失败
* UID/GID 不变
* 不新增 privileged
* 不新增额外 capabilities
* Seccomp 不得放宽。

## Deployment

改变部署配置而不改代码，应能修改：

* port
* bind IP
* domain
* runtime path
* image tag。

`./deploy.sh` 必须：

* 首次执行成功
* 重复执行幂等
* 初始化过的数据库不重复破坏性初始化
* migration failure 时停止
* health check failure 时返回非零。

## Cache

普通 frontend `.vue` 改动：

> 不应重新下载整个 pnpm dependency graph。

普通 backend `.py` 改动：

> 不应重新 resolve/install 全部 Python dependencies。

JudgeServer Python 业务改动：

> 不应重新编译 C Judger、GCC/Go/JDK。

这是 BuildKit 设计是否真正有效的验收标准，而不是“Dockerfile 里用了 cache mount”就算完成。

---

# 十四、停止条件

任何阶段出现以下情况，应立即停止发布而不是继续“把升级做完”：

1. 必须修改现有 Django app label 才能继续
2. 必须重建/改写历史 migrations
3. API wrapper 或 pagination 无法保持
4. Session/CSRF 无法保持
5. `/admin/` 或 `/public/` 无法兼容
6. PostgreSQL restore rehearsal 没有成功
7. 数据库回滚时间不可接受
8. Redis DB1/DB4 隔离发生变化
9. session pickle 无法兼容
10. django-dramatiq 在 Django 5.2 下存在未解决错误
11. Judge 结果 schema 变化
12. Judge Token protocol 变化
13. Judge heartbeat 变化
14. `/test_case` 需要写权限
15. Judger 需要 privileged mode
16. 需要新增危险 capability
17. Seccomp 必须放宽才能运行
18. resource limit 语义与旧版本不同且无法解释
19. 单次提交同时要求不可逆 DB migration + framework major + infrastructure major
20. 新镜像依赖 mutable/unpinned 外部 toolchain，无法重建同一 artifact。

---

# 十五、回滚原则

## 1. 一个阶段只改变一个主要风险轴

禁止：

> PostgreSQL 17 + Django 5.2 + Python3.14 + Psycopg3 + Redis8 + Dramatiq2

一次上线。

这种版本即使测试成功，故障时也几乎无法定位。

## 2. 三个模块独立 image tag

frontend、backend、server 分别拥有：

* immutable tag
* ideally digest
* previous-good tag。

frontend 出问题不应要求回滚 Judge。

## 3. 数据库不做“版本降级”

PostgreSQL major rollback 的本质是：

> 恢复升级前 snapshot / backup

不是把 PostgreSQL17 volume 直接重新挂回 PostgreSQL10。

## 4. Redis 同理

升级前保留：

* RDB/AOF snapshot
* config
* version
* keyspace statistics。

不要假设 Redis 高版本 persistence 可以随意让旧版本读取。

## 5. 旧 volume 延迟清理

新版本通过完整观察期之前，不删除：

* PostgreSQL old volume/snapshot
* Redis snapshot
* 前一版 images
* 前一版 deployment config。

---

# 十六、待本仓库实测的问题

以下问题通过文档无法替代真实代码/数据验证。

### Frontend

1. Webpack-specific loader/plugin 使用了多少
2. 是否存在 `require.context`
3. 是否依赖 `process.env.*`
4. 是否存在 runtime template compilation
5. Vue2 非标准生命周期/filters/mixins 使用量
6. Router history 配置及 `/admin/` 实际匹配方式
7. Vuex plugins
8. Axios 是否自定义 CSRF/interceptors
9. `/public/` 是否同时被 Django 与 frontend 使用。

### Backend

1. Django 3.2 deprecation warnings 实际数量
2. 是否有 removed Django APIs
3. 第三方 apps 是否修改 app label
4. migration 中 PostgreSQL-specific SQL
5. `jsonfield`→Django native JSONField 是否需要迁移
6. Raven/Sentry 老集成
7. django-cas-ng 与 Django5.2
8. django-dramatiq 0.15 + Django5.2
9. Redis cache pickle 中是否存在长期对象
10. DRF custom pagination/renderers/exceptions
11. Psycopg2 特有 API
12. transactions/autocommit assumptions。

### PostgreSQL

1. 实际数据库大小
2. extensions
3. collations
4. indexes
5. custom SQL
6. downtime budget
7. sequence correctness
8. PostgreSQL10 dump→17 restore 时间。

### Redis

1. DB1/DB4 实际 key count
2. memory
3. TTL
4. persistence format
5. queue backlog
6. session 生命周期
7. waiting_queue implementation
8. Dramatiq result backend 实际使用量。

### Judge

1. libjudger 在 Debian13/GCC14 下是否完全通过
2. seccomp syscall list 对新 runtime 是否足够
3. Java21 patch update 是否改变 memory accounting
4. Go1.26 binary memory/cpu accounting
5. Node24 V8 JIT 对 memory/time limit 的影响
6. GCC14 优化后历史题答案/时间
7. SPJ compile/runtime
8. `/test_case` inode/ownership
9. amd64/arm64 是否都需要支持。

---

# 十七、推荐的“保守生产组合”

这是**以生态成熟度和故障可诊断性优先**的组合：

```text
Frontend
  Node.js        24.19.0 / 24.x Active LTS
  pnpm           11.22.0
  Vite           8.2.x
  Vue            3.5.41
  Vue Router     5.2.0
  Pinia          4.0.3
  Vue I18n       11.4.8
  Axios          1.19.0
  Vitest         4.1.10
  Playwright     1.62.1
  nginx          1.30.4 stable

Backend
  Python         3.13.15
  Django         5.2.17 LTS
  uv             0.12.5
  DRF            3.18.0
  Gunicorn       26.1.0
  Dramatiq       2.2.0
  django-dramatiq 0.15.0 (compatibility gate)
  django-redis   7.0.0
  redis-py       8.1.0
  psycopg        3.3.4

Infrastructure
  PostgreSQL     17.10
  Redis          7.4.x 或在单独验证后直接 8.2.x
  Debian         13 / Trixie

Judge
  Temurin        21.0.12 LTS
  Node           24 LTS
  Go             1.26.7
  GCC            Debian 13 GCC 14 series
```

Redis 是这里唯一需要额外解释的部分：

若“保守”指**最小运行时变化**，7.4 比 8.2 更保守。

若“保守”指**未来 3～4 年减少再次升级次数**，则 8.2 更合理。

---

# 十八、推荐的“较新但仍可控组合”

```text
Frontend
  Node 24 LTS
  pnpm 11
  Vite 8.2
  Vue 3.5
  其余全部 stable
  （仍然拒绝 Node 26 Current / pnpm 12 RC / Vue 3.6 RC）

Backend
  Python 3.14.7
  Django 5.2.17 LTS
  uv 0.12.5
  其余当前 stable

Infrastructure
  PostgreSQL 18.4
  Redis 8.2.x
  Debian 13

Judge
  Temurin 25.0.4 LTS
  Node 24
  Go 1.26.7
  GCC 14
```

这里特别没有为了“较新”选择：

* Node 26 Current
* pnpm 12 RC
* Vue 3.6 RC
* Vitest 5 RC
* Go 1.27.0

因为“较新但可控”仍然意味着：

> **只采用已经 stable/GA/LTS 且已有足够生态验证的版本。**

---

# 十九、本仓库最终建议采用哪套

## 最终建议：保守组合为主体，但 Redis 直接规划到 8.2

即：

### frontend

**Node 24 + pnpm 11 + Vite 8.2 + Vue 3.5**

### backend

**Python 3.13 + Django 5.2 LTS + uv**

### database

**PostgreSQL 17**

### Redis

**Redis 8.2，独立迁移、独立回滚、先完成许可确认**

若组织政策明确不接受 Redis 8 的 AGPL/RSAL/SSPL模型，则建立独立决策：

**Valkey 8.1.9**

而不是偷偷在框架升级过程中切换。

### OS

**Debian 13 / Trixie**

### Judge

**Temurin 21 + Node24 + Go1.26 + GCC14**

---

## 为什么这套最适合 xju-OJ

这个仓库真正的问题不是版本落后本身，而是：

> **多个长期没有升级的子系统现在同时处于跨代点。**

例如：

* Vue2 → Vue3
* Webpack3 → Vite8
* Yarn → pnpm
* Django3.2 → Django5.2
* pip requirements → uv
* PostgreSQL10 → PostgreSQL17
* Redis4 → Redis8
* psycopg2 → psycopg3
* Dramatiq1 → Dramatiq2
* Judge toolchain → 新 Debian/toolchain。

在这种情况下，“每个组件取最长 EOL”并不是最低风险方案。

真正降低长期维护成本的方法是：

> **选择足够新的稳定基线，同时严格拆分升级的 rollback domain。**

Node 24、Python 3.13、Django5.2、PostgreSQL17、Temurin21 都符合这一原则。

它们不是最激进的版本，但在 2026-08-20 都有充分剩余生命周期。

---

# 二十、官方来源清单

以下均访问于 **2026-08-20**。

### 仓库

[xju-OJ 固定提交](https://github.com/xjuIcthub/xju-OJ/commit/2d84d089bcd8ea90d5836c00d7c46e6de47697fc?utm_source=chatgpt.com)

### Node.js

[Node.js Release Working Group](https://github.com/nodejs/Release?utm_source=chatgpt.com)
[Node.js canonical schedule.json](https://github.com/nodejs/Release/blob/main/schedule.json?utm_source=chatgpt.com)

### pnpm

[pnpm npm package / release tags](https://www.npmjs.com/package/pnpm?utm_source=chatgpt.com)

### Vite

[Vite Supported Versions / Release Policy](https://v8.vite.dev/releases?utm_source=chatgpt.com)
[Vite 8 Announcement / Node Requirements](https://vite.dev/blog/announcing-vite8?utm_source=chatgpt.com)

### Vue

[Vue Release Policy](https://vuejs.org/about/releases?utm_source=chatgpt.com)
[Vue npm package](https://www.npmjs.com/package/vue?utm_source=chatgpt.com)

### Vue Router / Pinia

[Vue Router npm package](https://www.npmjs.com/package/vue-router?utm_source=chatgpt.com)
[Pinia npm package](https://www.npmjs.com/package/pinia?utm_source=chatgpt.com)

### Python

[Python active release lifecycle](https://www.python.org/downloads/?utm_source=chatgpt.com)
[Python 3.13.15](https://www.python.org/downloads/release/python-31315/?utm_source=chatgpt.com)
[Python 3.14.7](https://www.python.org/downloads/release/python-3147/?utm_source=chatgpt.com)

### Django

[Django Supported Versions / Downloads](https://www.djangoproject.com/download/?utm_source=chatgpt.com)
[Django 5.2 Release Notes](https://docs.djangoproject.com/en/dev/releases/5.2/?utm_source=chatgpt.com)
[Django Python Compatibility Matrix](https://docs.djangoproject.com/en/dev/faq/install/?utm_source=chatgpt.com)
[Django 2026 Release Policy Announcement](https://www.djangoproject.com/weblog/2026/aug/10/annual-release-cycle/?utm_source=chatgpt.com)

### DRF

[DRF current compatibility requirements](https://www.django-rest-framework.org/?utm_source=chatgpt.com)
[DRF release notes](https://www.django-rest-framework.org/community/release-notes/?utm_source=chatgpt.com)

### uv

[uv Docker production guidance](https://docs.astral.sh/uv/guides/integration/docker/?utm_source=chatgpt.com)
[uv Installation / version pinning](https://docs.astral.sh/uv/getting-started/installation/?utm_source=chatgpt.com)

### Python backend ecosystem

[Gunicorn PyPI](https://pypi.org/project/gunicorn/?utm_source=chatgpt.com)
[Dramatiq PyPI](https://pypi.org/project/dramatiq/?utm_source=chatgpt.com)
[django-dramatiq PyPI](https://pypi.org/project/django-dramatiq/?utm_source=chatgpt.com)
[django-redis PyPI](https://pypi.org/project/django-redis/?utm_source=chatgpt.com)
[redis-py PyPI](https://pypi.org/project/redis/?utm_source=chatgpt.com)
[Psycopg 3 PyPI](https://pypi.org/project/psycopg/?utm_source=chatgpt.com)

### PostgreSQL

[PostgreSQL Versioning Policy](https://www.postgresql.org/support/versioning/?utm_source=chatgpt.com)
[PostgreSQL Release Notes](https://www.postgresql.org/docs/release/?utm_source=chatgpt.com)

### Redis

[Redis Open Source Version Management](https://redis.io/docs/latest/operate/oss_and_stack/install/version-mgmt/?utm_source=chatgpt.com)
[Redis Licensing](https://redis.io/legal/licenses/?utm_source=chatgpt.com)

### Valkey

[Valkey Release and Support Policy](https://valkey.io/topics/releases/?utm_source=chatgpt.com)
[Valkey Releases](https://valkey.io/download/releases/?utm_source=chatgpt.com)
[Redis → Valkey Migration Compatibility](https://valkey.io/topics/migration/?utm_source=chatgpt.com)

### Debian

[Debian LTS Schedule](https://wiki.debian.org/LTS?utm_source=chatgpt.com)
[Debian Releases](https://www.debian.org/releases/?utm_source=chatgpt.com)

### nginx

[nginx official downloads / stable-mainline channels](https://nginx.org/en/download.html?utm_source=chatgpt.com)

### Temurin

[Eclipse Temurin Support Roadmap](https://adoptium.net/support/?utm_source=chatgpt.com)

### GCC

[GCC Supported Releases](https://gcc.gnu.org/?utm_source=chatgpt.com)
[GCC Release History](https://gcc.gnu.org/releases.html?utm_source=chatgpt.com)

---

## 最终架构基线

**xju-OJ 2026 Production Baseline**

> **Node 24 LTS / pnpm 11 / Vite 8.2 / Vue 3.5**
> **Python 3.13 / Django 5.2 LTS / uv**
> **PostgreSQL 17 / Redis 8.2 / Debian 13**
> **nginx stable / Temurin 21 LTS / Go 1.26 / GCC 14**

同时把以下版本放入 CI compatibility matrix，而不是立即作为生产默认：

> **Node 26、Python 3.14、PostgreSQL 18、Temurin 25、Go 1.27**

而以下版本在 2026-08-20 应明确排除生产基线：

> **pnpm 12 RC、Vue 3.6 RC、Vitest 5 RC、Redis 8.0。**
