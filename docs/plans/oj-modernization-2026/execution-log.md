# 2026 现代化迁移执行记录

> 此文件只记录已经实际执行并验证的事实；计划文本、预估结果和“应当通过”不能写成完成事实。

## 全局信息

- 生产宿主：Ubuntu >=22.04；Step 00 实测目标为 Ubuntu 22.04，支持状态仍由 Step 03 preflight 再验收
- Python：3.10.x，Step 00 锁定官方 amd64 基础镜像解释器 `3.10.21` 与 manifest digest
- 当前分支：`main`
- 计划入口：[README.md](README.md)
- 当前执行模型：Phase 0–5；Step 文档作为 Phase 内技术清单
- 当前 Phase：Phase 2 fixture lane 已验收；可进入 Phase 3，真实 protected clone/生产发布证据仍留在后续 gate
- 最近完成：Phase 2 Judge 五边界闭环、完整 build/pull/rollback gate 与 WSL 全栈验收

## 记录格式

每完成一个 Phase 或重要 checkpoint，追加一条：

```text
### YYYY-MM-DD — Phase N / checkpoint

- Commit:
- 完成的 Step 清单:
- 实际命令:
- 测试/验收结果:
- 镜像与 digest:
- 数据/Redis/queue 证据:
- Soft failures / deferred:
- Hard-stop 核验:
- 回滚点:
- 下一 Phase:
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

- 状态: 非破坏性宿主/运行时预检已完成；旧 Step 模型曾因生产 Secret 缺失标记阻塞，后续 Phase 模型已把该门限定到 Phase 5。
- Commit: 本条记录随 `step 03: record Ubuntu runtime preflight` 独立提交
- 目标机: `huawei1` / `XJU-ICTHubS1`；Ubuntu 22.04.5 LTS、x86_64、kernel 5.15.0-186-generic、cgroup v2。
- 工具门: Docker Engine 29.7.1、containerd 2.2.6、runc 1.3.6、Compose v5.4.0、Buildx 0.36.0、BuildKit v0.32.0；default builder healthy，amd64 可用，未声称 arm64 生产就绪。
- 容量/挂载: `/dev/vda1` ext4 `rw,relatime`，40G 总量/17G 已用/22G 可用，inode 使用 15%；`/srv/xju-oj` 与 `/var/backups/xju-oj` 仅有空目录，未读取或修改数据内容。
- 目录/权限: 创建并核验 `/srv/xju-oj/runtime`、PG10/PG18、Redis4/6.2/7.4/8.2 独立根、`deployments`、`secrets` 和 `/var/backups/xju-oj`；运行/卷/部署目录为 `0750 root:root`，secrets/backup 为 `0700 root:root`。
- 权限测试: Judge root container 对 `runtime/judger`/`runtime/log` 写删 probe 成功；`runtime/public` 与 `runtime/test_case` 以 `:ro` 挂载时可读且写入被拒绝；probe 已删除。
- 网络门: UFW inactive；IPv4 Docker FORWARD DROP；IPv6 FORWARD ACCEPT 已记录为后续安全复核项；当前 host 仅监听 SSH/HTTP/HTTPS 与 loopback 服务，未监听 8000/8080/5432/6379；未修改防火墙。
- Secret 门: `/srv/xju-oj/secrets` 为空。没有生成、打印、请求或提交 PostgreSQL password、Django SECRET_KEY、Judge token、管理员密码或 TLS 私钥；生产发布门保持 fail-closed。Phase 1–4 可使用隔离测试 Secret，不再因此阻塞 WSL/huawei1 smoke。
- 证据: 详见 `docs/contracts/step03-host-preflight.md`、`docs/contracts/step03-runtime-preflight.md`、`docs/contracts/step03-known-findings.md`。
- 回滚点: `6aead8a81cc708d861263baf0bfcabe1a913db35`；仅可删除本 Step 创建的空目录，不执行 volume prune、`down -v` 或删除 Secret。
- 下一步: Phase 1 — 在 WSL 并行构建 frontend/backend/server 组件桥接和可重复镜像；生产 Secret 延后到 Phase 5。

### 2026-08-24 — Phase 执行模型收束

- 变更性质: 仅更新执行计划，不修改应用、镜像、数据、服务或 Secret。
- 新模型: 31 个 Step 收束为 Phase 0–5；Phase 是推进/验收/必需提交单位，Step 是内部技术清单。
- 环境顺序: WSL 组件与全栈 → WSL 最终应用 → huawei1 同 digest 隔离演练 → 生产数据与发布。
- 失败策略: 构建、依赖、代理、测试、候选版本和环境差异按 soft failure 在 Phase 内修复/重试/defer；只让破坏性数据、合同破坏、安全边界和不可恢复回滚四类 hard stop 停止。
- 依赖修正: Step21 fresh target 足以支持 WSL/huawei1 framework 开发；Step20 隔离 rehearsal 与生产 cutover 分开；Step22/生产 Secret 只在 Phase5 成为前置。
- 详细入口: [README.md](README.md) 与 `phases/00-foundation.md`–`phases/05-production-release.md`。
- 下一步: 新对话从 [Phase 1](phases/01-component-bridge.md) 开始。

### 2026-08-24 — Phase 1 / component bridge acceptance

- Commit: `7020d88` — `phase 1: build reproducible component bridge`
- 完成的 Step 清单: Frontend 04–06 bridge；Backend 11–14 bridge/compat-prep（JSONField migration-sensitive substep deferred）；Server 23–26 amd64 bridge/toolchain/protocol/health/hardening；Step 27 Bake definition and metadata shape。
- 实际命令: `corepack pnpm@11.22.0 import/install --frozen-lockfile`、`pnpm run lint`、`pnpm run build`；`uvx --from uv==0.12.5 uv lock/sync`、Django `check`、`makemigrations --check --dry-run`、isolated PostgreSQL10/Redis4 migration and `tests.contracts`；`docker buildx build` for all three images；`docker buildx bake --print`；server protocol unittest, JudgeServer `/ping`/healthcheck and hardened container probes。
- 测试/验收结果:
  - Frontend: pnpm frozen install, lint and Vite dual-entry build passed; `dist/index.html` and `dist/admin/index.html` present; isolated Nginx `/`, `/admin` redirect, `/admin/`, `/runtime-config.js` and `nginx -t` passed.
  - Backend: Python `3.10.21` image; uv locked environment; Django check passed with the pre-existing 15 JSONField W904 warnings; migration dry-run reported no changes after reverting the unsafe JSONField state switch; isolated migration and backend contract suite passed `7/7`.
  - Server: Python `3.10.21`, Go `1.26.5`, Node `24.19.0`, OpenJDK `21.0.12`, libseccomp `2.6.0`, amd64 Judger wheel/native library; JudgeServer protocol suite passed `4/4`; hardened `/ping` passed with `read_only`, `no-new-privileges`, `cap_drop=ALL`, `CHOWN/SETUID/SETGID/KILL`, `pids_limit=512`; `/test_case` write probe was blocked. Existing Judger corpus ran `32/35`; three resource/toolchain-sensitive cases remain deferred: `test_cpp_meta`, `test_gcc_random`, `test_get_time`.
  - Supply chain: `docker-bake.hcl --print` passed; frontend/backend/server image build inputs use recorded immutable base digests and the server toolchain exposes the locked runtime versions. No registry push was available in this WSL lane, so the following are local immutable image IDs for later OCI transfer/verification.
- 镜像与 digest: source SHA `7020d88`; local image IDs: `frontend sha256:d83823b894e3d26e50f467ebcf29cbe34331fe6faab94b2a36801e997a5793dd8` (about 68 MB), `backend sha256:9fd4528aa6e74612082e55a6abf5b46a3c56f3c8ced845e0a513920bb9fa8e7b` (about 281 MB), `server sha256:e46fde2989618f8dc312357227e760c8d8932d236bf74aeca8a582aa5a4183d8` (about 2.31 GB). Base references used: Python `sha256:7ed92b...`, Node `sha256:3638d9...`, Nginx `sha256:97d490...`, GCC Trixie `sha256:468b5b...`, Go `sha256:53eeac...`, Temurin `sha256:85f009...`, uv `sha256:e85be8...`; full values remain in Dockerfiles/version lock.
- 数据/Redis/queue 证据: only disposable PostgreSQL10/Redis4 containers and a temporary runtime root were used; migration/test containers were removed; no production volume, queue, dump, RDB/AOF, upload or Secret was read or changed. Redis DB1/DB4 contract tests passed.
- Soft failures / deferred:
  - WSL BuildKit inherited an unusable local proxy namespace; frontend registry/Git fetch used `--network=host` with the configured `127.0.0.1:10808`, while Debian package stages used the reachable mirror and recorded retry behavior. No production proxy or Secret was changed.
  - `jsonfield==3.2.0` cannot resolve with Django `3.2.25` because it requires Django `>=4.2`; the bridge keeps `jsonfield==3.1.0` and the historical PostgreSQL JSONField alias. A native JSONField switch produced unapproved `AlterField` output and was reverted; revisit only in the Django compatibility checkpoint with schema evidence.
  - GCC image resolved to the current GCC 14 series patch (`14.4.0`) rather than the earlier `14.2.x` candidate; record as same-major patch drift and re-evaluate before final promotion.
  - Vite reports legacy font URL, runtime-config script, CommonJS namespace and bundle-size warnings; build and route smoke still pass. Full six-language/security/resource corpus and cold/warm timing benchmark remain deferred to the next integration lane.
- Hard-stop 核验: no Secret, token, credential, private key or runtime data entered Git, image layers or ordinary logs; no `privileged`, Docker socket, `SYS_ADMIN`, public Judge port, writable `/test_case`, or weakened Judge UID/GID/Seccomp boundary was used. No destructive command (`down -v`, prune, FLUSHDB, DROP, volume deletion) was run.
- 回滚点: code checkpoint `0385d96` (Phase 0); bridge commit `7020d88`; local bridge images are separately tagged `git-7020d88` and old remote/legacy Compose assets were not modified.
- 下一 Phase: Phase 2 release-gate pending；完成 fixture/restore、Redis ladder、pull lane 和剩余 Judge/worker smoke 后再进入 Phase 3。Phase 1 can be reverted independently without data rollback.

### 2026-08-24 — Phase 2 / WSL full-stack checkpoint

- Commit: `db5de41` — `phase 2: run isolated WSL full stack`
- 完成的范围: Step 19 inventory/manifest 工具实现并在隔离运行时执行；Step 28 Compose 网络、卷、health、Secret-file 和多角色 backend 拓扑；Step 29 deploy.sh 的 build、首装、幂等升级、dry-run、config-only 和核心全栈 smoke。该条是 WSL checkpoint，不把尚未执行的发布路径写成完成。
- 实际命令: 在隔离 `COMPOSE_PROJECT_NAME=xju-oj-phase2`、临时 runtime/backup/Secret 根中执行四个 BuildKit chunk（`frontend`、`backend`、`judge-toolchain`、`server`）；执行 `ENV_FILE=/tmp/xju-oj-phase2-deploy.NrQVku/.env ./deploy.sh`（提交后重新构建并执行一次）、`./deploy.sh --dry-run`、`./deploy.sh --config-only`；执行 `docker buildx bake --allow=network.host --call=check --file docker-bake.hcl frontend backend judge-toolchain server`、`docker compose config --quiet`、各 shell `sh -n`、`git diff --check`；执行 `deploy/ops/inventory.sh` 和定向 HTTP/CSRF、Worker、Judge smoke。
- 测试/验收结果:
  - `deploy.sh` build chunk、infra readiness、bootstrap、migration、token/admin 幂等、service readiness、HTTP smoke、worker smoke 和 Judge `/ping` 均通过；`current.json` 已写入，`previous.json` 在升级路径中保留。migration second run 报告 `No migrations to apply`；已有 token/admin 未被覆盖。
  - 服务状态: PostgreSQL 18、Redis 8.2、backend-api、backend-worker、frontend、JudgeServer 全部 healthy；仅 frontend 发布 `127.0.0.1:18080`，backend/Judge/PostgreSQL/Redis 保持 Compose 内部端口。
  - HTTP/contract: `/` 为 200，`/admin` 为 301，`/admin/`、`/runtime-config.js`、`/api/website/`、`/public/website/favicon.ico` 通过；缺失 CSRF 返回 403，带合法 CSRF 的无效登录请求返回 200；内部 Judge `/ping` 鉴权和 heartbeat 通过。
  - Inventory: 生成 manifest 和 SHA-256；WSL rootless 无法读取容器 UID 拥有的 `backend/test_case` 时记录 `files=unavailable bytes=unavailable access=denied`，不再把权限错误刷入普通日志或错误报告为零文件。
  - Bake contract: 四个目标 `--call=check` 通过且无 Dockerfile warning；Compose config 和 shell syntax 通过。
- 镜像与 digest: source SHA `db5de41`；Compose SHA-256 `1355956767c57698a33deb9fc19792897af4baf596be9b5199d6a66680d907ae`；local image IDs: `frontend sha256:e747eccf28b02b69a57aba0cc4b4f127575b8496f671f0026a87048d0d47d3e7`、`backend sha256:2df80deadbb48369aeb2e8d74f3a03f984acffc8cc798e4fa94f7a3cf72564f2`、`server sha256:8cd01fb4839daa5759eee8c0e88e4c92825651aa4e0df2de33978b1c14076ce6`、`judge-toolchain sha256:7986f063d9d7a7370dc840b7e63c11c7dbcca574ffa467ccfbdafdd57fc8ca2e`；四个镜像 label revision 均为 `db5de41`、version `phase2`。
- 数据/Redis/queue 证据: 只使用 `/tmp/xju-oj-phase2-deploy.NrQVku` 隔离 runtime、临时 PostgreSQL/Redis 和测试 Secret；未读取或修改生产卷、生产 Secret、生产 queue、dump、RDB/AOF 或用户数据。已验证 Redis DB1/DB4 queue smoke、backend worker enqueue/result/delete 和 Judge heartbeat。
- Soft failures / deferred:
  - 真实 protected clone、PG directory dump restore、Redis 4→6.2→7.4→8.2 ladder、waiting_queue/DB4 完整业务核账仍为 release-gate pending；`backup-fixture.sh` 尚未作为恢复证据执行。
  - `DEPLOY_MODE=pull` 尚未执行；本 WSL lane 使用 `--load` 的本地 immutable image IDs，未进行 registry push/transfer。
  - `/judge`、`/compile_spj` 正向判题 smoke、worker retry/stop/restart、完整 login/session refresh/logout 矩阵尚未完成；本 checkpoint 已覆盖 `/ping`、heartbeat、CSRF 和核心 worker smoke。
  - SBOM/provenance/registry cache artifact 尚未生成；shellcheck 不在当前环境中，已执行 `sh -n` 替代语法检查。
  - 保留 Phase 1 已知软失败：Django 15 个 JSONField W904、Judger `test_cpp_meta`/`test_gcc_random`/`test_get_time` 三个资源/工具链敏感用例、GCC 14.4.0 与候选 14.2.x 的 patch drift。
- Hard-stop 核验: 未将 Secret、密码、Token、Cookie、私钥、运行数据或测试 dump 写入 Git、镜像层或普通日志；未使用生产连接、`privileged`、Docker socket、`SYS_ADMIN`、公开非 frontend 端口、可写 `/test_case`、`down -v`、prune、FLUSHDB、DROP 或 volume 删除；未执行 huawei1。
- 回滚点: Phase 1 bridge `7020d88`/acceptance `e39973e`；Phase 2 当前代码 `db5de41`；隔离 runtime、Compose project、日志和 local image IDs 均保留，未删除旧 checkpoint。
- 下一 Phase: 完成上列 Phase 2 release-gate pending 项后进入 Phase 3；在此之前不触碰 huawei1 或生产。

### 2026-08-24 — Phase 2 / Judge 五边界与 WSL fixture lane 验收

- Commit: `6536fe6` — `fix(server): close judge sandbox boundaries`；本条执行证据随独立 docs 提交记录。
- 完成的范围: JudgeServer 编译产物交接、File IO 生命周期、SPJ 隔离、native runner/后代回收、六语言 seccomp 五个边界闭环；完成最终 build deploy、immutable-digest pull、无数据 rollback、应用/Worker/Judge smoke，以及 fixture PostgreSQL/Redis 恢复证据。
- 实际命令: 对最终提交执行一次完整 `ENV_FILE=/tmp/xju-oj-phase2-deploy.NrQVku/.env-final ./deploy.sh`；随后执行既定 Judge API/security/SPJ/六语言脚本、Session/CSRF/路由脚本和 Worker stop/restart probe；把三张运行镜像推到临时 loopback registry 后，以 manifest digest 写入 `.env-pull` 并执行一次 `DEPLOY_MODE=pull` 全门；用 build refs 与 pull digest refs 各切换一次 Compose 验证 rollback；BuildKit 以 `--provenance=mode=min --sbom=true --push` 生成四个带 attestation manifest 的 OCI index。没有再次重复完整 Judge 或 deploy 矩阵。
- Judge/安全验收:
  - File IO 缺失输出稳定返回 WA，`output=null`、`output_md5=null`，随机哨兵不再进入 API；固定输入/输出拒绝 symlink、hardlink 和替换，编译产物保持 root-owned、单链接并在 runtime 前完成显式交接。
  - SPJ 使用私有 staging、版本化不可变发布和 root-only compile lock；4 路并发编译、4 路并发判题（每次 8 testcase）通过，冲突版本被拒绝，调用方配置未被修改。
  - native Judger 为 `2.1.4`；显式 cwd、setup/exec error pipe、UID/GID/补充组降权、process group、subreaper、FD 清理、后代 CPU/rusage 聚合、精确 timeout 和 Landlock File IO scope 均通过定向验证。
  - C、C++20、Python、Java、Go、JavaScript 的 Standard IO/File IO 为 `12/12`；通用攻击矩阵 `6/6`、多 runtime 安全矩阵 `8/8`、负例矩阵 `7/7`；外部只读 `/test_case`、Node worker thread、noexec/setup error、后代回收和资源边界通过。
  - 上游 Judger corpus 为 `36/38`；仅保留两个现代工具链断言差异：`cpp_meta` 当前为 RE 而旧断言预期 TLE，`gcc_random` 在 GCC 14.4 立即失败而旧断言预期等待至少 2 秒。实际 Judge、资源和攻击矩阵不受影响。
- 应用/部署验收: frontend、backend-api、backend-worker、JudgeServer、PostgreSQL 18、Redis 8.2 均 healthy；登录、session refresh、sessions endpoint、logout、合法/非法 CSRF、`/`、`/admin/`、deep links、API、完整 `/public/`、immutable asset cache 通过。Worker 在停止期间成功入队，重启后消费并恢复 health，DB1 保持 `0→0`，DB4 为 `1→3→1`；额外 deterministic retry-failure 注入未为测试而新增。临时 registry/builder 清理后，只有 frontend 发布 `127.0.0.1:18080`。
- build/pull/rollback: 完整 build gate 的 attempt 为 `attempt-20260824T153830Z-2265677`，pull gate 为 `attempt-20260824T154802Z-2286167`；两者均通过 infra、bootstrap、migration、token/admin 幂等、services-ready、HTTP、Worker 和 Judge `/ping`。build refs 与 pull digest refs 双向切换后 Session/Worker smoke 通过；`current.json`/`previous.json` 保留相同 image ID 和不同引用，证明无数据镜像 rollback 路径。
- 镜像与 digest: source SHA `6536fe65da9a8ab1c6e050a99cd3221e17a31233`；Compose SHA-256 `dec1ee36418177386732245c3cac959740091bd6e12a1b8d280b81a3722dc176`；image IDs 为 frontend `sha256:97aa218b10b26e57a6f52ef30bad166d6b96907b8ec39b4f42ef89b34596ddae`、backend `sha256:93b18ce3ba8f9fe3839cf26de7ec53a7196711bd1cff2c072a4c299ba939bfae`、server `sha256:f90353373b23dadb4d4be7a6ff7da6c4959c829a0920ba70e54c6a568177f8b7`、judge-toolchain `sha256:d6e2ab4ec2e99cd50180aa7bcf3fcf0e2063177b10f4ae70fb4ac425d67247fc`。
- immutable pull refs: frontend `sha256:bf79ab9101edcc76c1d28ae1c4fc5a87b141ccac4ae1627a5eada2e895d3954a`、backend `sha256:f4982197ddcf4af3d0b517588716e56fadcd8ca7cef052fb9073d8c526b44dd8`、server `sha256:7a1fa7486a5f1f236fda3c45662c63fb24e0ad48e4f1621b2383156a978c06ed`；`runtime/deployments/images.env` 已由 `current.json` 生成且模式为 `0600`。
- SBOM/provenance: 四个临时 OCI index 均包含 amd64 image manifest 和独立 attestation manifest；index digest 为 frontend `sha256:6c21201bb27c9218e2e1e1eb6baa857cdf5dfab02f3063f512d235f9cd428fa9`、backend `sha256:8fcecf19cbcab0c66b2201b5707744b18b783bd12c34a156f76bfb88fe876171`、judge-toolchain `sha256:fc8c6534932fb0969f6fb8fcaa81f9a2fea0f640aed88b1f11139cf518742e39`、server `sha256:28053e7821f5e6115cef1a78e926815157a103581d4d3ec287fa6002b91d2252`。临时 loopback registry 已删除；持久 registry/cache promotion 和 CVE scanner gate 留到 Phase 3/4，当前环境没有可用 scanner。
- 数据/Redis/queue 证据: 最新 fixture backup `20260824T085542Z` 的 `sha256sums` 全部通过；fresh PostgreSQL 18 directory restore 已验证 `django_migrations=70`；Redis `4.0.14→6.2.23→7.4.10→8.2.8` 每跳均保留 DB1 marker、`waiting_queue=1` 和 DB4 marker。所有数据、RDB、dump、Secret 和 runtime 均位于 Git ignored 的临时根；未访问生产数据。
- Soft failures / deferred: 真实 protected clone、两次生产规模 restore、业务对象级 queue/ACK/result 核账和持久 registry transfer 按 Phase 2 文档留作后续 release gate；显式 Worker retry-failure 注入、registry cache artifact、CVE scan 与 `shellcheck` 未执行。15 个历史 JSONField W904、GCC patch drift 和上述两项旧 Judger corpus 差异继续记录，不阻塞 fixture lane。
- Hard-stop 核验: 未触碰 `huawei1` 或生产；未把 Secret、Token、Cookie、私钥、dump、RDB/AOF 或 runtime 写入 Git、镜像参数或普通日志；未使用 `privileged`、Docker socket、`SYS_ADMIN`、公开非 frontend 端口、可写 `/test_case`、`down -v`、prune、FLUSHDB、DROP 或破坏性 volume 操作。
- 回滚点: `008fa38` 为 Phase 2 checkpoint，`6536fe6` 为 Judge 五边界代码提交；最终 build refs 与 immutable pull refs 映射到相同 image IDs，`previous.json`/`current.json` 和两个成功 attempt 日志均保留在隔离 runtime。
- 下一 Phase: Phase 2 WSL fixture lane 已达到进入 Phase 3 的完成标志；Phase 3 只继续最终应用/供应链收束，不重跑已通过的 Judge 全矩阵。进入 Phase 4 前仍不触碰 `huawei1`。
