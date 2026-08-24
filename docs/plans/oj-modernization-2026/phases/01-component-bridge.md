# Phase 1：WSL 组件桥接与可重复构建

## 目标

在本机 WSL 同时推进 frontend、backend、server 三条独立 lane，尽快得到可运行、可缓存、可按 digest 标识的组件镜像。此 Phase 不连接生产数据，不等待生产 Secret。

## Step 映射

| Lane | Step | 内部顺序 | Phase 结果 |
|---|---|---|---|
| Frontend | 04–06 | pnpm lock → Vite7 双入口 → Nginx image | Vue2 bridge 镜像可运行 |
| Backend | 11–14 | uv metadata → uv image → Python3.10 base → Django compat cleanup | 当前框架 bridge 镜像可运行 |
| Server | 23–26 | build context → toolchain → protocol/health → hardening | hardened amd64 server/toolchain 可运行 |
| Supply chain | 27 | 等三个 lane 的 image stage 可构建后接入 | Bake、cache、digest、metadata |

Frontend、backend、server lane 可并行；Step 27 最后汇总，但可先建立骨架。

## 执行顺序

1. 核验 clean tree、Phase 0 contracts 和版本锁。
2. 同时启动三个 lane；每个 lane 先修 owning layer 的根因，不做跨模块补丁。
3. 每个 lane 达到 component smoke 后保留 checkpoint commit/image。
4. 统一 Docker build context、BuildKit cache id、Git SHA tag、digest 和 metadata。
5. 在 WSL 执行 clean/warm build 与最小 component smoke。
6. 更新 execution-log，Phase 验收后提交并 push。

## 最小验收

### Frontend

- `pnpm install --frozen-lockfile` 可从 clean store 重建。
- `/` 与 `/admin/` 两入口可构建；deep link、`/api`、`/public` 不误入 SPA fallback。
- runtime config 不含 Secret，域名/端口变化无需重编 bundle。
- 保留旧 Webpack/Yarn 路径和 Vue2 bridge image，直到 Phase 3 完成；不按 Step06 过早删除。

### Backend

- `uv.lock` 可在 Python `>=3.10,<3.11` clean image 中安装。
- API、worker、migrate/bootstrap 角色由同一 image 提供。
- Django check、migration dry-run、合同测试通过；无意外 migration。
- URL/JSONField/historical migration blocker 在 owning layer 修复。

### Server

- 根 context 能同时访问 `server/judger` 与 `server/judge-server`，修复大小写/context 问题。
- toolchain 和 JudgeServer Python runtime 符合锁定版本；amd64 为必需，arm64 可 deferred。
- `/ping`、Judge protocol corpus、UID/GID、Seccomp、资源限制和攻击负向通过。
- 不需要 privileged、Docker socket、SYS_ADMIN 或公开 8080。

### Build

- `docker buildx bake` 或等效命令能构建 frontend/backend/server/toolchain。
- 源码-only 修改不重新下载全部依赖或重建 toolchain。
- 记录 source SHA、base digest、result digest、cold/warm 时间和 cache 行为。
- 本地 scanner/SBOM 暂不可用可标 deferred，但相应 image 不晋级生产。

## Soft failure 处理

- npm/PyPI/apt/registry/proxy/DNS 故障：修代理或 mirror 后重试，不停止其他 lane。
- 候选 patch 不可用：保持 feature line，更新版本锁并选择可验证 patch。
- 单测、lint、browser 或 size regression：留在 lane 内修复；不阻塞无依赖 lane。
- WSL 缺少 host header/library：优先容器化 build，不要求系统级本地安装作为唯一路径。
- arm64/QEMU 失败：记录为 experimental deferred，不阻塞 amd64。

## Hard stop

- 为启动 server 必须放宽 Judge 安全边界。
- Secret 或 runtime data 进入 image/build context/log。
- 合同测试证明 API/Session/CSRF、migration identity、Redis/Judge 协议已被未批准改变。
- Python3.10 无法取得受维护且可锁 digest 的构建来源。

## 交付与回滚

- 至少保留 frontend/backend/server 三个 lane checkpoint；Phase 接受后一个汇总提交并 push。
- 任何 lane 可退回 Phase 0/current image；无数据写入，不需要数据回滚。
- 输出供 Phase 2 消费的 image reference、digest 和 build metadata。

## 完成标志

WSL 能独立启动三个组件的最小 smoke，且可从 clean checkout/lock 重建。随后进入 [Phase 2](02-wsl-full-stack.md)。
