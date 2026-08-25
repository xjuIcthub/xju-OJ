# xju-OJ 数据基础设施现代化专项调研报告：PostgreSQL 10 / Redis 4 升级方案

**研究基线**

* 仓库：`xjuIcthub/xju-OJ`
* 分支：`main`
* 固定提交：`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`
* 调研截点：**2026-08-20**
* 范围：PostgreSQL、Redis、Dramatiq 队列与数据迁移；不修改代码，不创建 PR。
* 访问日期：本报告外部来源均于 **2026-08-20** 核验。

---

## 一、执行摘要

### 1. 推荐结论

| 项目                | 推荐                                                 |
| ----------------- | -------------------------------------------------- |
| PostgreSQL 最终目标   | **PostgreSQL 18.6**                                |
| PostgreSQL 保守回退候选 | **PostgreSQL 17.11**                               |
| PostgreSQL 首选迁移方式 | **`pg_dump` / `pg_restore` 到全新 PG18 集群**           |
| Redis 最终目标        | **Redis 8.2.8**                                    |
| Redis 关键中间落点      | **Redis 7.4.10**；必要时先经 **6.2.23**                  |
| Valkey            | **本次不切换产品**                                        |
| Redis 队列原则        | **先停止生产者 → drain → 优雅停 Worker → 业务级核账 → 再迁 Redis** |
| PostgreSQL/应用顺序   | **应用兼容准备 → 数据基础设施升级 → 最终 Django/框架主升级**            |
| 回滚原则              | **切回保留的旧集群/旧 volume；绝不尝试让新主版本数据目录“降级”运行**          |

PostgreSQL 18 截止本报告日期当前维护版本为 **18.6**，于 2025-09-25 首发，官方支持到 **2030-11-14**；17 当前为 **17.11**，支持到 **2029-11-08**。2026-08-13 官方刚发布 18.6/17.11；18.5 因回归问题没有正式发布。18 已有约 11 个月生产成熟期，同时比 17 多约一年生命周期，因此本项目长期目标优先选 **18.6**；若 staging 出现 PG18 特有阻塞，再退到 17.11。

Redis 不建议因为“最新版”直接选当前 Standard 分支。官方生命周期定义中 **8.2 是 Extended、GA，支持到 2030-09-01**；7.4 也是 Extended、GA，支持到 2029-12-01。因此最终推荐 **Redis 8.2.8**，但 Redis 4 不应直接跨到 8：官方 Redis 8 standalone 升级指南列出的来源是 Redis OSS **7.x → 8**，没有把 Redis 4 → 8 列为受支持升级路径。生产应分阶段验证，7.4.10 是重要的稳定落点。

### 2. “先应用还是先数据库”的明确答案

**不能先把 Django 完整升级到 2026 目标版再继续使用 PostgreSQL 10。**

原因是当前支持中的 Django 版本已经要求更高 PostgreSQL 基线；例如 Django 5.2 支持 PostgreSQL 14+，而 PostgreSQL 10 已于 2022-11-10 EOL。当前仓库 Django 3.2 虽能连接老 PostgreSQL，却自身已经 EOL。因此不存在一个长期受支持的“新版 Django + PostgreSQL 10”过渡组合。

推荐顺序为：

**第一步：应用兼容性准备发布。** 不做 Django 主版本跃迁，不改数据库表名/migration 历史，只增加可观测性、队列核账、可切换连接配置并验证新客户端兼容性。

**第二步：独立升级 Redis，再独立升级 PostgreSQL。** 每种数据服务拥有自己的回滚点，Redis 与 PostgreSQL 不在同一停机窗口大爆炸式升级。

**第三步：数据库稳定后，再完成 Django/psycopg/uv 等最终框架主升级。**

换句话说：

> **不是“完整应用先升级”，而是“兼容准备代码先发布，数据服务随后升级，框架主升级最后完成”。**

---

# 二、当前仓库事实

## 2.1 已核实事实

固定提交确实存在，SHA 为 `2d84d089...`。根目录包含 frontend、backend、server 和旧根 `docker-compose.yml`。

当前根 Compose 明确使用：

* `redis:4.0-alpine`
* `postgres:10-alpine`
* `./data/redis:/data`
* `./data/postgres:/var/lib/postgresql/data`
* backend/judge 仍引用旧远程 `1.6.1` 镜像。

backend 当前固定：

* Django 3.2.25
* redis-py 4.6.0
* django-redis 5.4.0
* Dramatiq 1.16.0
* django-dramatiq 0.11.6
* psycopg2 2.9.9。

当前 backend 镜像已经使用 Python 3.12，因此后续对较新 redis-py/Dramatiq 的 Python 运行时要求并不是根本阻塞项。

### PostgreSQL

生产配置使用 Django PostgreSQL backend；数据库 host、port、name、user、password 均来自环境变量。

仓库 migration 树从 2017 年开始并持续存在，符合“不得重写历史 migration”的兼容约束。

仓库仍通过 `django.contrib.postgres.fields.JSONField` 暴露 JSONField；题目和提交模型大量使用它，例如：

* `samples`
* `test_case_score`
* `languages`
* `template`
* `io_mode`
* `statistic_info`
* Submission `info`

并显式保留 `db_table`。

### Redis DB 1

Django cache 明确连接 Redis **DB 1**，Session 使用 cache backend：

```text
SESSION_ENGINE = django.contrib.sessions.backends.cache
SESSION_CACHE_ALIAS = default
```

因此用户 Session 与普通 cache 共处 DB 1。

更重要的是，`waiting_queue` 也在 DB 1。仓库判题逻辑为：

* 没有可用 JudgeServer：`LPUSH waiting_queue`
* 某次判题结束：`RPOP waiting_queue`
* 解 JSON
* 调用 `judge_task.send(...)` 投递到 Dramatiq。

因此：

> **绝不能为了“允许 Session 失效”直接 `FLUSHDB 1`。**

Session 可以作为业务决策主动失效，但 `waiting_queue` 是待判任务，不可随 Session/cache 一并丢弃。

此外，当前实现存在一个本来就存在的业务原子性窗口：

