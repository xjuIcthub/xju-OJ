# 2026 现代化迁移执行记录

> 此文件只记录已经实际执行并验证的事实；计划文本、预估结果和“应当通过”不能写成完成事实。

## 全局信息

- 生产宿主：Ubuntu >=22.04；Step 00 实测目标为 Ubuntu 22.04，支持状态仍由 Step 03 preflight 再验收
- Python：3.10.x，Step 00 锁定官方 amd64 基础镜像解释器 `3.10.21` 与 manifest digest
- 当前分支：`main`
- 计划入口：[README.md](README.md)
- 当前 Step：Step 00 已完成，准备 Step 01
- 最近完成 Step：Step 00

## 记录格式

每完成一个 Step，追加一条：

```text
### YYYY-MM-DD — Step NN

- Commit:
- 变更摘要:
- 实际命令:
- 测试/验收结果:
- 镜像与 digest:
- 数据/Redis/queue 证据:
- 已知风险:
- 回滚点:
- 下一步:
```

## 禁止记录

- Secret、密码、Token、私钥、Cookie、Authorization header。
- 完整生产数据库 dump、Redis RDB/AOF、用户上传文件或判题运行数据。
- 未执行的命令结果、未验证的版本或推测性的“已完成”。

### 2026-08-23 — Step 00

- Commit: 本条记录随 `step 00: lock modernization decisions` 独立提交
- 变更摘要: 新增 `docs/contracts/modernization-version-lock.md` 与 `docs/contracts/modernization-compatibility.md`；锁定平台、版本、镜像 digest、兼容合同和停止门。
- 实际命令: 本地核验 `git rev-parse HEAD`、`git status --short --branch`、源依赖声明和当前工具版本；在配置目标 `huawei1` 执行计划中的宿主/容器工具查询；通过 Docker Official Image 元数据和 `docker run` 核验 `python:3.10-slim-bookworm@sha256:7ed92b32353e8d8bd865b5ba811e0315d3999c3b57b1c2df2b504a359d4a1707` 的 amd64 Python `3.10.21`；通过 npm/PyPI 包元数据核验 pnpm 11.22.0、Vite bridge/final、Vue bridge/final、uv 0.12.5 和 Django 5.2.17 候选。
- 测试/验收结果: `huawei1` 为 Ubuntu 22.04、x86_64、cgroup v2、Docker 29.7.1、Compose v5.4.0、Buildx v0.36.0；版本锁已解释 pnpm 11.21/11.22、PG17/18、Redis/Valkey 和 Python 3.10/3.13 冲突；未修改应用代码、旧锁文件或运行数据。
- 镜像与 digest: Python amd64 manifest `sha256:7ed92b32353e8d8bd865b5ba811e0315d3999c3b57b1c2df2b504a359d4a1707`; Node 24.19.0、PostgreSQL 18.6/17.11、Redis 6.2.23/7.4.10/8.2.8、Debian Trixie 的 manifest digest 记录在版本锁中。
- 数据/Redis/queue 证据: 本 Step 未触碰 PostgreSQL、Redis、queue、Secret 或用户数据。
- 已知风险: 当前宿主 Node/pnpm/uv 仍为旧工具版本；Step 03 必须重新执行 Ubuntu/runtime-root/权限/工具链门，后续镜像构建必须使用锁定 digest。
- 回滚点: `d59d274ce3237bb10165fc9afadc4260aa79c359`；本 Step 仅新增文档，错误时回到该提交即可。
- 下一步: Step 01 — 行为合同与特征测试。

### 2026-08-23 — Step 01

- Commit: 本条记录随 `step 01: characterize compatibility contracts` 独立提交
- 变更摘要: 新增 API/Session/CSRF、路由、数据身份、Judge 协议 golden；新增 Django、frontend 路由、Judge transport 的可重复特征测试和隔离 schema/Redis/migration 快照。
- 实际命令: 在临时 PostgreSQL 10/Redis 4 容器与临时 runtime root 中执行 `python manage.py check`、`showmigrations --plan`、`makemigrations --check --dry-run`、`test`；执行标记的 `tests.contracts` 两次；执行 frontend route manifest 两次；执行 Judge protocol unittest 两次；通过临时 Nginx gateway 用 curl/Playwright 核验 `/admin`、SPA deep link、`/public`、`/api/website/` 和响应边界。
- 测试/验收结果: 标记的 backend 合同套件 `7 tests` 两次通过；Judge transport 套件 `4 tests` 两次通过；frontend 静态路由合同和 gateway HTTP 合同通过；未标记的旧 `python manage.py test` 实际为 `0 tests`，并记录在 known failures；发现并记录 15 个现有 JSONField W904 警告和 dist 浏览器启动错误，未在 characterization Step 中修复旧行为。
- 镜像与 digest: 仅使用当前基线的临时 PostgreSQL 10/Redis 4 容器和仓库现有 frontend/dist；未构建、发布或修改生产镜像，未产生新的发布 digest。
- 数据/Redis/queue 证据: 只使用临时数据库/runtimes；生成 `migration-plan.txt`、`schema-redis-golden.json`；DB1 保持 session/cache/waiting_queue，DB4 保持 Dramatiq broker/result，快照 key 数为 0；未连接生产数据。
- 已知风险: 完整 JudgeServer compiler/Seccomp runtime corpus 因没有现成 baseline JudgeServer 服务未执行；frontend committed dist 的 `__STATIC_CDN_HOST__` JS URL 在 history fallback 下返回 HTML，Playwright 观察到 `Unexpected token '<'`，均记录于 `docs/contracts/step01-known-failures.md`。
- 回滚点: `f899a96deffa16aedd8a2fc2e803f77c0adc6da4`；本 Step 只新增合同、测试和快照资产，删除本 Step 文件即可回到 Step 00 行为。
- 下一步: Step 02 — 现状盘点与构建基线。

