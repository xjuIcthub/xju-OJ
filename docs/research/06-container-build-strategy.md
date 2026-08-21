# xju-OJ Docker 基础镜像与 BuildKit 缓存专项调研报告

> **固定研究基线**
> 仓库：`xjuIcthub/xju-OJ`
> 分支：`main`
> 提交：`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`
> 调研截点：**2026-08-20**
> 本报告只讨论 Docker 基础镜像、BuildKit/buildx 缓存、镜像供应链与发布方式；不修改代码、不创建 PR。

---

# 1. 执行摘要

## 1.1 结论

**推荐采用“两个应用级多阶段缓存 + 一个真正可复用的 Judge Toolchain 基础镜像”的结构：**

| 模块       | 构建 target          | 是否作为正式镜像发布 | 结论                        |
| -------- | ------------------ | ---------: | ------------------------- |
| frontend | `frontend-deps`    |          否 | 构建阶段、缓存边界                 |
| frontend | `frontend-runtime` |          是 | 前端正式运行镜像                  |
| backend  | `backend-deps`     |          否 | 构建阶段、缓存边界                 |
| backend  | `backend-runtime`  |          是 | Backend API/Worker 共用正式镜像 |
| server   | `judge-toolchain`  |      **是** | 真正值得长期维护的可复用基础镜像          |
| server   | `judge-server`     |          是 | JudgeServer 正式运行镜像        |

**frontend/backend 不建议为了“缓存”单独发布 deps 基础镜像。** Docker 多阶段 layer cache + BuildKit registry cache 已经能够解决大多数“源码变化却重新安装全部依赖”的问题。额外发布 `frontend-deps` / `backend-deps` 会产生独立版本、CVE、清理、同步和发布生命周期，却没有足够跨项目复用价值。Docker 官方推荐通过稳定指令前置、依赖清单先复制、cache mount 和 external cache 来提升此类构建。

**server 则不同。** 固定提交中的 JudgeServer 镜像同时包含 GCC/G++、Go、JDK、Node、Python、Seccomp/Judger 原生构建等重型环境，而且这些内容和 Flask/JudgeServer Python 业务源码当前处于同一 Dockerfile 生命周期。 因而 `judge-toolchain` 应成为独立、扫描、版本化、低频更新的 OCI 镜像；JudgeServer 源码变化只从该 digest 往上构建。

缓存总体采用：

```text
稳定输入
  ↓
Docker layer cache
  ↓
BuildKit cache mount
  ↓
registry cache (mode=max)
  ↓
最终 image + SBOM + provenance + digest
```

其中：

* **layer cache**：输入完全一致时直接跳过整个构建步骤；
* **cache mount**：步骤必须重新执行时，保留 pnpm/uv/apt 等下载缓存；
* **registry cache**：跨开发机和 CI 恢复 BuildKit 的 layer/intermediate cache；
* **local cache**：开发机或固定 CI runner 的第二级缓存；
* **inline cache**：只作为简单场景补充，不作为本项目主要方案。Docker 官方明确指出 registry cache 更适合复杂、多阶段、`mode=max` 构建。

生产部署应最终使用**镜像 digest**，而不是只依赖可变 tag：

```text
registry.example/xju-oj/backend@sha256:...
```

tag 用于人类阅读、版本发现和 CI；digest 才是生产部署身份。

---

# 2. 当前仓库事实

## 2.1 已核实事实

固定提交确认为：

`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`，提交信息为 `chore: separate backend runtime services`。

仓库一级结构已经存在 `frontend`、`backend`、`server`，同时根目录仍存在独立 `docker-compose.yml`。

### frontend

当前 `frontend/package.json` 仍是 Vue 2.5、Webpack 3、Yarn 构建体系，`build:ci` 仍调用 Yarn 和 Webpack DLL。

固定提交已有：

```dockerfile
FROM node:14.21.3-buster AS build

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . ./
RUN yarn run build:ci

FROM nginx:1.27-alpine
...
```

说明它已经正确意识到“依赖文件先于源码 COPY”的基础缓存原则，但 Node 14 已 EOL，且还没有 pnpm store/cache mount/registry cache。

### backend

当前 backend 已采用：

```dockerfile
FROM python:3.12-alpine
COPY deploy/requirements.txt ...
RUN --mount=type=cache,target=/var/cache/apk ...
    --mount=type=cache,target=/root/.cache/pip ...
...
COPY ./ /app/
```

即依赖步骤与源码步骤已经分开。

但存在两个缓存效果问题：

1. pip mount 到 `/root/.cache/pip`，同时执行 `pip install --no-cache-dir`，后者会关闭 pip download cache；
2. APK cache mount 与 `apk add --no-cache` 同时存在，当前写法不应被视为已经实现了有效的 APK 持久下载缓存。

当前依赖入口还是 `deploy/requirements.txt`，其中包括 Django 3.2.25、Dramatiq 1.16、django-dramatiq 0.11.6、Pillow、psycopg2 等。

backend `.dockerignore` 已经排除 `.venv`、`venv`、`node_modules`、运行数据、测试数据、数据库 dump、证书、`.env` 等，这一方向是正确的。

### server

`server` 明确包含 JudgeServer 和 Judger 两部分。

JudgeServer 当前 Dockerfile 的 builder：

* Debian trixie-slim；
* CMake；
* GCC；
* `libseccomp-dev`；
* Python；
* 编译 Judger；
* 构建 Python wheel。

最终阶段又安装：

* Python 3.12；
* Go 1.22；
* Temurin JDK 21；
* GCC/G++ 13；
* Node.js 20；
* strace；
* Flask/Gunicorn/Python deps；
* `libjudger.so`；
* UID 901/902/903 用户。

它已经正确使用了 apt cache mount 和 `sharing=locked`，同时取消 `docker-clean` 并启用 downloaded-package retention，这与 Docker 官方 apt cache 示例一致。Docker 官方特别要求 apt 类共享缓存使用 `sharing=locked` 防止并发写损坏。

但是 JudgeServer 的 pip cache 同样挂载后又使用了 `--no-cache-dir`。