```text
RPOP waiting_queue
        ↓
judge_task.send(...)
```

若进程在两者之间退出，该任务可能已经从 DB 1 删除、却尚未进入 DB 4。

所以 Redis 数据迁移更不能采用“逐条 RPOP 后发到新 Redis”这种人工搬运方案。

### Redis DB 4 / Dramatiq

Dramatiq broker 和 result backend 均明确使用 Redis **DB 4**，且 result `result_ttl=None`。

当前判题 actor 使用：

* `max_retries=0`
* `time_limit=3600000ms`
* `max_age=7200000ms`。

Dramatiq 1.16 Redis broker 的实际结构包括：

* `dramatiq:<queue>`：待消费 message ID list
* `dramatiq:<queue>.msgs`：message 数据 hash
* `dramatiq:__acks__.<worker>.<queue>`：已取出、尚未 ACK 的 message ID
* heartbeat
* delay queue
* dead-letter queue。

1.16 的 broker 在正常 ACK 时才删除 message；Worker shutdown 时可以把已经 fetch、尚未完成的消息重新放回队列。

这说明 Dramatiq 是**至少一次语义风险模型**，而不是可以由 Redis snapshot 自动保证的业务 exactly-once。

---

# 三、官方支持与版本矩阵

## 3.1 PostgreSQL

| 版本            | 截止 2026-08-20 状态 |  当前 patch | 首发         | 官方支持结束         | 官方镜像             | 本项目判断  |
| ------------- | ---------------- | --------: | ---------- | -------------- | ---------------- | ------ |
| PostgreSQL 10 | EOL              |     10.23 | 2017-10-05 | **2022-11-10** | 历史镜像             | 必须退出   |
| PostgreSQL 17 | Supported        | **17.11** | 2024-09-26 | **2029-11-08** | `17.11-bookworm` | 最保守候选  |
| PostgreSQL 18 | Supported        |  **18.6** | 2025-09-25 | **2030-11-14** | `18.6-bookworm`  | **推荐** |
| PostgreSQL 19 | Beta             |    Beta 3 | —          | —              | 非生产目标            | 不采用    |

版本生命周期：
2026-08-13 更新公告：
官方 Docker 镜像标签：

**访问日期：2026-08-20。**

### 为什么选 18 而不是 17

17 的成熟时间更长，因此如果本项目依赖某个对 PG18 尚未验证的扩展、驱动或操作系统 locale，它是合理的保守后备。

但本仓库没有发现必须将目标锁死在 17 的数据库扩展依赖；而 18：

* 已经进入第六个维护版本；
* 多一年官方支持；
* 18.6 是刚发布的安全/错误修复版本；
* PG19 此时仍是 Beta，不构成生产候选。

因此推荐 18.6，而不是为了“追最新”选择 19。

### PostgreSQL 18 Docker 特别注意

官方 PostgreSQL Docker 镜像从 **18+** 起调整了默认 `PGDATA`/volume 布局；旧版常见的 `/var/lib/postgresql/data` 不能无脑照搬到 18。新部署必须按 PG18 官方镜像规则重新建立 volume，并把 PG10 volume 完全保留。

---

## 3.2 Redis

Redis 官方并没有把所有长期维护版本称为 LTS；应使用官方 **Standard / Extended** 分类。

| 分支         | 官方发布类型       | 状态  | 截止日期           | 本报告 patch  | 判断            |
| ---------- | ------------ | --- | -------------- | ---------- | ------------- |
| Redis 4    | 已不受支持        | EOL | 已结束            | 4.0        | 必须退出          |
| Redis 6.2  | Extended     | GA  | **2027-04-01** | **6.2.23** | 迁移桥接候选        |
| Redis 7.4  | Extended     | GA  | **2029-12-01** | **7.4.10** | 强烈建议生产中间落点    |
| Redis 8.0  | Standard     | GA  | 2026-12-01     | —          | 生命周期太短，不选     |
| Redis 8.2  | **Extended** | GA  | **2030-09-01** | **8.2.8**  | **最终推荐**      |
| Redis 8.10 | Standard     | GA  | TBD            | —          | 太新且 EOL 未定，不选 |

官方 Docker 有 `8.2.8-bookworm`、`7.4.10-bookworm`、`6.2.23-bookworm` 等明确 patch 标签。

**访问日期：2026-08-20。**

### Redis 客户端兼容

当前仓库固定 redis-py **4.6.0**。维护者兼容矩阵显示：

* 4.5+ 面向 Redis 5–7.0；
* redis-py 5.x 扩展到 Redis 7.4；
* redis-py 6.x 面向 Redis 7.2 到当前 Redis；
* RESP3 是后来客户端新增能力，但 Redis 服务仍能使用 RESP2。

因此不能保持 redis-py 4.6 不动而直接声称 Redis 8 是经过支持的生产组合。

Dramatiq 1.18 的官方包定义允许 `redis>=2,<7`，并要求 Python >=3.9；本仓库 Python 3.12 满足后者。

这意味着 **Redis 8 前的 Python Redis 客户端/Dramatiq 兼容升级必须作为独立应用依赖发布完成并验收**，而不能和 Redis 服务切换塞进同一个不可回滚变更。

---

# 四、推荐目标及不选其他候选的原因

## 4.1 PostgreSQL：18.6

**架构建议：**

版本仍固定为 PostgreSQL 18.6，不使用 floating `postgres:18` 或 `latest`。

初始保守候选是 `postgres:18.6-bookworm`，用于减少跨 PG10→18 时 musl/glibc、locale/collation 与 native debugging 同时变化的变量。2026-08-25 发布扫描发现该锁定镜像含无法消除的 Debian Critical 项，因此最终 release base 改为固定 digest 的 `postgres:18.6-alpine`，并用 Go 1.26.5 重建、替换官方镜像中的 `gosu` 1.19。该选择不改变 PostgreSQL major/minor，但必须重新执行 fresh restore、collation、UTC 和应用连接验收，最终只消费派生镜像的 immutable digest。

### 不首选 PG17 的原因

17.11 很成熟，但支持窗口短一年。只在 staging 发现明确 PG18 blocker 时退回。

