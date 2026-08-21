# Step 07：Vue 3 核心迁移

## 目标

在 Vite 7 桥接稳定后，将两个 SPA 的运行时从 Vue 2 迁移到 Vue 3；本 Step 只处理入口、全局 API、Router、i18n、状态库桥接，不同时替换所有 UI 和编辑器。

## 进入条件

- Step 06 frontend 镜像、Nginx、浏览器合同通过。
- 已建立 Vue 2 模板语法和全局 API inventory。
- 可独立回滚到 Vue2/Vite7 镜像。

## 目标依赖

- Vue 3.5.41。
- `vue-router` 5.2.0。
- `vue-i18n` 11.4.8。
- 先使用 Vuex 4.1.0，Pinia 延后到 Step 10。
- `@vue/compat` 只用于诊断，不作为永久运行时。

## 文件范围

- `frontend/src/pages/oj/index.js`
- `frontend/src/pages/admin/index.js`
- `frontend/src/pages/*/router/**`
- `frontend/src/store/**`
- `frontend/src/i18n/**`
- `frontend/src/shared/**`
- `frontend/package.json`
- 受影响的组件测试和入口 HTML

## 改造顺序

1. `new Vue()` → `createApp()`，将 `Vue.prototype` 映射为 `app.config.globalProperties` 或明确 composable。
2. 处理插件安装、全局 filters、`Vue.util` 和混入；过滤器改为显式 formatter。
3. Router 3 → Router 5，保持 `/admin/` base、route name、meta title、history fallback。
4. 删除 `vuex-router-sync`，将 route 状态通过 Router/composable 明确传给 store。
5. Vuex 3 → Vuex 4，保持 state/action/mutation 语义。
6. i18n 7 → i18n 11，逐个验证 locale、fallback、日期/数字格式。
7. 入口成功后再处理组件模板语法和 UI。

## 必测 Vue 2 语法

- `.native`、`.sync`、`slot-scope`、旧 `v-model` 的 value/input。
- `filters`、`Vue.prototype`、`Vue.util`、`new Vue`。
- 动态组件、keep-alive、异步组件、错误处理和页面标题。

## 计划命令

```bash
cd frontend
pnpm add vue@~3.5.41 vue-router@~5.2.0 vuex@~4.1.0 vue-i18n@~11.4.8
pnpm add -D @vue/compat@~3.5.41
pnpm install --frozen-lockfile
pnpm run build
pnpm run test:unit
pnpm run test:e2e
```

真实脚本名以项目配置为准；`@vue/compat` 关闭前必须清理 warning。

## 验收

- `/` 和 `/admin/` 均可启动、导航、刷新、登录和退出。
- route meta title、权限路由、404、重定向、懒加载 chunk 与基线一致。
- Vuex 无双写；没有长期同时维护两套 source of truth。
- locale、日期/数字格式和 API 错误展示一致。
- compat warning 为零，或每一条有批准的临时豁免和移除日期。

## 停止条件

- 必须永久启用 compat 才能运行关键页面。
- Router base、Session/CSRF、API wrapper 或 history 行为变化。
- 需要把 UI/编辑器/数据库 HTML 结构改写才能启动。
- Vuex 与新状态库形成不可解释的双向写入。

## 回滚

切回 Step 06 的 Vue2/Vite7 frontend digest；不回滚 backend、数据库、Redis 或 API。

## 完成标志

提交格式建议：

```text
feat(frontend): migrate application runtime to Vue 3
```

下一步先迁 UI，编辑器单独按 Step 09 处理。