更重要的是，其 NodeSource 配置仍明确使用 `node_20.x`。Node 20 已于 **2026-04-30 EOL**，所以将现有 server 环境提取成基础镜像时，不能把它“永久冻结”。

### 根部署

根 `docker-compose.yml` 仍运行：

```text
registry.cn-hongkong.aliyuncs.com/oj-image/judge:1.6.1
registry.cn-hongkong.aliyuncs.com/oj-image/backend:1.6.1
```

以及 Redis 4/PostgreSQL 10 旧镜像，没有切换到仓库当前三个模块自己的构建产物。Judge `/test_case` 当前已经以 `:ro` 挂载。

因此基线真实状态是：

> **模块 Dockerfile 已经部分现代化，但根级生产部署仍停留在旧远程镜像体系。**

---

# 3. 官方支持与版本矩阵

以下版本结论均以 **2026-08-20** 为访问/判断日期。

| 组件            | 推荐/当前版本            | 官方状态                            | 支持结束                                                | 本项目结论                           | 官方来源                                                                               |
| ------------- | ------------------ | ------------------------------- | --------------------------------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| Node.js       | **24.19.0 / 24.x** | Active LTS（Krypton）             | Active LTS → 2026-10-20；EOL 2028-04-30              | frontend 构建推荐；不选 26 Current     | [Node Releases](https://nodejs.org/en/about/previous-releases)                     |
| Node.js 26    | 26.x               | Current                         | 计划 2026-10-28 才进入 LTS；EOL 2029-04-30                | 截点时不作为长期生产默认                    | 同上                                                                                 |
| Node.js 20    | 20.x               | **EOL**                         | 2026-04-30                                          | 当前 Judge toolchain 必须后续迁移       | 同上                                                                                 |
| pnpm          | **11.21.0**        | Stable release                  | 官方未公布 LTS/EOL 日期                                    | 推荐；Node 22/24/26 支持             | [pnpm Installation](https://pnpm.io/installation)                                  |
| pnpm          | 12.0.0-rc.3        | **RC / Pre-release**            | 不适用                                                 | 不推荐当前生产迁移直接采用                   | 同上                                                                                 |
| uv            | **0.12.5**         | 官方称 stable、广泛用于 production      | 官方未公布固定 EOL                                         | 精确 pin 0.12.5；minor 升级单独验证      | [uv Docker Guide](https://docs.astral.sh/uv/guides/integration/docker/)            |
| Docker Buildx | **0.36.1**         | Latest stable                   | 无 LTS 日期                                            | 推荐当前 CI pin                     | [Buildx Releases](https://github.com/docker/buildx/releases)                       |
| BuildKit      | **0.32.2**         | stable patch，被 Buildx 0.36.1 引用 | **无 LTS；新 feature release 后旧 feature release 不再支持** | 必须持续跟进最新稳定 patch                | [BuildKit project policy](https://github.com/moby/buildkit/blob/master/PROJECT.md) |
| Debian        | **13.6 / trixie**  | Stable                          | 常规支持至 2028-08-09；LTS 至 2030-06-30                   | Judge toolchain 推荐基础 OS         | [Debian Trixie](https://www.debian.org/releases/trixie/)                           |
| Alpine        | **3.24**           | Stable branch                   | 2028-06-01                                          | backend 若继续 Alpine，应显式固定 minor  | [Alpine releases](https://www.alpinelinux.org/releases/)                           |
| Python        | 当前 3.12            | Security-fixes-only             | 2028-10                                             | Docker 缓存改造阶段可以暂时保持，但不是未来框架升级决策 | [Python 3.12 lifecycle](https://www.python.org/downloads/release/python-31213/)    |

### pnpm 12 为什么不选

pnpm 官方安装文档截至调研日仍明确称 **pnpm 12 “currently a release candidate”**。

并且 RC 阶段已有 lockfile 和 CI frozen-lockfile 行为相关问题报告。因此没有必要为了“最新”将一次大规模 Vue/Vite/pnpm 迁移建立在 RC package manager 上。

### BuildKit 为什么不能几年不升级

BuildKit 官方项目策略明确写明：

* 没有 LTS release；
* 新 feature release 发布后，上一 feature release 不再提供支持；
* 用户应始终采用最新 patch release。

因此“pin digest”不能变成“永远不更新”。

---

# 4. 推荐总体架构

```text
                           ┌─────────────────────┐
                           │ upstream base image │
                           │ exact tag + digest  │
                           └──────────┬──────────┘
                                      │
         ┌────────────────────────────┼───────────────────────────┐
         │                            │                           │
 frontend Dockerfile          backend Dockerfile          server Dockerfile
         │                            │                           │
 frontend-deps                 backend-deps                judge-toolchain
         │                            │                           │
 frontend-build                backend-build               judger-build
         │                            │                           │
 frontend-runtime              backend-runtime             judge-server-deps
         │                            │                           │
         └───────────────┬────────────┴──────────────┬────────────┘
                         │                           │
                  Buildx registry cache       SBOM/provenance
                         │                           │
                         └───────────┬───────────────┘
                                     │
                              OCI Registry
                                     │
                              digest deployment
```

---

# 5. frontend：目标与缓存设计

## 5.1 推荐阶段

```dockerfile
FROM node:<24.19.0-tested-tag>@sha256:<digest> AS frontend-base

# 安装精确 pnpm 11.21.0

FROM frontend-base AS frontend-deps

COPY pnpm-lock.yaml ./

RUN --mount=type=cache,id=pnpm-store-${TARGETOS}-${TARGETARCH}-v11,target=/pnpm/store \
    pnpm fetch --frozen-lockfile

COPY package.json ./

RUN --mount=type=cache,id=pnpm-store-${TARGETOS}-${TARGETARCH}-v11,target=/pnpm/store \
    pnpm install --offline --frozen-lockfile

FROM frontend-deps AS frontend-build
COPY . .
RUN pnpm build

FROM nginx:<approved-tag>@sha256:<digest> AS frontend-runtime
COPY ...
COPY --from=frontend-build /app/dist /usr/share/nginx/html
```

这是**阶段结构示意**，不是要求直接复制到仓库。

## 5.2 为什么必须先 `pnpm fetch`

pnpm 官方明确称 `fetch` 专门适合改善 Docker 构建，它主要依据 lockfile，将包提前装入 store，而无需先依赖完整项目 manifest。只要 lockfile 不变，该层可以继续命中。

正确顺序是：

```text
pnpm-lock.yaml
      ↓
pnpm fetch
      ↓
package.json
      ↓
pnpm install --offline --frozen-lockfile
      ↓
业务源码
      ↓
pnpm build
```

而不是：

```text
COPY 整个项目
pnpm install
```

这样普通 `.vue/.ts/.js/.css` 改动不会触发依赖下载。

`--offline` 要求只从已有 store 安装；`--frozen-lockfile` 保证 CI 不偷偷修改 lockfile。pnpm 官方同时说明 frozen lockfile 在 CI 是关键一致性约束。

## 5.3 frontend-deps 是否发布

**不发布。**

它的身份几乎完全由本项目 `pnpm-lock.yaml` 决定，与业务版本绑定。

Registry `mode=max` 已能保存多阶段中间层；单独发布 deps image 会重复 BuildKit 已经完成的工作。

---

# 6. backend：目标与 uv 缓存设计

## 6.1 推荐阶段

```dockerfile
FROM python:<backend-approved-version-and-os>@sha256:<digest> AS backend-base

COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:<digest> \
     /uv /uvx /bin/

ENV UV_LINK_MODE=copy

FROM backend-base AS backend-deps

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,id=uv-${TARGETOS}-${TARGETARCH}-py312-uv012,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

FROM backend-deps AS backend-build
COPY . .

RUN --mount=type=cache,id=uv-${TARGETOS}-${TARGETARCH}-py312-uv012,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM backend-base AS backend-runtime
COPY --from=backend-build /app/.venv /app/.venv
COPY ...
USER backend
```

## 6.2 `--locked` 与 `--frozen`

二者不能混用成“差不多”。

**普通单项目 backend：**

```bash
uv sync --locked --no-install-project
```

优先。

`--locked` 会确认 `uv.lock` 与项目定义一致，否则失败。

**只有 workspace 的初始依赖阶段无法取得所有 workspace manifests 时**，才按 uv 官方建议使用：

```bash
uv sync --frozen --no-install-workspace
```

因为 `--frozen` 不验证 lockfile 是否相对于 manifest 最新。

## 6.3 `--no-install-project`

uv 官方专门把它用于 Docker 分层：

> 先安装第三方依赖，但不安装当前项目，随后再 COPY 高频变化的业务源码。

因此 Python 文件变化时，不会重新构建整个第三方环境。

## 6.4 `UV_LINK_MODE=copy`

uv 官方 Docker 文档明确建议在使用 BuildKit cache mount 时设置：

```dockerfile
ENV UV_LINK_MODE=copy
```

原因是 uv cache 与最终 `.venv` 可能处于不同文件系统，copy mode 可以避免硬链接问题，并使最终虚拟环境自包含。

## 6.5 `.venv` 的边界

这里需要严格区分：

**禁止进入构建上下文的是开发机现成的 `.venv`。**

这与最终 runtime 从受控构建阶段复制：

```text
backend-build/.venv → backend-runtime
```

不是同一件事。

uv 官方同样要求把宿主机 `.venv` 加入 `.dockerignore`。

固定提交当前 `.dockerignore` 已做到这一点。

## 6.6 backend-deps 是否发布

同 frontend：

**不建议发布。**

`uv.lock` 变化已经是明确的缓存失效边界；registry cache 足够。

---

# 7. server：为什么必须有 judge-toolchain

这是本专项最重要的结构变化。

## 7.1 当前问题

当前 JudgeServer Dockerfile：

```text
Debian
 ├─ GCC/CMake/libseccomp
 ├─ build Judger
 ├─ Python
 ├─ GCC/G++
 ├─ Go
 ├─ Java
 ├─ Node
 ├─ Python deps
 └─ JudgeServer Python source
```

这使得：

```text
低频、超重、安全敏感 toolchain
```

与：

```text
高频、轻量 JudgeServer Python 源码
```

处于同一维护生命周期。

## 7.2 推荐拆分

```text
Debian 13 exact digest
        │
        ▼
judge-toolchain
 ├─ GCC / G++
 ├─ Go
 ├─ JDK
 ├─ Node
 ├─ Python runtime/build support
 ├─ libseccomp
 └─ stable system tooling
        │
        ├─────────────── publish + scan + SBOM
        │
        ▼
judger-build
 ├─ Judger C source
 ├─ libjudger.so
 └─ Python wheel
        │
        ▼
judge-server-deps
 ├─ Flask
 ├─ Gunicorn
 ├─ requests / psutil ...
 └─ Judger bindings
        │
        ▼
judge-server
 ├─ JudgeServer source
 ├─ entrypoint
 └─ UID/GID/runtime configuration
```

**普通 `service.py` / Flask 代码变化时：**

```text
judge-toolchain     CACHED / pull existing digest
judger-build        CACHED
judge-server-deps   CACHED
judge-server source rebuild
```

不会再次：

```text
apt download GCC
download JDK
download Go
download Node
compile compiler/runtime stack
```

## 7.3 为什么它值得作为真正基础镜像发布

即使 CI 的 BuildKit cache 被清空：

```text
FROM registry/xju-oj/judge-toolchain:v1.x@sha256:...
```

只需要从 OCI Registry 拉取已经验证过的 toolchain layers。

它不再依赖重新访问：

* Debian mirror；
* Adoptium；
* NodeSource；
* Go packages；
* 编译 Judger 基础环境。

这是 frontend/backend deps image 不具备的价值。

---

# 8. apt / apk 缓存

## 8.1 apt

Docker 官方模式：

```dockerfile
RUN rm -f /etc/apt/apt.conf.d/docker-clean \
 && echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' \
      > /etc/apt/apt.conf.d/keep-cache

RUN --mount=type=cache,id=apt-...,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-lib-...,target=/var/lib/apt,sharing=locked \
    apt-get update \
 && apt-get install ...
```

官方明确解释，某些包管理器要求 exclusive access，因此应用 `sharing=locked`。

当前 JudgeServer 已基本使用此模式。

推荐 cache ID：

```text
apt-debian13-linux-amd64
apt-debian13-linux-arm64
```

**不要包含 Git SHA。**

否则每次提交都会创建新 cache，完全失去复用价值。

## 8.2 apk

最小方案可以继续：

```text
apk add --no-cache
```

并主要依赖 Docker layer + registry cache。

如果实际测量发现 Alpine 包层经常需要重新执行，再启用真实 `/var/cache/apk` cache mount，并按架构/Alpine minor 分区、`sharing=locked`。

Alpine 官方确认 APK 本身存在可启用、清理的 package cache。

不要维持当前这种“声明了 cache mount，但命令自身又走 no-cache 模式”的模糊状态。

---

# 9. cache mount 与最终镜像 layer cache 的区别

| 属性           | Docker layer cache    | `RUN --mount=type=cache` |
| ------------ | --------------------- | ------------------------ |
| 命中条件         | 当前指令及输入未改变            | RUN 即使重新执行也可复用目录内容       |
| 是否跳过 RUN     | 是                     | 否                        |
| 典型内容         | 完整 `pnpm install` 结果层 | pnpm store               |
|              | 完整 uv sync 层          | uv artifact/cache        |
|              | toolchain 完整层         | apt package downloads    |
| 是否进入最终 image | 该层可能进入                | cache 目录本身不会被提交          |
| 主要目的         | 不重新执行步骤               | 重新执行时少下载                 |
| 可被 GC        | 是                     | 是                        |

BuildKit 官方明确指出 cache mount 内容可以跨 builder invocation 保留，但只应视为性能优化；其内容可以被并发构建覆盖，也可能被 GC。构建必须在 cache 为空时仍然正确。

因此不能把 cache mount 当成构建正确性的依赖。

---

# 10. registry / local / inline cache 组合

## 推荐生产 CI

### `cache-from`

每次分支构建读取：

```text
当前 branch cache
+
main cache
```

例如：

```text
registry/xju-oj/cache/frontend:feature-123-linux-amd64
registry/xju-oj/cache/frontend:main-linux-amd64
```

Docker 官方明确支持多个 cache source。

### `cache-to`

写入：

```text
当前分支自己唯一的 ref
```

使用：

```text
type=registry
mode=max
```

`max` 会包括多阶段中的 intermediate layers，正适合 `frontend-deps` / `backend-deps` / `judger-build`。

Docker 官方同时警告：

> 同一个 cache location 被多个并发 job 写入会覆盖。

所以禁止多个并行 architecture/job 同时写：

```text
cache/frontend:main
```

而应该隔离成：

```text
cache/frontend:main-linux-amd64
cache/frontend:main-linux-arm64
```

## local cache

用于：

* 开发机；
* self-hosted CI；
* 离线或网络差环境；
* registry cache 暂时不可达。

按：

```text
.buildx-cache/frontend/linux-amd64/
.buildx-cache/backend/linux-amd64/
.buildx-cache/judge-server/linux-amd64/
```

隔离。

Docker local backend 使用 OCI layout，可显式 import/export。

## inline cache

不作为主方案。

原因：

* 与输出镜像绑定；
* 对复杂多阶段 workflow 扩展性差；
* 无法像独立 registry cache 一样自然管理完整 `mode=max` 中间缓存。

Docker 官方建议复杂 workflow 使用 registry backend。

---

# 11. registry cache 与 pnpm/uv cache mount 的重要边界

不能把二者理解成完全等价。

Registry cache 主要用于恢复 BuildKit 的构建 layer/intermediate records。

Cache mount 则是在某个 BuildKit builder 上持久化 package-manager 工作目录。BuildKit 官方对 cache mount 的定义是“在 builder invocations 之间持久存在”。

因此：

### 临时 CI runner + registry cache

如果 lockfile **没有变化**：

```text
dependency layer hit
→ 根本不运行 pnpm/uv
→ 0 npm/PyPI download
```

很好。

但如果 lockfile **变化**：

```text
dependency layer miss
→ pnpm/uv RUN 重新执行
```

若该 runner 没有以前的 cache mount，本次可能需要重新下载较多 artifacts。

### 更强完整方案

对真正高频 CI 使用：

```text
长期存活的 BuildKit builder
        +
registry cache
```

这样：

* persistent builder 保存 cache mounts；
* registry cache 解决跨机器/灾难恢复/开发机 layer reuse。

这比假设 registry cache 会成为 pnpm store/uv cache 的逐文件远端备份更可靠。

---

# 12. 多架构缓存

frontend/backend 可以目标：

```text
linux/amd64
linux/arm64
```

Docker Buildx 原生支持：

```text
--platform linux/amd64,linux/arm64
```

cache mount ID 必须带：

```text
TARGETOS
TARGETARCH
TARGETVARIANT
```

例如：

```text
pnpm-store-linux-amd64-v11
pnpm-store-linux-arm64-v11

uv-linux-amd64-py312-uv012
uv-linux-arm64-py312-uv012

apt-debian13-linux-amd64
apt-debian13-linux-arm64
```

### JudgeServer 特别限制

**不得因为 amd64/arm64 都“能 build”就宣称都支持生产判题。**

Seccomp syscall、Judger native ABI、资源限制、编译器输出等都可能存在架构差异。

因此初期建议：

```text
frontend: amd64 + arm64
backend:  amd64 + arm64

judge-server:
  amd64 = production supported
  arm64 = experimental until full sandbox regression passes
```

这属于安全边界要求，而不是 Docker 构建问题。

---

# 13. 所有 FROM：tag + digest

推荐形式：

```dockerfile
FROM node:24.19.0-bookworm-slim@sha256:<verified-digest>
```

而不是：

```dockerfile
FROM node:24
FROM node:lts
FROM node:latest
```

Docker 官方指出 tag 是可变引用，而 digest 可以保证获取相同内容；同时使用可读 tag + digest兼顾审阅体验与可重复性。

uv 的官方 Docker 文档同样直接把 SHA256 pin 描述为 reproducible build 场景的最佳实践。

同样适用于：

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:<digest>
```

和：

```dockerfile
FROM registry/xju-oj/judge-toolchain:tc-v1.2.3@sha256:<digest>
```

**本报告不编造具体 digest。** digest 应由迁移 PR 实际解析、验证后提交进仓库。

---

# 14. 自定义 judge-toolchain 镜像版本规范

建议：

```text
registry.example/xju-oj/judge-toolchain:tc-v1.0.3
registry.example/xju-oj/judge-toolchain:git-<12-char-sha>
```

并产生最终：

```text
registry.example/xju-oj/judge-toolchain@sha256:<digest>
```

### 版本语义

**major**

改变判题环境 contract：

* GCC major；
* Python major/minor；
* JDK major；
* Node major；
* Go major/minor；
* UID/GID contract；
* Seccomp policy；
* Judger ABI。

**minor**

兼容性扩充，例如新增一种语言运行时，并经过完整 judge regression。

**patch**

不改变判题语义的：

* Debian security updates；
* 同一 compiler/runtime branch 的安全 patch；
* CA certificates；
* OS library security fixes。

OCI labels 至少包含：

```text
org.opencontainers.image.source
org.opencontainers.image.revision
org.opencontainers.image.version
org.opencontainers.image.created
```

另建议记录：

```text
xju-oj.toolchain-contract
xju-oj.judger-revision
```

---

# 15. 镜像命名与 tag 规范

推荐：

```text
<registry>/xju-oj/frontend
<registry>/xju-oj/backend
<registry>/xju-oj/judge-server
<registry>/xju-oj/judge-toolchain
```

每个正式 runtime build：

```text
frontend:git-a1b2c3d4e5f6
frontend:v2.8.0
frontend:main            # 可变，仅发现

backend:git-a1b2c3d4e5f6
backend:v2.8.0
backend:main

judge-server:git-a1b2c3d4e5f6
judge-server:v2.8.0

judge-toolchain:tc-v1.0.3
```

**Git SHA tag 应不可覆盖。**

`main`、`stable` 等 tag 可以移动，但不得直接作为生产部署的唯一引用。

---

# 16. 生产 Compose：tag 还是 digest

**生产：digest。**

```yaml
services:
  frontend:
    image: ${FRONTEND_IMAGE}

  backend:
    image: ${BACKEND_IMAGE}

  judge:
    image: ${JUDGE_IMAGE}
```

生产配置：

```text
FRONTEND_IMAGE=registry/.../frontend@sha256:...
BACKEND_IMAGE=registry/.../backend@sha256:...
JUDGE_IMAGE=registry/.../judge-server@sha256:...
```

这样仍满足：

> 镜像标签/地址可通过部署配置修改

但配置项实际上接受的是**完整 image reference**，而不局限于 tag。

CI 可以同时记录：

```text
tag: git-a1b2...
digest: sha256:...
```

部署只消费 digest。

---

# 17. SBOM、provenance、digest、Git SHA

BuildKit 原生支持：

```text
--sbom=true
--provenance=mode=max
```

Docker 官方说明：

* SBOM 描述镜像包含/构建使用的软件；
* provenance 描述镜像如何构建；
* minimal provenance 默认存在；
* 可以显式使用 max provenance；
* 推送 registry 时 attestation 会跟随 image index。

推荐正式 CI：

```text
SBOM        = enabled
provenance  = mode=max
Git SHA     = tag + OCI revision label
digest      = metadata file
```

使用：

```bash
docker buildx bake \
  --push \
  --metadata-file build-metadata.json
```

Buildx 官方 `--metadata-file` 输出中明确包含：

```json
"containerimage.digest": "sha256:..."
```

CI 保存：

```text
artifacts/
  build-metadata.json
  images.env
  deployment-digests.json
```

SBOM/provenance 的主副本放 OCI registry attestation，而不是只作为 CI 临时文件。

---

# 18. 是否使用 `docker buildx bake`

**建议使用。**

本项目现在刚好满足 Bake 适用条件：

* 3 个独立模块；
* 4 个正式 OCI artifacts；
* 多个共享变量；
* 多架构；
* cache-from/cache-to；
* SBOM/provenance；
* Git SHA tags；
* 多 target。

Docker 官方把 Bake 定位为 declarative Buildx build configuration，并支持并发执行多个 build targets。

## 文件结构建议

```text
/
├── docker-bake.hcl
├── frontend/
│   └── Dockerfile
├── backend/
│   └── Dockerfile
└── server/
    └── Dockerfile
```

示意：

```hcl
variable "REGISTRY" {}
variable "GIT_SHA" {}
variable "PLATFORMS" {
  default = ["linux/amd64", "linux/arm64"]
}

group "default" {
  targets = [
    "frontend-runtime",
    "backend-runtime",
    "judge-server"
  ]
}

group "toolchain" {
  targets = ["judge-toolchain"]
}

target "_common" {
  platforms = PLATFORMS

  attest = [
    "type=sbom",
    "type=provenance,mode=max"
  ]
}

target "frontend-runtime" {
  inherits   = ["_common"]
  context    = "./frontend"
  dockerfile = "Dockerfile"
  target     = "frontend-runtime"
  tags = [
    "${REGISTRY}/xju-oj/frontend:git-${GIT_SHA}"
  ]
}

target "backend-runtime" {
  ...
}

target "judge-toolchain" {
  context = "./server"
  target  = "judge-toolchain"
}

target "judge-server" {
  context = "./server"
  target  = "judge-server"
}
```

实际 cache refs 建议按 target 分别声明，**不要在 `_common` 中让所有模块写同一 cache ref。**

---

# 19. 缓存 key 与失效规则

## 19.1 cache mount key

### frontend

```text
pnpm-store-{os}-{arch}-pnpm11
```

### backend

```text
uv-{os}-{arch}-py{minor}-uv{minor}
apk-{arch}-alpine{minor}
```

### judge

```text
apt-debian13-{arch}
apt-lib-debian13-{arch}
pip-judge-{arch}-py{minor}
```

**不加入：**

```text
Git SHA
branch
lockfile hash
```

cache mount 本来就是要跨这些变化累积 artifacts。

## 19.2 registry cache ref

这里反而需要 scope：

```text
cache/frontend:main-linux-amd64
cache/frontend:branch-abc-linux-amd64

cache/backend:main-linux-amd64

cache/judge-server:main-linux-amd64
cache/judge-toolchain:tc-v1-linux-amd64
```

---

# 20. 四种典型修改会失效哪些缓存

| 操作                        | frontend                          | backend                     | judge-server                 |
| ------------------------- | --------------------------------- | --------------------------- | ---------------------------- |
| **首次冷构建**                 | 全部构建/下载                           | 全部构建/下载                     | toolchain + Judger + deps 全部 |
| **普通源码修改**                | 只失效 source/build/runtime copy     | 只失效 source/project sync 及以后 | 只失效 JudgeServer source 及以后   |
| **lockfile 修改**           | `fetch/install` 重跑；pnpm store 可复用 | deps sync 重跑；uv cache 可复用   | Judge Python deps layer 重跑   |
| **系统包列表修改**               | 通常不涉及                             | OS deps 及后续失效               | 对应 toolchain 及所有下游失效         |
| **基础镜像 digest 更新**        | 从 base 开始重建                       | 从 base 开始重建                 | toolchain 从 base 重建          |
| **Judger C 源码修改**         | 无影响                               | 无影响                         | judger-build 及以后失效           |
| **JudgeServer Python 修改** | 无影响                               | 无影响                         | **不得重建 judge-toolchain**     |

基础镜像安全更新导致下游 cache 失效是**正确行为**，不应该为了构建速度阻止它。

---

# 21. 最小可行方案

第一阶段不追求一次完成所有基础设施。

## Phase A：缓存边界

frontend：

```text
pnpm lock
→ frontend-deps
→ frontend-build
→ frontend-runtime
```

backend：

```text
pyproject + uv.lock
→ backend-deps
→ backend-runtime
```

server：

```text
judge-toolchain
→ judge-server
```

## Phase B：Buildx

加入：

```text
docker-bake.hcl
registry cache mode=max
branch + main cache-from
architecture-specific refs
```

## Phase C：供应链

加入：

```text
tag + digest FROM
SBOM
provenance
metadata-file
Git SHA tags
```

## Phase D：根部署

`./deploy.sh`：

```text
validate config
→ docker compose config
→ build/pull
→ bootstrap/migrate
→ docker compose up -d
→ smoke test
```

最终 compose 使用本项目三个 runtime images，而不再使用远程 `1.6.1` 老镜像。

---

# 22. 完整 CI / 镜像仓库方案

推荐流程：

```text
PR
 │
 ├─ Dockerfile/Bake static validation
 ├─ frontend tests
 ├─ backend tests
 ├─ JudgeServer/Judger tests
 │
 └─ buildx build
      ├─ cache-from branch
      ├─ cache-from main
      └─ cache-to PR/branch cache

main
 │
 ├─ same validation
 ├─ build amd64
 ├─ build arm64
 ├─ generate SBOM
 ├─ provenance=max
 ├─ vulnerability scan
 ├─ push git-SHA tags
 ├─ record image digests
 └─ update main registry cache

release
 │
 ├─ promote existing tested digest
 ├─ attach version tag
 └─ generate deployment manifest
```

### Judge toolchain 独立 pipeline

触发条件：

```text
server toolchain definition changed
OR
base digest changed
OR
security rebuild schedule
OR
critical CVE
```

流程：

```text
build judge-toolchain
→ compiler version inventory
→ SBOM
→ scan
→ Judger regression
→ seccomp regression
→ publish immutable digest
→ update judge-server toolchain digest
→ judge-server regression
```

不能把“toolchain rebuild”绑定到每次 JudgeServer Python 修改。

---

# 23. 基础镜像升级与 CVE 策略

## 推荐节奏

### 每日

Registry 自动 vulnerability scan。

### 每周

检查：

```text
upstream base digest
Node security release
Python security release
Debian/Alpine security changes
Buildx/BuildKit releases
```

### 每月

即使业务没有变化，也执行一次完整基础镜像 review/rebuild/promote。

### 紧急

建议内部 SLA：

```text
Critical / known exploited reachable CVE: ≤24h 开始修复
High + fix available: ≤7d
Medium: 月度批次
```

这属于架构治理建议，不是 Docker 官方生命周期定义。

## BuildKit 特殊要求

由于 BuildKit 官方没有 LTS：

> 新 feature release 发布后应尽快迁移到该 feature line 的最新 patch。

不应将 `0.32.2` 固定数年。

---

# 24. 基础镜像中绝对不能放什么

`judge-toolchain` 等可复用 base 不应包含：

```text
业务源码
.env
Secret
API Token
JUDGE_SERVER_TOKEN
TLS private keys
本机 node_modules
本机 .venv
runtime data
/test_case
用户上传文件
数据库 dump
生产日志
OJ 测试数据
```

Docker 官方也明确警告 Secret 不应通过 `COPY` 或 `ARG` 管理，应使用 dedicated secret mechanism。

### node_modules / .venv 的准确解释

禁止的是：

```text
COPY ./node_modules
COPY ./.venv
```

但：

```text
frontend-deps 中由 pnpm 创建 node_modules
backend build 中由 uv 创建 .venv
```

属于构建产物，可以在非基础构建 stage 或最终 runtime 中按需存在。

frontend 最终 Nginx runtime 根本不需要 `node_modules`。

`/test_case` 必须继续通过：

```text
/test_case:ro
```

挂载给 JudgeServer，不得 bake 到 image；当前 compose 已经使用只读挂载。

---

# 25. 开发速度与安全更新如何平衡

不要选择：

```text
基础镜像永远不更新
```

来获得缓存。

正确办法是：

```text
普通业务开发
    ↓
稳定 base digest
    ↓
极高 cache hit

安全更新 PR
    ↓
显式改变 base digest
    ↓
有意识地一次性 invalidate 下游
    ↓
完整 rebuild + tests
```

也就是说：

> **安全更新应该是“低频、显式、可审计的 cache bust”，而不是“永远不 bust”。**

---

# 26. 分阶段迁移路径

## Stage 0：只建立测量基线

不改框架。

记录：

```text
cold build duration
warm build duration
npm/PyPI/apt bytes
image sizes
cache hit rate
```

## Stage 1：frontend package-manager/cache

只迁移：

```text
Yarn → pnpm 11
Docker dependency stages
pnpm fetch/offline install
```

不要同时做所有 Vue/Vite 业务改造。

## Stage 2：backend dependency manager

只建立：

```text
pyproject.toml
uv.lock
uv sync
dependency layers
```

尤其要注意当前 requirements 只直接 pin 依赖，首次生成 `uv.lock` 会固定此前未固定的传递依赖，因此必须独立回归。

## Stage 3：server toolchain extraction

先保持判题语言版本不变，把现有环境拆出去。

**不要在同一个不可回滚提交里一边拆 toolchain，一边升级全部编译器。**

随后再单独解决已经 EOL 的 Node 20 等运行时。

## Stage 4：buildx Bake + registry cache

完成跨开发机/CI 的 BuildKit cache。

## Stage 5：supply-chain metadata

SBOM、provenance、digest promotion。

## Stage 6：root deployment

最后才让根 Compose/`deploy.sh` 切换到新镜像。

---

# 27. 破坏性变更与高风险项

## 高风险 1：pnpm lock 转换

当前 frontend 依赖年代较老，包括 Vue 2、Webpack 3、旧 Babel/loader。

pnpm 更严格的依赖隔离可能暴露过去 Yarn Classic hoisting 隐藏的 undeclared dependencies。

这是前端迁移测试重点。

## 高风险 2：uv lock 首次生成

当前 requirements 直接依赖是固定版本，但传递依赖并没有完整 lock。

所以：

```text
pip requirements → uv.lock
```

本身就可能产生环境差异。

不得把这些差异误认为“只是 Docker 重构”。

## 高风险 3：Alpine → Debian

虽然 Debian/glibc 很可能减少 psycopg2/Pillow 等 native package 的本地编译成本，但 backend 更换 distro 会改变 libc/native wheel 行为。

因此本专项不建议和 uv/Django 升级一起做。

## 高风险 4：Judge compiler/runtime 升级

输出差异会直接影响判题环境。

当前 Node 20 已 EOL，但迁移到 Node 24 必须单独使用判题 corpus 验证，不应悄悄发生在 Docker 重构中。

## 高风险 5：arm64 Judger

必须重新验证 Seccomp/UID/resource limit，不得仅凭镜像构建成功开启。

---

# 28. 测试和验收标准

## 28.1 浏览器/API兼容性

Docker 改造后必须保持：

```text
/api
/admin/
/public/
Django Session
csrftoken
X-CSRFToken
现有 API wrapper
pagination
```

不能因 frontend/runtime gateway 更换而改变这些 contract。

## 28.2 Backend

必须保持：

```text
app labels
DB table names
migration graph
Redis DB 1
Redis DB 4
```

## 28.3 Judge

必须逐项验证：

```text
/judge
/compile_spj
/ping
heartbeat
Token digest
result schema
UID 901/902/903 semantics
resource limits
Seccomp
/test_case read-only
```

---

# 29. “没有重新下载所有依赖”的可测指标

这是本专项必须落地成 CI 指标的部分。

## Test A：cold build

使用全新 builder、无 external cache。

记录：

```text
T_cold
npm registry bytes
PyPI bytes
apt/apk bytes
registry bytes
```

设为基线。

## Test B：仅修改 frontend 源码

例如改一行 Vue/TS。

要求：

```text
pnpm fetch                       CACHED
pnpm install                     CACHED
系统依赖                         CACHED
```

验收：

```text
npm/pnpm package download bytes = 0
```

## Test C：仅修改 backend Python 源码

要求：

```text
uv sync --no-install-project dependency layer = CACHED
OS build deps                            = CACHED
```

验收：

```text
PyPI artifact download bytes = 0
```

## Test D：仅修改 JudgeServer Python

要求：

```text
judge-toolchain digest unchanged
judge-toolchain build steps not executed
Judger C compilation not executed
compiler installation not executed
```

验收：

```text
apt compiler/JDK/Go/Node download bytes = 0
```

这是 server 最重要的 KPI。

## Test E：增加一个 frontend 小依赖

在**同一 persistent builder**上：

```text
pnpm fetch reruns
pnpm store reused
```

记录：

```text
downloaded package count
download bytes
```

要求绝大多数旧 package 不重新传输。

可先采用项目级门槛：

```text
新增一个小 dependency：
download bytes < cold dependency download 的 20%
```

随后根据实际 baseline 调整。

## Test F：uv.lock 小变化

同样要求：

```text
uv cache reuse
```

而不是重新下载整个 Python dependency graph。

## Test G：fresh CI runner + registry cache

删除本地 builder cache，只保留 registry cache：

```text
cache-from branch
cache-from main
```

仅修改源码。

要求 dependency layers 仍然命中：

```text
npm/PyPI/apt dependency downloads = 0
```

允许发生：

```text
OCI registry cache layer download
```

因为目标是避免重新访问 package ecosystems，而不是要求网络字节绝对为零。

## 推荐 CI 指标

最终 Dashboard 至少保存：

```text
cold build seconds
warm source-only build seconds
dependency-install vertex cache hit
package registry egress bytes
OCI cache bytes
cache import duration
cache export duration
judge-toolchain digest
```

目标可设为：

```text
普通源码修改：
100% dependency/toolchain expensive vertices cached

package registries:
0 dependency downloads

warm build wall time:
≤ cold build 的 30%~40%
```

最终时间阈值应以真实基线校准，而不是先人为固定。

---

# 30. 停止条件

出现以下任意情况，应停止当前阶段，不继续叠加升级：

1. `/api`、Session、CSRF、`/admin/`、`/public/` contract 发生变化；
2. API response wrapper 或 pagination 改变；
3. Django migration graph/table/app label 发生非预期变化；
4. Redis DB 1/4 语义变化；
5. pnpm 转换后 frontend bundle 行为无法解释；
6. uv lock 引入未验证的 dependency 行为改变；
7. Judge result schema/heartbeat/token contract 改变；
8. UID/GID/resource limits/Seccomp 有任何弱化；
9. `/test_case` 不再只读；
10. arm64 sandbox 无法通过与 amd64 等价的安全 regression；
11. registry cache 并发写出现覆盖/污染；
12. 发布镜像存在未处置的可利用 Critical CVE；
13. 无法确认实际生产运行的是预期 digest。

---

# 31. 回滚原则

所有正式发布必须保留：

```text
previous frontend digest
previous backend digest
previous judge-server digest
previous judge-toolchain digest
previous compose deployment manifest
```

回滚方式：

```text
修改完整 image ref 到旧 digest
docker compose up -d
```

而不是：

```text
把 latest/stable tag 强行重新指向旧镜像
```

Judge toolchain 必须能独立回退：

```text
judge-toolchain tc-v1.0.4
             ↓ regression
judge-server FROM tc-v1.0.3@sha256:...
```

Docker/cache 重构阶段原则上不得伴随不可逆数据库 migration，这样镜像回滚才真正可行。

---

# 32. 待本仓库实测的问题

### frontend

* 旧 Yarn lock 转 pnpm lock 后是否存在 undeclared/hoisted dependency；
* Vue 2 → Vite 迁移后的实际 Node 24 compatibility；
* `pnpm fetch` 对最终 mono/non-workspace 布局的具体配置；
* Nginx history fallback 是否完整保持 `/admin/`；
* `/api`、`/public/` proxy/cache headers。

### backend

* 当前项目生成 `pyproject.toml` / `uv.lock` 后传递依赖差异；
* Alpine 下 psycopg2/Pillow 是否仍大量源码编译；
* 是否值得后续独立切 Debian slim；
* API 与 Worker 是否可以完全使用同一 runtime image；
* Python runtime 最终版本应由 backend modernization 专项确定，而不是由 Docker 专项抢先决定。

### server

* Judger native build 是否在 amd64/arm64 完全一致；
* Seccomp syscall rules 是否架构相关；
* Node 20 → Node 24 的判题 compatibility；
* Go/JDK/GCC 版本升级是否影响历史题目；
* toolchain image 中哪些 runtime 真正需要长期保留；
* 是否可以移除 NodeSource/Adoptium 混合 package repository；
* native Judger wheel 是否应成为独立 artifact，还是跟 `judge-server` 构建。

---

# 33. 最终推荐

本仓库不要建立：

```text
frontend-base-image 每次依赖更新都 push
backend-base-image 每次 Python dependency 更新都 push
```

这会制造额外维护负担。

应采用：

```text
frontend
  └─ multi-stage + pnpm store + registry cache

backend
  └─ multi-stage + uv cache + registry cache

server
  └─ published judge-toolchain
        └─ judge-server
```

并让：

```text
registry cache
```

成为开发机/CI 的主要跨机器 layer cache，

让：

```text
persistent BuildKit cache mount
```

负责 lockfile 变化时减少 package 下载，

让：

```text
judge-toolchain OCI image
```

负责彻底隔离低频重型判题工具链。

安全更新则通过：

```text
精确 tag + digest
→ 周期扫描
→ 显式 base update
→ rebuild
→ SBOM
→ provenance
→ regression
→ 新 digest
```

完成。

这套结构能同时满足两个看似冲突的目标：

> **普通业务开发尽可能不重新下载/编译依赖；安全更新又不会因为缓存和基础镜像长期冻结而停滞。**

---

# 34. 官方来源清单

访问日期均为 **2026-08-20**。

| 来源                                                                                              | 用途                                                  |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [Docker Build cache optimization](https://docs.docker.com/build/cache/optimize/)                | layer、cache mount、apt locked cache、external cache   |
| [Docker cache backends](https://docs.docker.com/build/cache/backends/)                          | registry/local/inline、cache-from/to、并发 cache ref    |
| [Docker registry cache](https://docs.docker.com/build/cache/backends/registry/)                 | registry `mode=max`                                 |
| [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/)          | amd64/arm64                                         |
| [Docker Build attestations](https://docs.docker.com/build/metadata/attestations/)               | SBOM / provenance                                   |
| [Docker buildx build reference](https://docs.docker.com/reference/cli/docker/buildx/build/)     | metadata-file / image digest                        |
| [Docker Buildx Bake](https://docs.docker.com/build/bake/)                                       | 多 target 声明式 build                                  |
| [Docker build best practices](https://docs.docker.com/build/building/best-practices/)           | multi-stage、pin digest、base refresh                 |
| [pnpm fetch](https://pnpm.io/cli/fetch)                                                         | Docker fetch workflow                               |
| [pnpm install](https://pnpm.io/cli/install)                                                     | offline / frozen lockfile                           |
| [pnpm Docker recipe](https://pnpm.io/docker)                                                    | BuildKit pnpm store cache                           |
| [pnpm installation/version compatibility](https://pnpm.io/installation)                         | pnpm 11/12 状态、Node compatibility                    |
| [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/)                         | uv cache、locked/frozen、no-install-project、copy mode |
| [uv versioning policy](https://docs.astral.sh/uv/reference/policies/versioning/)                | stable status、minor breaking policy                 |
| [Node.js releases](https://nodejs.org/en/about/previous-releases)                               | Node Current/LTS/EOL                                |
| [Node.js release schedule](https://raw.githubusercontent.com/nodejs/Release/main/schedule.json) | 精确 Maintenance/EOL 时间                               |
| [Buildx Releases](https://github.com/docker/buildx/releases)                                    | Buildx 0.36.1 / BuildKit 0.32.2                     |
| [BuildKit project policy](https://github.com/moby/buildkit/blob/master/PROJECT.md)              | 无 LTS、feature release 支持策略                          |
| [Debian 13 Trixie](https://www.debian.org/releases/trixie/)                                     | Debian Stable/LTS 生命周期                              |
| [Alpine release branches](https://www.alpinelinux.org/releases/)                                | Alpine 支持结束时间                                       |
| [Alpine APK documentation](https://docs.alpinelinux.org/user-handbook/0.1a/Working/apk.html)    | APK package cache                                   |
| [固定仓库提交](https://github.com/xjuIcthub/xju-OJ/commit/2d84d089bcd8ea90d5836c00d7c46e6de47697fc)   | 仓库研究基线                                              |