### 不选 PG19 Beta

2026-08-20 PG19 仍处 Beta，不能作为长期生产基线。

---

## 4.2 Redis：最终 8.2.8

最终版本固定为 Redis 8.2.8。2026-08-25 发布扫描后，最终运行镜像从 Bookworm 变体改为 Critical=0 的固定 digest `redis:8.2.8-alpine`；此前已验证的 6.2/7.4 阶梯和 DB1/DB4 ledger 要求不变。

生产迁移不是：

```text
4 → 8.2
```

而是经过实测的阶梯。

**推荐逻辑路径：**

```text
Redis 4
  ↓
6.2.23（必要桥接）
  ↓
7.4.10
  ↓
独立升级 redis-py / Dramatiq
  ↓
8.2.8
```

每一箭头都必须在 staging 用**真实生产 snapshot clone**验证。

官方 Redis 8 standalone 升级文档明确描述 7.x → 8，而没有给 Redis 4 → 8 的直接支持承诺。

因此本报告**不能把 Redis 4 RDB/AOF 能否由 6.2/7.4/8.2 无损直接加载当作已核实事实**。这必须成为 staging stop gate。

---

## 4.3 Redis 8 与 Valkey

Redis 许可变化：

* Redis ≤7.2：BSD-3-Clause；
* Redis 7.4：RSALv2 / SSPLv1；
* Redis ≥8：增加 AGPLv3，形成多许可模式。

Valkey 官方迁移资料说明：

* Redis OSS 2.x–7.2 与 Valkey 7.2+ 在协议及 RDB/AOF 方面具有迁移兼容性；
* Redis 7.4+ 生成的磁盘数据文件不属于同样兼容范围。

**结论：本次不切 Valkey。**

Valkey 本身是合理的未来替代产品，但这次已经同时涉及：

* Django；
* PostgreSQL 八个主版本跨度；
* Redis 多代跨度；
* Dramatiq；
* Docker/deploy；
* JudgeServer。

此时更换 Redis 产品没有足够收益抵消额外回滚和运维变量。

如果未来因治理/许可单独评估 Valkey，应作为独立项目进行。特别是如果希望利用官方磁盘格式兼容路径，决策最好发生在跨过 Redis 7.4 之前，而不是把产品替换夹在当前框架升级中。

---

# 五、PostgreSQL 10 → 18 的迁移方法比较

## 5.1 PG10 能否直接 `pg_upgrade` 到 PG18？

**能。**

PostgreSQL 18 官方 `pg_upgrade` 文档明确支持从 **9.2+** 升到当前版本，因此技术上允许：

```text
10 → 18
```

不要求：

```text
10 → 11 → 12 → ... → 18
```

但 PostgreSQL 官方同时明确要求跨多个主版本时阅读所有中间版本迁移说明。外部模块、二进制对象、初始化参数、checksum 等也必须满足 `pg_upgrade` 条件。

所以：

> **“允许直接 pg_upgrade”不等于“本项目应该首选 pg_upgrade”。**

---

## 5.2 三种方案

| 方法                   | 停机 | 回滚              | 跨 10→18 风险             | OJ 适用性          |
| -------------------- | -- | --------------- | ---------------------- | --------------- |
| `pg_dump/pg_restore` | 较长 | **最好**          | 最低、最透明                 | **首选**          |
| `pg_upgrade`         | 较短 | copy/clone 模式尚可 | 跨八主版本排查复杂              | restore 超窗时第二选择 |
| 逻辑复制                 | 最短 | 复杂              | schema/sequence/DDL 另管 | 只有极低停机 SLO 才值得  |

### 首选 `pg_dump` / `pg_restore`

原因：

1. PG10 原集群完全不修改；
2. PG18 使用全新初始化的数据目录；
3. 表和索引在 PG18 重新构建；
4. 能直接获得 PG18 新集群默认 checksum 等现代初始化能力；
5. 回滚最简单；
6. 对 OJ 这类通常不是 TB 级的单数据库系统，复杂度比逻辑复制低很多。

PG18 当前 dump 工具可以读取 9.2+ server，因此可以用新工具从 PG10 逻辑导出。

推荐 directory 格式：

```bash
pg_dump -Fd -j <N>
pg_restore -j <N>
```

以利用并行 dump/restore。

### `pg_upgrade`

若两次 staging 实测证明 dump/restore 明显超过允许停机窗口，再评估。

必须先：

```bash
pg_upgrade --check
```

若使用，优先 default copy 或文件系统支持时 `--clone`。

**不推荐 `--link` / `--swap` 作为本项目默认生产方案**：一旦新集群启动或目录发生 destructive swap，旧集群简单回滚能力明显下降。官方也专门说明这些模式的回退限制。

另外 PG18 默认启用 data checksum，而 `pg_upgrade` 要求旧/新 checksum 配置兼容。如果 PG10 当前没有 checksum，就会削弱使用 PG18 新默认能力的便利性。

### 逻辑复制

只在业务停机 SLO 确实要求秒级切换且 restore 无法满足时使用。

官方限制包括：

* schema/DDL 不由逻辑复制解决；
* sequence state 不会自动同步；
* cutover 前要单独处理 sequence。

对本项目，逻辑复制增加的操作复杂度没有明显必要。

---

# 六、为什么不能复用 PostgreSQL 10 data directory

PostgreSQL 官方版本策略明确：

> 主版本会改变内部存储格式，数据目录并不保证主版本间兼容；主版本升级需要 dump/reload、`pg_upgrade` 或复制方法。

因此禁止：

```text
postgres:18
    +
./data/postgres(PG10) → PG18 data directory
```

生产设计必须是：

```text
PG10 volume ───── 保持不变
       │
       │ dump
       ▼
backup/
       │
       │ restore
       ▼
PG18 fresh volume
```

切换失败直接重新启动 PG10 volume，而不是尝试将 PG18 的目录交给 PostgreSQL 10。

---

# 七、迁移前数据清单和 PostgreSQL 校验

## 7.1 环境清单

迁移前保存以下输出：

