# Step 27：BuildKit、Bake 与供应链

## 目标

统一 frontend/backend/server 的多阶段构建、缓存、digest、SBOM、provenance 和镜像标签；不改变业务协议或数据。

## 进入条件

- Step 06 frontend、Step 12/13 backend、Step 23/24/26 server image stages 已能独立构建。
- Step 03 持久化 BuildKit builder 和 Ubuntu24.04 preflight 通过。
- 镜像 registry、权限和 cache namespace 已批准。

## Target 设计

```text
frontend-deps / frontend-build / frontend-runtime
backend-deps / backend-build / backend-runtime
judge-toolchain / judger-build / judge-server-deps / judge-server
```

frontend/backend 的 deps 只作为构建缓存，不单独发布。`judge-toolchain` 真正发布，因为包含重型编译器和语言运行时，需独立扫描、版本化和回滚。

## 缓存规则

Frontend：

```text
COPY package.json pnpm-lock.yaml
RUN --mount=type=cache,id=pnpm-${TARGETOS}-${TARGETARCH},target=/pnpm/store pnpm fetch
COPY source
RUN --mount=type=cache,id=pnpm-${TARGETOS}-${TARGETARCH},target=/pnpm/store pnpm install --offline --frozen-lockfile
```

Backend：

```text
COPY pyproject.toml uv.lock
RUN --mount=type=cache,id=uv-${TARGETOS}-${TARGETARCH}-py312,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev
COPY source
RUN uv sync --locked --no-dev
```

Server：

- apt cache 使用 `sharing=locked`，按 OS/ARCH 隔离。
- CMake/Judger 只在 judger-build 执行。
- JudgeServer Python 源码变化不得触发 toolchain 重装/重编。

cache mount 与 layer cache 是两个机制，都要保留；registry cache 使用 `mode=max`。

## Bake 与标签

新增根 `docker-bake.hcl`，统一声明四个发布目标：

- frontend
- backend
- judge-toolchain
- server

每个正式镜像同时有可读 tag 和 immutable digest：

```text
registry/xju-oj/frontend:git-<sha>
registry/xju-oj/backend:git-<sha>
registry/xju-oj/server:git-<sha>
registry/xju-oj/judge-toolchain:tc-v<major>.<minor>.<patch>
```

生产 Compose 消费 `image@sha256:<digest>`，不消费 `latest/main/stable`。

## 供应链

正式构建启用：

```text
SBOM
provenance=mode=max
build metadata
vulnerability scan
```

保存 `build-metadata.json`、`images.env`、`deployment-digests.json`；OCI labels 至少包含 source、revision、version、created。所有 `FROM` 使用 tag + verified digest。

## 计划命令

```bash
docker buildx bake --file docker-bake.hcl \
  --set '*.platform=linux/amd64' \
  --set '*.cache-to=type=registry,ref=<cache-ref>,mode=max' \
  --metadata-file build-metadata.json --push
```

实际 registry/cache ref、平台和凭据由 CI Secret 注入；不要在命令或日志中写 token。

## 验收指标

- 源码-only 修改：frontend 不重新下载 npm，backend 不重新下载 PyPI，JudgeServer 不重建 toolchain/Judger。
- lockfile 变更：已有 artifact 尽可能复用。
- fresh CI runner + registry cache 能恢复依赖层。
- 记录 cold/warm 时间、下载量、cache hit、昂贵 vertex 和镜像 digest。
- amd64/arm64 cache 不互相污染；Judge arm64 仍受 Step26 支持门控制。

## 停止条件

- 并行 job 写同一 registry cache ref 导致污染。
- 生产镜像没有 digest/SBOM/provenance。
- cache 命中依赖 Secret 或把业务源码/运行数据 bake 入基础镜像。
- Critical CVE 未有批准处置，或无法确认最终运行 digest。

## 回滚

构建缓存不可用不应影响旧镜像部署；切回上一 deployment digest。`judge-toolchain` 版本独立回退，不删除正在观察的旧 tag/digest。

## 完成标志

提交格式建议：

```text
build: add reproducible buildx bake and supply-chain metadata
```
