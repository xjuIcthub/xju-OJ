# Step 10：Frontend 最终平台清理

## 目标

在 Vue3、UI、编辑器均稳定后，独立升级 Vite 8、迁移 Vuex→Pinia，并清理旧 Webpack/Yarn/监控和工具依赖。

## 进入条件

- Step 07、08、09 的回归和数据 corpus 通过。
- 两个 SPA 已无未批准的 compat warning、Vue2 模板语法和旧 UI 引用。
- frontend 可按 Step 06 镜像回滚。

## 迁移顺序

1. Vite 7.3.6 → Vite 8.2.1：单独构建、浏览器 SLA、旧标签页和 N/N-1 assets 验证；只在配置迁移完成后使用 Vite8/Rolldown 配置。
2. 每次只迁一个 store：Vuex4 → Pinia4.x，禁止长期双写；迁移后删除对应 Vuex module。
3. ECharts 3 → ECharts6/vue-echarts8，逐页做图表 golden。
4. `raven-js` → `@sentry/vue`，检查 DSN 为空和启用两条路径。
5. moment → `Intl` 或 Day.js；日期时区 golden 必须先通过。
6. Font Awesome4、highlight.js9、`vue-analytics` 分项替换/删除。
7. 删除 Webpack DLL、Babel6、旧 loader、Webpack dev server、Yarn Classic 和旧部署脚本。

## 文件范围

- `frontend/vite.config.mjs`
- `frontend/package.json`、`pnpm-lock.yaml`
- `frontend/src/store/**`
- `frontend/src/shared/monitoring/**`、`time/**`、`analytics/**`
- `frontend/build/**`、`frontend/config/**`（确认零引用后删除）
- `frontend/yarn.lock`（最后删除）
- `frontend/Dockerfile`、Nginx、E2E/CI

## 运行时配置合同

`runtime-config.js` 至少保持 N/N-1 schema；Sentry DSN、analytics ID、feature flag 可运行时注入，但不得含 Token/密码。域名、端口和 backend upstream 变化不能触发 frontend build。

## 计划命令

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm run lint
pnpm run test:unit
pnpm run test:e2e
pnpm run build
rg -n 'webpack|vuex-router-sync|new Vue|Vue\.util|raven-js|vue-analytics|vue-codemirror-lite|tar-simditor' src package.json build config || true
```

## 验收

- `pnpm install --frozen-lockfile` 在干净目录成功；不需要 Yarn、全局 loader 或 hoist。
- Vite8 双入口、history、Nginx、cache、runtime-config 和旧标签页通过。
- Pinia 无双状态源；所有 store 有单元/E2E 覆盖。
- 用户端/管理端、编辑器、图表、监控、上传、API/CSRF 全量通过。
- 旧 Webpack/Yarn 文件删除后 `git grep` 无业务引用。
- frontend 镜像可独立回滚，不需要 backend/database migration。

## 停止条件

- Vite8 改变浏览器 SLA，或只能通过放弃旧标签页兼容解决。
- 任何 store 需要长期双写。
- 删除旧依赖后构建依赖隐式全局包。
- frontend 回滚必须改变数据库或后端协议。

## 回滚

Vite8、Pinia 和每类依赖使用独立 commit/image；失败时切回上一 frontend digest。不要自动恢复已改变的数据库 HTML/配置。

## 完成标志

提交格式建议：

```text
chore(frontend): remove legacy webpack and finalize Vite platform
```

frontend 轨道完成后，继续维护 N/N-1 镜像直到 Step 30 发布窗口结束。