```sql
SELECT version();
SHOW server_encoding;
SHOW TimeZone;
SHOW lc_collate;
SHOW lc_ctype;
SHOW data_checksums;

SELECT current_database(), pg_database_size(current_database());

SELECT datname,
       pg_encoding_to_char(encoding),
       datcollate,
       datctype
FROM pg_database
ORDER BY datname;

SELECT extname, extversion
FROM pg_extension
ORDER BY extname;
```

当前 Django 明确配置 `TIME_ZONE='UTC'`、`USE_TZ=True`；PG18 恢复后应用连接必须继续验证 UTC 语义。

## 7.2 migration 历史

```sql
SELECT app, name, applied
FROM django_migrations
ORDER BY app, name;
```

迁移前后必须完全一致。

数据库基础设施升级本身**不得删除、重写或 fake 2017 年以来 migration 历史**。

## 7.3 JSONB

先建立 JSONB column inventory：

```sql
SELECT n.nspname,
       c.relname,
       a.attname,
       format_type(a.atttypid, a.atttypmod)
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE a.attnum > 0
  AND NOT a.attisdropped
  AND a.atttypid = 'jsonb'::regtype
ORDER BY 1,2,3;
```

验收不能比较 JSON 文本序列，因为 JSONB key 顺序不具有业务语义。

应比较：

* NULL 数量；
* `jsonb_typeof()` 分布；
* 每个关键表随机/固定 PK 样本的 JSONB 等值；
* Problem/Submission/API 返回语义；
* JSONB 相关 index 是否成功重建。

## 7.4 索引和 constraint

迁移前后：

```sql
SELECT n.nspname, c.relname
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT i.indisvalid
   OR NOT i.indisready;
```

目标必须为 **0 行**。

```sql
SELECT conrelid::regclass, conname, contype
FROM pg_constraint
WHERE NOT convalidated;
```

除明确已有历史例外外也应为 0。

## 7.5 Sequence

`pg_restore` 能恢复 sequence value，但仍必须业务核验。

对每个序列记录：

* sequence 名；
* owned table/column；
* `last_value`;
* `is_called`;
* 对应 numeric PK 最大值。

恢复后必须保证 next value 不落后于表实际最大 ID。

## 7.6 Collation

记录：

* cluster/database locale；
* OS/libc；
* PostgreSQL collation version；
* 所有依赖非默认 collation 的 index。

PostgreSQL 官方明确警告 collation version 不一致可能使依赖排序规则的索引失效；需要重建受影响对象，再 refresh collation version，而不能只执行 refresh。

dump/restore 会在目标系统重新构建索引，因此比原地 pg_upgrade 更适合本次大跨度升级，但任何 uniqueness/collation 错误都必须停止上线。

## 7.7 权限和 owner

普通 `pg_dump` 不包含整个 cluster 的 roles/tablespaces 等 global objects，所以必须另外保存：

```bash
pg_dumpall --globals-only
```

同时记录：

```sql
SELECT rolname,
       rolsuper,
       rolcreatedb,
       rolcreaterole,
       rolcanlogin,
       rolconfig
FROM pg_roles
ORDER BY rolname;
```

以及 database/schema/table/sequence owner 和 ACL。

---

# 八、Redis 4 → 8 数据、协议与持久化

## 8.1 RDB

Redis 官方说明 RDB 是 point-in-time snapshot；按 snapshot 周期可能丢失最近若干分钟数据。

因此对于 DB 4：

> **有一份 RDB 文件 ≠ 判题队列完整。**

## 8.2 AOF

`appendfsync everysec` 模式即使正常工作，也存在大约一秒量级未刷盘窗口。

切换前若使用 AOF，至少检查：

```text
aof_rewrite_in_progress = 0
aof_rewrite_scheduled   = 0
aof_last_bgrewrite_status = ok
```

Redis 7+ 还引入 multipart AOF，因此不能假定 Redis 4 的单文件 AOF 运维流程能原封不动复制到现代 Redis。

## 8.3 RESP

现代 Redis 同时支持 RESP2/RESP3，连接仍可以使用 RESP2。

本项目迁移期建议：

> **显式保持 RESP2，不在 Redis 服务升级的同时切 RESP3。**

协议升级属于另一个客户端行为变化，不应该进入同一回滚单元。

---

# 九、Redis 队列 drain 流程

这是整次迁移中最重要的业务安全环节。

## 9.1 第一步：关闭所有新任务生产者

先从入口层拒绝/冻结：

* 新 Submission；
* rejudge；
* admin 批量判题；
* contest 中可能提交判题的入口；
* 其他调用 `judge_task.send()` 的后台入口。

**不能先停 Worker。**

否则新任务仍会进入队列而无人处理。

## 9.2 第二步：自然 drain

保持：

* 旧 Redis；
* 旧 Dramatiq Worker；
* 旧 JudgeServer

继续工作。

等待以下三类状态同时清零。

### DB 1

```text
SELECT 1
LLEN waiting_queue
```

目标：

```text
0
```

### PostgreSQL

仓库 Submission 状态：

```sql
SELECT result, count(*)
FROM submission
GROUP BY result
ORDER BY result;

SELECT count(*)
FROM submission
WHERE result IN (6, 7);
```

其中：

```text
6 = PENDING
7 = JUDGING
```

理想 cutover 条件：

```text
PENDING = 0
JUDGING = 0
```

### DB 4 Dramatiq

检查实际发现的 `dramatiq:*`：

* ready queue；
* `.msgs`;
* delayed queue；
* ACK sets；
* dead-letter queue；
* heartbeat。

Dramatiq 1.16 的 qsize 内部会考虑普通 message、delay message 和 ACK 状态，因此不能只 `LLEN dramatiq:default`。

这些内部 key 是 **1.16 实现细节，只可作为迁移诊断工具，不应成为长期业务 API**。

## 9.3 第三步：优雅停止 Worker

队列达到 0 后：

1. 给 Worker 发正常 `SIGTERM`；
2. 等待正在执行的 actor 完成；
3. 不使用 `kill -9`；
4. 重新检查 DB4 ACK sets。