### 2026-08-23 — Step 02

- Commit: 本条记录随 `step 02: record inventory and build baseline` 独立提交
- 变更摘要: 新增源码/依赖/构建/运行卷盘点、当前 Compose 镜像 digest、cold/warm 构建指标和已知发现。
- 实际命令: 执行 Step 02 的 `find`、`git ls-files`、`find docs/research`、`du`、`git diff --check`；盘点 package/lock、两 SPA、Webpack/Babel、Axios/CSRF、Django URL/JSONField、Redis DB1/DB4、Judge CMake/Dockerfile、Compose 和 runtime path metadata；执行 `docker compose config --quiet`；通过隔离临时目录测量 frontend Webpack、backend Buildx 和 Judger CMake cold/warm；查询当前 Compose 远程 image manifest digest。
- 测试/验收结果: 当前源文件 554、Git tracked files 534、research reports 7；frontend compatibility build 在 `NODE_OPTIONS=--openssl-legacy-provider` 下 cold 16.91s/warm 8.17s；未加 workaround 的 Node24 cold build 1.15s 失败，错误已记录；backend image cold 142.03s/warm 1.35s；隔离 Debian Judger build 成功，native host 因缺少 `seccomp.h` 的失败已记录；Compose config 通过但报告 obsolete `version` warning。
- 镜像与 digest: 记录当前 Compose `postgres:10-alpine`、`redis:4.0-alpine`、remote judge/backend `1.6.1` 的 manifest digest；记录本地存在的 stage image size/layer/ID；临时 backend build tags 已删除，未推送任何镜像。
- 数据/Redis/queue 证据: 只读取本地脱敏目录的名称/模式，未读取 secret 内容；记录 `backend/data/config/secret.key` 为 600 且未被 Git 跟踪；没有访问生产数据库、Redis、queue、dump、RDB/AOF 或用户上传。
- 已知风险: frontend 老 Webpack/Babel 与 Node24 的 OpenSSL 兼容问题；Judge Dockerfile 的 `COPY Judger/`/`COPY server/` context/case mismatch；host 缺少 libseccomp dev header；root Compose 仍是 PG10/Redis4、backend 发布端口和浮动 tag。详见 `docs/contracts/step02-known-findings.md`。
- 回滚点: `3e209be8e5574aa4f4ec211dc0da2ce054e0f358`；本 Step 只新增脱敏清单/指标，删除本 Step 文件即可回到 Step 01。
- 下一步: Step 03 — Ubuntu >=22.04 运行前置。

### 2026-08-24 — Step 03

- 状态: **阻塞（非破坏性宿主/运行时预检已完成；生产 Secret 门未满足）**。
- Commit: 本条记录随 `step 03: record Ubuntu runtime preflight` 独立提交
- 目标机: `huawei1` / `XJU-ICTHubS1`；Ubuntu 22.04.5 LTS、x86_64、kernel 5.15.0-186-generic、cgroup v2。
- 工具门: Docker Engine 29.7.1、containerd 2.2.6、runc 1.3.6、Compose v5.4.0、Buildx 0.36.0、BuildKit v0.32.0；default builder healthy，amd64 可用，未声称 arm64 生产就绪。
- 容量/挂载: `/dev/vda1` ext4 `rw,relatime`，40G 总量/17G 已用/22G 可用，inode 使用 15%；`/srv/xju-oj` 与 `/var/backups/xju-oj` 仅有空目录，未读取或修改数据内容。
- 目录/权限: 创建并核验 `/srv/xju-oj/runtime`、PG10/PG18、Redis4/6.2/7.4/8.2 独立根、`deployments`、`secrets` 和 `/var/backups/xju-oj`；运行/卷/部署目录为 `0750 root:root`，secrets/backup 为 `0700 root:root`。
- 权限测试: Judge root container 对 `runtime/judger`/`runtime/log` 写删 probe 成功；`runtime/public` 与 `runtime/test_case` 以 `:ro` 挂载时可读且写入被拒绝；probe 已删除。
- 网络门: UFW inactive；IPv4 Docker FORWARD DROP；IPv6 FORWARD ACCEPT 已记录为后续安全复核项；当前 host 仅监听 SSH/HTTP/HTTPS 与 loopback 服务，未监听 8000/8080/5432/6379；未修改防火墙。
- Secret 门: `/srv/xju-oj/secrets` 为空。没有生成、打印、请求或提交 PostgreSQL password、Django SECRET_KEY、Judge token、管理员密码或 TLS 私钥；因此生产发布门保持 fail-closed，不能声称 Step 03 完成，也不能进入 Step 04。
- 证据: 详见 `docs/contracts/step03-host-preflight.md`、`docs/contracts/step03-runtime-preflight.md`、`docs/contracts/step03-known-findings.md`。
- 回滚点: `6aead8a81cc708d861263baf0bfcabe1a913db35`；仅可删除本 Step 创建的空目录，不执行 volume prune、`down -v` 或删除 Secret。
- 下一步: 由外部 Secret 管理流程提供并核验文件路径/权限/非空内容后，重新验收 Step 03；在此之前停止现代化顺序。
