# 前端快速迭代与隔离发布计划

## 目标

在不改变 Django、OIDC、数据库、Redis、Worker、Judge 协议和运行时配置合同的前提下，让 Vue 前端可以独立构建、验收和上线。一次前端发布只替换 Nginx frontend 容器，不触碰后端服务和持久化数据。

## 当前结论

- 当前 Compose 已将 frontend 作为唯一宿主端口服务；`/api` 由 frontend Nginx 反向代理到 `backend-api`。
- `frontend/Dockerfile` 已分为 `frontend-base`、`frontend-deps`、`frontend-build`、`frontend-runtime`；Node/pnpm 与依赖下载可由 BuildKit/pnpm cache 复用。
- 现有 `BUILD_TARGETS=frontend` 已避免其他镜像重建，但旧路径仍会执行全栈初始化和 Worker/Judge smoke，不能算快速发布。
- 本轮新增 `deploy.sh --frontend-only`，把“只替换 frontend”做成显式、fail-closed 的发布合同。

## 发布合同

```text
frontend source change
        |
        v
frontend-base/deps cache -> frontend image
        |
        v
backend-api reachability check
        |
        v
frontend only recreate -> static/API smoke -> current.json/previous.json
```

前端-only 要求上一成功 release 存在，并保留非前端镜像；当前提交与工作树若有 `frontend/` 之外的变更（包括 backend、server、Compose、deploy 脚本或 Secret/运行配置相关文件），脚本拒绝执行并提示使用完整部署。这样不会把“前端-only metadata”误当成包含后端变更的全栈 release。

## 日常迭代步骤

1. 前端开发：只修改 `frontend/`，运行前端 lint/build、路由合同和必要浏览器测试。
2. 提交并推送：

   ```bash
   git add frontend
   git commit -m "feat(frontend): ..."
   git push origin main
   ```

3. huawei1 拉取并预检：

   ```bash
   cd /home/winbeau/xju-OJ
   git pull --ff-only
   BUILD_TARGETS=frontend ./deploy.sh --frontend-only --dry-run
   ```

4. huawei1 快速发布：

   ```bash
   BUILD_TARGETS=frontend ./deploy.sh --frontend-only
   ```

5. 通过公网反向代理验收 `/`、`/admin/`、一个 SPA deep link、`/runtime-config.js`、`/api/website/` 和 OIDC 登录按钮；确认 backend/Worker/Judge 容器未被重建。

## 缓存与耗时策略

- 同一主机保留 BuildKit builder、本地 `frontend-base` 镜像和 pnpm cache；不要每次清理这些 cache。
- 依赖未改变时，`frontend-deps` 使用 lockfile 层缓存，源码修改只重新执行 `frontend-build` 与 runtime 导出。
- 多主机或清理后主机可配置持久 `CACHE_REGISTRY`，为 `frontend` 和 `frontend-base` 提供 registry cache；生产仍必须使用已验收的 immutable image ref。
- 不把浏览器缓存、CDN 缓存或 runtime-config 变更混入前端-only 的版本判断；需要 Compose/环境变更时走完整部署。

## 回滚

- 每次成功发布前，脚本将旧 `current.json` 保存为 `previous.json`；旧 frontend image 必须在观察窗口内保留。
- 回滚前先确认 API/Session/CSRF 合同兼容，再从 `previous.json` 取得旧 frontend image reference，通过 `docker compose ... up -d --no-deps --force-recreate frontend` 切回；不执行 `down -v`、数据库回滚或删除旧服务。
- 回滚后运行相同 frontend smoke，并记录原因和 image reference；如果问题涉及 API/Compose/运行配置，停止 frontend-only 回滚，改走完整 release rollback 流程。

## 分阶段升级计划

1. **已完成：部署隔离** — 增加 `--frontend-only`、前端范围门、非前端镜像保留、frontend-only smoke 和 release metadata 保留。
2. **下一步：视觉改造** — 仅在 `frontend/` 内按页面/组件切片迭代，每个切片通过 lint、build、route contract 和浏览器 smoke 后发布。
3. **稳定性阶段** — 为首页、题目、比赛、提交、个人中心和 admin 各补一条关键路径浏览器回归；只验证 API 合同，不改后端。
4. **缓存阶段** — 在 huawei1 验证本地 BuildKit/pnpm cache 命中；需要时再接入受控 registry cache，不把 mutable tag 用于生产回滚。
5. **推广阶段** — 连续若干次前端-only 发布无后端重启、无 API 回归、回滚演练通过后，将该模式作为日常前端发布标准。

## 验收与停止条件

- 必须通过 `sh -n deploy.sh`、`git diff --check`、frontend lint/build、route contract、frontend-only dry-run 和实际 frontend smoke。
- 发现非前端变更、上一 release 缺失、保留镜像缺失、backend-api 不可达或 frontend health 失败时立即停止；不自动重启全栈，不删除数据或旧镜像。
- 后端/OIDC/数据库/Redis/Judge/Compose/Secret 任何变更都不能借用此路径，必须执行完整部署与对应安全测试。