Dramatiq 的正常 shutdown 会重新排队 fetched-but-unprocessed 消息。

若 graceful shutdown 之后仍存在无法解释的 ACK：

**停止迁移。**

不要赌 Redis 重启后的维护逻辑最终会把它找回来。

## 9.4 第四步：业务 manifest

最终冻结时创建三份清单：

```text
PG:
submission_id + result(PENDING/JUDGING)

DB1:
waiting_queue 中每个 JSON
→ submission_id/problem_id

DB4:
每个未完成 Dramatiq message
→ message_id
→ actor
→ submission_id/problem_id
```

保存：

* 记录数；
* 内容；
* SHA-256。

目标不是“Redis 有多少个 key”，而是：

> **每一个还没有完成的 submission 是否都能解释。**

---

# 十、DB 1 Session 与 waiting_queue

## Session

由于 Django 使用 cache session，Redis DB1 丢失 Session 会导致用户重新登录。

对于计划停机升级：

**Session 主动失效通常可以接受，但必须作为明确业务决策，而不是数据迁移副作用。**

同时必须保持：

* Session cookie 机制；
* `csrftoken`;
* `X-CSRFToken`;
* 同源 `/api`。

### 严禁

```text
FLUSHDB 1
```

因为 `waiting_queue` 与 Session 同 DB。

若决定清 Session，只能在确认 `waiting_queue=0` 后，按**已验证的 Session key namespace**定向清理。

## waiting_queue 单独保护

迁移前：

```text
TYPE waiting_queue
LLEN waiting_queue
LRANGE waiting_queue 0 -1
```

冻结生产者后导出完整内容，解析所有 JSON，生成 submission ID manifest 和内容 hash。

如果队列不为 0，优先继续自然 drain。

只有业务明确允许携带未完成任务切换时，才允许 frozen-copy，并必须证明：

```text
old list count
=
export count
=
new list count
```

且顺序保持。

---

# 十一、DB 4 能否只靠 RDB/AOF？

**不能。**

原因至少有三层：

1. RDB 本身具有 snapshot 时间窗口；
2. AOF everysec 也可能失去最近约一秒；
3. 消息可能处于“Worker 已 fetch，但尚未 ACK”的状态。

因此：

> **Redis persistence 是灾难恢复介质，不是 OJ 判题业务 ledger。**

真正的 ledger 必须联合：

```text
PostgreSQL Submission 状态
+
DB1 waiting_queue
+
DB4 Dramatiq message/ack 状态
```

来核账。

特别是不能简单看到：

```text
DBSIZE(new) == DBSIZE(old)
```

就宣告成功。

---

# 十二、Redis 迁移前指标

DB 1、DB 4 均记录：

```text
INFO server
INFO persistence
INFO memory
INFO keyspace
DBSIZE

CONFIG GET save
CONFIG GET appendonly
CONFIG GET appendfsync
CONFIG GET dir
CONFIG GET dbfilename
```

若字段在 Redis 4 版本中不存在，应记录“不支持”，不能以新版本命令结果倒推旧集群。

生产 inventory 使用：

```text
SCAN
TYPE
LLEN
HLEN
SCARD
ZCARD
PTTL
```

不要在大 keyspace 直接：

```text
KEYS *
```

DB1 特别记录：

* key 总量；
* `waiting_queue` length；
* waiting_queue JSON manifest；
* Session key 数；
* cache key TTL 分布。

DB4 特别记录：

* broker namespace；
* queue 名；
* ready 数；
* `.msgs` 数；
* delayed 数；
* ACK 数；
* XQ/dead letter 数；
* result key 数；
* persistence 状态。

---

# 十三、Staging clone 演练流程

至少完成 **两次可重复演练**，才能生产执行。

### Phase 1：制作生产 clone

分别获取：

* PG10 logical dump；
* Redis4 RDB/AOF 或一致 snapshot；
* runtime 文件 snapshot。

staging 必须与生产网络隔离。

**尤其禁止 staging Dramatiq Worker/JudgeServer 连接生产 JudgeServer 或生产 Redis。**

### Phase 2：建立 pre-migration manifest

运行前述：

* PG schema/row/migration/JSON/index/sequence/ACL inventory；
* DB1 waiting_queue manifest；
* DB4 broker manifest；
* snapshot 文件 SHA-256。

### Phase 3：Redis ladder 演练

逐级验证：

```text
4 → 6.2.23
6.2.23 → 7.4.10
7.4.10 → 8.2.8
```

每一级都：

1. 新 volume；
2. 加载数据；
3. 服务启动；
4. 检查 persistence log；
5. 比较 key 数、type、TTL；
6. 比较 waiting_queue；
7. 比较 Dramatiq manifests；
8. SAVE；
9. 停机；
10. 再次启动验证。

**Redis 4 → 6.2 的实际 RDB/AOF 文件加载兼容性是本报告尚无法从当前官方升级指南直接证明的事项，因此是硬性 staging stop gate。**

若该步不能无损通过，改用经过验证的 Redis 数据导出/导入或额外中间版本，而不能生产冒险直跳。

### Phase 4：故障注入

至少模拟：

* Worker 已 fetch 尚未执行时 SIGTERM；
* Worker 执行过程中 Redis 重启；
* JudgeServer 临时不可用，产生 waiting_queue；
* waiting_queue 非空时停止新任务；
* Redis 切换前后 Worker 重启；
* old Worker 被意外启动。

验收必须证明不会出现静默任务丢失。

### Phase 5：PostgreSQL restore rehearsal

用 PG18.6 client：

1. globals dump；
2. directory dump；
3. 初始化 fresh PG18；
4. restore；
5. ANALYZE；
6. 数据和业务校验；
7. 完整应用 smoke。

记录：

```text
dump duration
dump size
restore duration
index build duration
ANALYZE duration
application validation duration
```

只有这些实测数字才能最终确定生产停机窗口。

---

# 十四、生产分阶段迁移路径

不建议把 Redis 与 PostgreSQL 放在一个周末一次完成。

## 阶段 A：兼容准备

保持 PG10/Redis4。

发布：

* 数据服务地址配置化；
* migration/queue inventory 工具；
* drain 开关；
* 监控；
* backup/restore runbook。

不得改变数据库历史语义。

## 阶段 B：Redis 桥接

独立维护窗口：

```text
Redis4 → 经 staging 证明可行的 bridge
```

优先最终达到：

```text
Redis7.4.10
```

保持 RESP2。

业务 soak 后再继续。

## 阶段 C：Redis 客户端/Dramatiq 准备

作为**普通应用依赖发布**单独完成。

不要同时升级 Redis server。

本仓库 Python 3.12 可以满足 Dramatiq 1.18 的 Python >=3.9 基线，而 Dramatiq 1.18 允许 redis-py <7。

具体 redis-py/Dramatiq 组合仍须以 staging broker/result 完整测试确定。

## 阶段 D：Redis 7.4 → 8.2.8

此步符合 Redis 官方 Redis 7.x→8 升级路径范围。

再次完整 drain。

Redis8 稳定后，不要马上迁 PostgreSQL。

## 阶段 E：PostgreSQL 10 → 18.6

独立维护窗口，通过 dump/restore 到 fresh PG18。

## 阶段 F：Django/psycopg 最终现代化

数据库稳定后，再升级最终受支持 Django、psycopg 及 uv dependency 管理。

该阶段可以生成新的 migration，但：

* 不改旧 migration；
* 不改 app label；
* 不改现有表名；
* JSONField 现代化不得借数据库搬迁重写历史。

---

# 十五、PostgreSQL 生产停机切换时间线

以下使用相对时间，真实时长由 staging rehearsal 决定。

### T-7 天以上

* 最终 staging rehearsal 成功；
* 真实 backup 已实际 restore；
* 18.6 镜像和 digest 冻结；
* disk capacity 验证；
* rollback runbook 走通。

### T-24h

* 禁止 schema migration；
* 禁止部署其他业务变更；
* 保存完整 PG/Redis baseline。

### T-60m

进入维护状态：

* 停新 Submission；
* 停 rejudge；
* 停其他异步 producer；
* 开始 drain 判题。

因为当前 actor time limit 可达一小时，不能假设 drain 几分钟完成。

### T0：Queue clean checkpoint

只有：

```text
DB1 waiting_queue = 0
PG PENDING/JUDGING = 0
DB4 ready/delayed/acks = 0
```

才继续。

随后：

1. SIGTERM Worker；
2. 重新确认 ACK=0；
3. 停 backend 写入口；
4. 确认 PostgreSQL 没有业务写连接。

### T+：最终 PG dump

执行 globals snapshot 和 final database directory dump。

对 dump 做 hash，保留日志。

### T+：创建 PG18 fresh cluster

使用全新 volume。

按 staging 验证过的：

* encoding；
* locale/collation；
* timezone；
* authentication；
* checksum

初始化。

### T+：Restore

1. 创建/恢复所需 roles；
2. 创建 database；
3. `pg_restore --exit-on-error -j N`；
4. `ANALYZE`；
5. schema/data 验证。

### Read-only acceptance gate

**这一步仍不开放外部写入。**

运行：

* Django system check；
* migration history；
* `/api` read smoke；
* `/admin/`；
* `/public/`；
* JSONB；
* index；
* sequence；
* ACL；
* timezone。

通过之后才允许进入新集群写入。

---

# 十六、PostgreSQL Restore 验收

必须全部满足：

### 数据

* 所有业务表存在；
* 关键表 row count 相同；
* `django_migrations` 完全一致；
* Submission 各 result count 一致；
* Problem/Contest/User/JudgeServer/config 数量一致。

### JSONB

固定样本和统计一致，API 反序列化正常。

### Sequence

所有 owned sequence 的 next value 均安全大于已有 ID。

### Index

invalid/unready = 0。

### Constraint

无新增 unvalidated constraint。

### Collation

无 unresolved collation mismatch。

### 时间

Django connection：

```sql
SHOW TimeZone;
```

符合 UTC 设计。

同时抽查历史 Submission/Contest timestamp 的 epoch 值，而非只比较本地化字符串。

### 权限

应用账户：

* 可以正常读写业务表；
* 可以使用需要的 sequence；
* 不能获得额外 superuser 权限。

### Database health

运行目标版本可用的 catalog/physical consistency 检查，并完成 `ANALYZE`。PostgreSQL 官方也建议 restore 后重建 optimizer statistics。

---

# 十七、Docker volume、bind mount 与备份布局

## 推荐

数据库数据与 application runtime 完全分离：

```text
runtime/
  backend/
    public/
    test_case/
    log/
    config/

volumes/
  postgres/
    10/
    18/
  redis/
    4/
    6.2/
    7.4/
    8.2/

backups/
  postgres/
    2026-xx-xx/
      globals.sql
      onlinejudge/
      manifest.sha256
  redis/
    2026-xx-xx/
      dump.rdb
      appendonly/
      inventory/
      manifest.sha256
```

目录名字只是建议；最终路径必须由部署配置参数化。

### 不允许

```text
postgres10-volume → postgres18
```

同一目录复用。

也不允许：

```text
redis4-data → redis8
```

直接覆盖式升级且删除旧副本。

### PG18 mount

按 PG18 官方镜像新的 data layout 建立独立 mount，不照搬当前：

```text
/var/lib/postgresql/data
```

的 PG10 Compose 写法。

### 权限

* database data directory：只允许对应 container database user；
* backup：0700 目录，dump 0600；
* secret：0600；
* 不应将 PostgreSQL/Redis production port 默认发布到公网；
* 不在 compose 中假设历史 host UID；
* deploy 校验阶段应针对实际 pinned image 检查容器用户 UID/GID。

---

# 十八、破坏性变更与高风险项

## P0：Redis old/new Worker 并行

最危险场景之一是：

```text
old Worker → old Redis
new Worker → new Redis
```

同时处理同一批逻辑 Submission。

这会造成重复判题以及 Problem/UserProfile/Contest 统计二次更新风险。

**任何时刻只能有一套 production Worker 获得消费权。**

## P0：waiting_queue 与 Session 共 DB1

不能通过 DB1 flush 达成 Session reset。

## P0：RDB/AOF 当作 queue truth

不成立。

必须 PG + DB1 + DB4 三方核账。

## P0：复用 PG10 data directory

禁止。

## P0：`pg_upgrade --link` 后尝试简单回滚

不作为默认方案。

## P1：Sequence 落后

会造成恢复后 PK 冲突。

## P1：Collation 改变

可能影响 index 顺序和 uniqueness。

## P1：Django 3.2 与 PG18 的临时过渡

当前 Django 3.2 已 EOL；现代受支持 Django 又不能留在 PG10，因此这里不存在完全受支持的双端 overlap。

必须把它视为**短暂、充分 staging 验证的迁移桥梁**，而不是长期生产架构。

## P1：Redis 服务和 Redis Python stack 同时跃迁

禁止。

先让客户端与当前/中间 Redis 兼容，再迁 server。

---

# 十九、测试和验收标准

## PostgreSQL

必须达到：

* schema object 数一致；
* migration history 一致；
* 关键表 count 一致；
* JSONB 语义一致；
* invalid index = 0；
* sequence 验证 100% 通过；
* owner/ACL 通过；
* UTC timestamp 通过；
* Django ORM CRUD 通过；
* restore rehearsal 至少两次可重复。

## Redis

必须达到：

* persistence 无错误；
* DB1 waiting_queue manifest 完全对应；
* Session preservation 或 intentional invalidation 有明确决策；
* DB4 unfinished message manifest 完全对应；
* 无 unexplained ACK；
* old/new worker 不并行；
* synthetic judge task 在故障测试中不静默丢失。

## OJ 业务兼容

数据迁移上线至少验证：

* 浏览器继续同源 `/api`；
* Session/csrftoken/X-CSRFToken；
* `/admin/` history；
* `/public/`;
* `{"error": ..., "data": ...}`；
* pagination；
* Django app label/table/migration；
* Redis DB1/DB4 边界；
* `/judge`；
* `/compile_spj`；
* heartbeat；
* JudgeServer token 摘要；
* Submission result/info/statistic_info；
* `/test_case` 继续只读给 JudgeServer；
* 不改变 Judger UID/GID/resource/seccomp 安全边界。

数据基础设施升级不应以“顺便修改接口”为条件。

---

# 二十、停止条件

命中任何一条，**停止生产切换并回到上一个稳定版本**：

1. `waiting_queue` 中存在无法解析或无法映射到 Submission 的记录。
2. drain 后仍有无法解释的 PENDING/JUDGING。
3. Dramatiq Worker 已优雅停止但 DB4 仍有 unexplained ACK。
4. old/new Worker 同时运行。
5. Redis RDB/AOF 在 staging 的 4→bridge 或7→8加载不完全成功。
6. Redis key type、queue count、manifest hash 出现无法解释差异。
7. Redis persistence 报错或 AOF rewrite 未完成。
8. PostgreSQL dump 有错误或 dump hash 不可验证。
9. PG18 restore 出现任何未评估 error。
10. `django_migrations` 不一致。
11. 关键表 row count 不一致。
12. JSONB semantic comparison 不一致。
13. sequence 比对应数据最大值落后。
14. 出现新增 invalid index。
15. collation warning 尚未查清。
16. owner/ACL 无法恢复。
17. timezone 行为改变。
18. staging 从未成功恢复真实 backup。
19. 磁盘不足以同时保留 old cluster、new cluster 和 backup。
20. 方案要求覆盖或删除唯一 PG10/Redis4 rollback volume。
21. 必须依赖 `pg_upgrade --link` 才能满足窗口，但没有独立 immutable backup。
22. 新数据库已经开放写入，却没有明确处理“如何把新写入同步回旧数据库”的 rollback 方案。
23. 任何判断只能依赖“Redis 启动成功”或“PostgreSQL 能连接”，而没有完成业务级核账。
24. 发现某次 Redis 操作可能造成待判任务静默丢失或重复投递，但无法列出准确 submission manifest。

其中 1、2、3、4、5、12、13、20、24 应视为**硬停止条件**，不接受带风险上线。

---

# 二十一、回滚原则与决策点

## 21.1 PostgreSQL

### 最佳 rollback checkpoint

PG18 restore 完成后，先保持应用 read-only。

此时若失败：

```text
停止 PG18
→ 将应用连接重新指向 PG10
→ 启动旧业务栈
```

旧 PG10 从未被新版本修改，因此回滚清晰。

### PG18 开始接受写入后

旧 PG10 会立即落后。

此后不能直接切回而声称“无数据损失”。

必须：

1. 再次关闭写入；
2. 盘点 PG18 上新产生的业务变更；
3. 将这些变更按业务级方案回灌旧系统，或从明确 backup point 恢复并接受经批准的数据窗口；
4. 才能重新启用 PG10。

因此正式开放 PG18 写入前必须设置一次严格的 **GO/NO-GO checkpoint**。

绝不能：

```text
PG18 data directory
→ PostgreSQL 10
```

做“降级”。

---

## 21.2 Redis

每次：

```text
4 → 6.2
6.2 → 7.4
7.4 → 8.2
```

都保留上一代 data volume 和 snapshot。

### 新 Worker 尚未开始消费

可直接停止新 Redis，恢复旧 Redis/Worker。

### 新 Worker 已开始处理任务

不能简单切 Redis endpoint。

必须重新：

* gate producers；
* drain/freeze；
* PG PENDING/JUDGING reconciliation；
* DB1 waiting reconciliation；
* DB4 message reconciliation。

否则会发生：

```text
旧队列重新出现
+
新队列已经执行过
=
重复判题
```

---

# 二十二、待本仓库实测的问题

以下不是已核实事实，必须在真实 staging 回答：

1. 生产 PG10 实际 database size、最大表、最大 index。
2. dump/restore 实际耗时是否满足停机 SLO。
3. PG10 当前是否启用 data checksum。
4. PG10 实际 locale/collation/provider。
5. 是否存在仓库代码之外安装的 PostgreSQL extension。
6. sequence/identity 的完整实际列表。
7. 是否存在手工创建的 index/trigger/function 未进入 migration。
8. PG18.6 + 当前 Django3.2/psycopg2 组合能否作为短期 migration canary 完整工作。
9. Redis4 实际启用 RDB、AOF 或两者。
10. Redis4 RDB/AOF 是否能够在指定 bridge 版本无损加载。
11. DB1 实际 Session key namespace。
12. DB1 waiting_queue 的峰值长度和实际最大 payload。
13. DB4 实际 Dramatiq queue 名称。
14. 是否存在除 `default` 外的 actor queue。
15. DB4 是否存在历史 DLQ。
16. result backend 永久结果实际数据量。
17. Worker graceful shutdown 在真实最长 JudgeServer 调用下需要多少时间。
18. 当前提交入口关闭后是否仍有 cron/admin/API 能产生 judge message。
19. waiting_queue `RPOP → send` 原有非原子窗口是否曾产生线上孤儿 Submission。
20. 是否存在 PENDING/JUDGING 长期脏数据，需要迁移前先清账。
21. Redis-py/Dramatiq 的最终 Redis8 组合需选择并锁定准确版本，不能只写宽范围。
22. 官方 PG18 Docker 新 volume layout 在目标宿主机 backup/restore 工具链中的实际路径和 UID/GID。
23. 恢复后 collation 变更是否会改变任何业务 uniqueness/order 行为。

这些问题没有完成验证前，不能把本报告直接视为 production execution authorization。

---

# 二十三、最终推荐的执行路线

```text
固定基线
  │
  ▼
应用兼容/观测/队列核账准备
  │
  ├── 不升级 Django 主版本
  ├── 不改表名
  └── 不改历史 migration
  │
  ▼
Redis 4
  │
  ▼
经 staging 验证的 bridge
  │
  ▼
Redis 7.4.10
  │
  ▼
独立 Redis client / Dramatiq 兼容发布
  │
  ▼
Redis 8.2.8
  │
  ▼
生产 soak + queue correctness 验收
  │
  ▼
PG10 write freeze
  │
  ▼
pg_dump / pg_restore
  │
  ▼
全新 PostgreSQL 18.6
  │
  ▼
Read-only GO/NO-GO
  │
  ▼
开放业务
  │
  ▼
稳定观察
  │
  ▼
再完成 Django / psycopg / uv 等框架现代化
```

**禁止：**

```text
Django 主升级
+ PG10→18
+ Redis4→8
+ Dramatiq 主升级
+ Docker 重构
+ deploy.sh 重构
```

在同一个不可回滚生产提交/窗口完成。

---

# 二十四、官方来源清单

以下均于 **2026-08-20** 访问。

### PostgreSQL

* PostgreSQL Versioning Policy：包含各主版本首发日期、当前 patch、支持状态和 EOL，以及主版本 data directory 不兼容原则。[PostgreSQL Versioning Policy](https://www.postgresql.org/support/versioning/)
* PostgreSQL 2026-08-13 minor release 公告：18.6/17.11，并说明 18.5 因 regression 未发布。
* PostgreSQL 18 Upgrading a PostgreSQL Cluster：dump/restore、pg_upgrade、replication 和 major-version 数据兼容原则。
* PostgreSQL 18 `pg_upgrade`：支持从 PostgreSQL 9.2+ 升到当前版本，包含 `--check`、copy/link/clone/swap。
* PostgreSQL Logical Replication restrictions：DDL/schema 与 sequence 限制。
* PostgreSQL `pg_dumpall`：global objects/roles/tablespaces。
* PostgreSQL `pg_dump`/`pg_restore`：directory format、parallel dump/restore、sequence 和 ANALYZE。
* PostgreSQL collation version：collation mismatch 后的 REINDEX/REFRESH 要求。
* PostgreSQL 18 initdb/upgrade changes：data checksum 默认和升级要求。
* Docker Official Image `postgres`：17.11/18.6 镜像与 PG18 data-directory layout。

### Redis

* Redis Software Version Management：Standard/Extended、GA、EOL。
* Redis 8 standalone upgrade guide：官方支持来源路径和 SAVE/data directory 升级步骤。
* Redis persistence：RDB/AOF durability。
* Redis RESP protocol：RESP2/RESP3。
* Redis licensing：7.4 与 Redis 8 licensing。
* Redis release/download 与 Docker image：6.2.23、7.4.10、8.2.8。
* redis-py 维护者兼容矩阵：redis-py major 与 Redis server/Python 版本关系。

### Dramatiq

* 本仓库固定 Dramatiq 1.16.0。
* Dramatiq 1.16 RedisBroker 和 consumer ACK/requeue 实现。
* Dramatiq 1.16 Redis Lua broker 数据结构和 ACK/requeue/qsize 语义。
* Dramatiq 1.18 package compatibility：Python >=3.9、redis-py `<7.0`。

### Valkey

* Valkey 官方 Redis→Valkey migration compatibility：Redis OSS 至 7.2 的协议/RDB/AOF 兼容及 Redis 7.4+ 磁盘格式边界。

---

## 最终决策

**PostgreSQL：选 18.6；17.11 仅作为 staging 发现 PG18 blocker 后的保守备选。**

**Redis：最终选 8.2.8；以 7.4.10 作为关键生产过渡/稳定落点，不直接 Redis4→8。**

**PostgreSQL 10→18：技术上允许直接 `pg_upgrade`，但本 OJ 首选 fresh PG18 + `pg_dump/pg_restore`，因为它提供最清晰的验证和回滚边界。**

**应用与数据升级顺序：兼容准备发布在前，数据库服务升级居中，Django 等最终框架主升级在后。**

**任何 Redis 切换必须把 PostgreSQL Submission、DB1 waiting_queue 与 DB4 Dramatiq 三者联合当作判题任务 ledger；仅凭 RDB/AOF 不足以证明“没有丢任务或重复判题”。**

**生产回滚永远回到保留的旧 PostgreSQL/Redis 集群和旧 volume；绝不尝试降级 PG18/Redis8 已写入的数据目录。**
