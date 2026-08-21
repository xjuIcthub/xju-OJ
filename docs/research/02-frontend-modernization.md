# xju-OJ Frontend 2026 现代化专项调研报告

**调研对象**：`xjuIcthub/xju-OJ`
**固定分支**：`main`
**固定提交**：`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`
**调研截点**：2026-08-20
**调研范围**：仅 `frontend` 现代化及其与现有 Django/API/Nginx 部署边界的衔接；不修改代码、不创建 PR。
**结论分类**：

* **已核实事实**：来自固定提交仓库内容或官方资料。
* **架构建议**：基于已核实事实给出的生产迁移方案。
* **仍需仓库实测**：无法仅凭静态代码和公开文档确认，必须在目标仓库执行构建/E2E 后决策。

---

# 1. 执行摘要

## 1.1 核心结论

**建议采用“三阶段迁移”，不建议一次性从 Vue 2/Webpack 3/Yarn 跳到 Vue 3/Vite 8/pnpm 并同时替换 UI、编辑器、状态管理和部署。**

推荐顺序：

| 阶段      | 核心变化                                                               | 明确不同时做                         |
| ------- | ------------------------------------------------------------------ | ------------------------------ |
| P0      | 建立行为基线、依赖审计、E2E                                                    | 不换框架                           |
| Stage 1 | Node 24 LTS + pnpm 11 + Vite 7.3 + Vue 2.7.16                      | 不换 Vue 3、不换 UI                 |
| Stage 2 | Vue 3.5 + Router 5 + i18n 11 + Element Plus/View UI Plus；Vuex 4 暂留 | 不同时上 Vite 8、不强制 Pinia、不批量重写编辑器 |
| Stage 3 | Vite 8.2、Pinia、CodeMirror 6、Tiptap、Sentry、ECharts 6 等最终清理          | 每类依赖独立可回滚                      |

最重要的原因是：官方 `@vitejs/plugin-vue2` **只支持 Vue 2.7，并且项目已经停止积极维护，仓库于 2026-05-19 归档；其 peer dependency 只覆盖 Vite 3～7，而没有 Vite 8**。因此 Vue 2 + Vite 是一个合理的**短期构建系统桥梁**，但绝不能成为新的长期平台。

Vue 2 本身已于 **2023-12-31 EOL**，2.7.16 是最终版本，因此 Stage 1 应设明确退出条件，例如“完成 Vite 化后两个发布周期内启动 Vue 3 切换”，而不是把 Vue 2 + Vite 7 当成长期生产目标。

最终 Node 推荐 **24.x LTS，而不是 26.x Current**。截至调研日，Node 24 为 Active LTS，2026-10-20 进入 Maintenance，2028-04-30 EOL；Node 26 仍是 Current，要到 2026-10-28 才进入 LTS。Node 官方明确建议生产应用使用 Active LTS 或 Maintenance LTS。

最终 Vue 推荐 **3.5.41 稳定线**，不选择当时仍处于 RC/Beta 的 Vue 3.6。npm 截点显示 `3.5.41=latest`，而 `3.6.0-rc.4=rc`。

最终 Vite 推荐 **8.2.1**，但应放到 Vue 3 产品迁移之后。Vite 8 已于 2026-03-12 正式稳定发布并将生产 bundler 切换为 Rolldown；截至截点，8.2 获得 regular patches，7.3 仍获得 important/security fixes，因此 Stage 1 使用 Vite 7.3.6 并不意味着立即进入无支持状态。

---

# 2. 当前仓库事实

## 2.1 固定基线

目标提交确认为 `2d84d089bcd8ea90d5836c00d7c46e6de47697fc`，提交说明为 `chore: separate backend runtime services`；固定提交下存在 `frontend`、`backend`、`server` 三个一级模块。

当前 frontend 的 `.nvmrc` 仍固定为 **Node 14.21.3**。

现有 Dockerfile 构建阶段同样使用 `node:14.21.3-buster`，执行 Yarn Classic `yarn install --frozen-lockfile`，运行阶段使用 Nginx；因此 Node/Yarn/构建工具升级可以在 frontend 镜像内部完成，不要求先改变 backend/server。

## 2.2 两个 SPA 是真实的独立入口

Webpack 配置明确存在：

```text
oj    -> ./src/pages/oj/index.js
admin -> ./src/pages/admin/index.js
```

而不是一个 SPA 中简单区分两个路由前缀。

因此本报告**不建议把两个 SPA 合并**。Vite 应继续保留两个 HTML entry：

```text
/
└── index.html

/admin/
└── index.html
```

最终生成：

```text
dist/index.html
dist/admin/index.html
```

## 2.3 API/CSRF 是明确的兼容契约

用户端 API 代码当前明确设置：

```text
axios.defaults.baseURL = '/api'
xsrfHeaderName = 'X-CSRFToken'
xsrfCookieName = 'csrftoken'
```

同时通过 `res.data.error !== null` 判断业务错误。

管理端采用同样的 `/api`、`csrftoken`、`X-CSRFToken` 约定，并同样依赖 `{error,data}` 包装。

所以：

> **迁移过程中不得把 frontend 改成独立 API 域名，也不应为了 Vite 开发方便而引入生产 CORS。**

生产继续保持浏览器看来完全同源：

```text
https://oj.example.com/
https://oj.example.com/admin/
https://oj.example.com/api/...
https://oj.example.com/public/...
```

## 2.4 当前 history/Nginx 边界已经较清晰

固定提交下 Nginx 已经具有：

* `/admin` → 301 `/admin/`
* `/admin/...` → fallback 到 `/admin/index.html`
* `/...` → fallback 到 `/index.html`
* `/api`、`/api/...` → backend
* `/public/...` → `/data/public/`
* `/api` 与 `/public` 不经过 SPA history fallback

这是非常好的兼容边界，现代化时应**保持语义而不是重新设计路由拓扑**。

## 2.5 当前 Vue 2 技术债并非只在 package.json

代码已实际使用以下 Vue 2 模式：

* `Vue.prototype`
* `new Vue(...)`
* `Vue.util...`
* 全局 filter
* Vuex 3
* `vuex-router-sync`
* Vue Router history

特别是 Router 中存在：

```text
sync(store, router)
```

Store 中又读取：

```text
state.route.meta.title
```

说明 `vuex-router-sync` 不是“装了没用”，而是存在真实行为耦合。

## 2.6 pnpm 会立即暴露至少两个隐式依赖

当前 `CodeMirror.vue` 直接：

```text
import 'codemirror/mode/clike/clike.js'
import 'codemirror/mode/python/python.js'
```

但顶层 manifest 没有显式声明 `codemirror`。

Simditor 自定义插件又直接：

```text
import * as $ from 'jquery'
```

同样依赖 Yarn Classic 的 hoist 行为。

pnpm 官方明确强调 package 只能访问自己 `package.json` 中声明的依赖，这种严格性正是迁移价值之一。

**Stage 1 不应通过 `shamefully-hoist=true` 永久掩盖问题。**
短期继续使用旧编辑器时，应把 `jquery`、`codemirror` 显式补成 direct dependency；最终替换编辑器后再删除。

## 2.7 编辑器属于高风险持久化兼容点

管理端 Simditor 不是纯 UI：

* 保存富文本 HTML；

* 图片上传固定为 `/api/admin/upload_image/`；

* 自定义文件上传固定为 `/api/admin/upload_file`；

* 自定义插件会生成 `<a ...>` HTML；

* 组件以 Vue 2 `value` + `input` 实现 `v-model`。

因此编辑器迁移不能仅以“页面能打开”为验收标准，必须做**已有内容打开→不编辑→保存后 HTML 等价性**测试。

---

# 3. 官方支持与版本矩阵

> 所有“访问日期”均为 **2026-08-20**。
> Vue、Vite、pnpm 等项目没有官方 LTS 概念时，本报告不会自行称其为 LTS。

## 3.1 核心运行时和框架

| 组件                    | 截点版本/范围                        | 发布状态                 | 官方支持状态                     | 支持结束                                 | 兼容/备注                            | 本报告结论        | 来源 |
| --------------------- | ------------------------------ | -------------------- | -------------------------- | ------------------------------------ | -------------------------------- | ------------ | -- |
| Node 24.x             | 24.x；官方 changelog 截点可见 24.18.1 | Active LTS / Krypton | Active LTS                 | 2028-04-30；2026-10-20 进入 Maintenance | 生产官方推荐使用 LTS/Maintenance         | **选择**       |    |
| Node 26.x             | 26.x                           | Current              | Current                    | 预计 2029-04-30；2026-10-28 才进 LTS      | 截点尚非生产首选 LTS                     | **暂不选**      |    |
| pnpm                  | 11.22.0                        | Stable / `latest`    | 当前稳定主线                     | 官方未公布固定 EOL                          | pnpm 11 支持 Node 24；严格依赖解析        | **选择**       |    |
| pnpm 12               | 12.0.0-rc.6                    | RC                   | 预发布                        | 不适用                                  | 不能作为生产固定基线                       | **不选**       |    |
| Vue 2                 | 2.7.16                         | Final                | **EOL**                    | **2023-12-31**                       | 最终 Vue 2；无社区安全修复                 | **仅桥接**      |    |
| Vue 3                 | 3.5.41                         | Stable / `latest`    | 当前稳定线                      | 未公布固定 EOL                            | Vue 3 当前正式稳定版本                   | **最终选择**     |    |
| Vue 3.6               | 3.6.0-rc.4 / beta.17           | RC/Beta              | 预发布                        | 不适用                                  | 不是稳定版本                           | **不选**       |    |
| Vite                  | 7.3.6                          | Stable / previous    | Important + security fixes | 无固定日期；滚动支持                           | `plugin-vue2` 支持的最后一个 Vite major | **Stage 1**  |    |
| Vite                  | 8.2.1                          | Stable / latest      | Regular patches            | 无固定日期；滚动支持                           | Vite 8 使用 Rolldown               | **最终选择**     |    |
| `@vitejs/plugin-vue2` | 2.3.4                          | Stable package       | **不再积极维护；仓库已归档**           | 实际已停止正常维护                            | Vue `^2.7`; Vite `^3`～`^7`       | **短期桥梁**     |    |
| `@vitejs/plugin-vue`  | 6.0.8                          | Stable / latest      | 当前维护                       | 未公布固定 EOL                            | peer 支持 Vite 5～8、Vue 3           | **Vue 3 使用** |    |

### Node 资料冲突说明

Node Release WG 的 schedule 是决定生命周期的权威来源。部分 Node Archive/CHANGELOG 页面在抓取时出现“最新 patch 展示不同步”的现象，因此本报告**不把某个 patch 号写死为长期架构约束**。

生产规则应为：

> `Node 24.x LTS` 是平台基线；Docker/CI 在每次依赖维护窗口固定一个已验证 patch + image digest。

生命周期判断以 Release WG 的 schedule 为准，而不是 archive 页面某个瞬时 patch 列表。

## 3.2 Vue 生态目标版本

| 包              |      推荐版本 | 状态                            | 支持结束      | 兼容要求/原因                                               | 来源 |
| -------------- | --------: | ----------------------------- | --------- | ----------------------------------------------------- | -- |
| `vue-router`   |  `~5.2.0` | Stable                        | 未公布固定 EOL | v5 官方称为无主要 breaking change 的“boring release”；适合 Vue 3 |    |
| `vue-i18n`     | `~11.4.8` | Stable                        | 未公布固定 EOL | 当前正式版本；Vite 已有对应 tree-shaking 支持                      |    |
| `vuex`         |   `4.1.0` | Stable / Maintenance-oriented | 未公布固定 EOL | Vue 3 兼容；API 与 Vuex 3 高度一致；官方已推荐新项目用 Pinia            |    |
| `pinia`        |   `4.0.3` | Stable / latest，但发布很新         | 未公布固定 EOL | Vue 3；可与 Vuex 共存并逐 module 迁移                          |    |
| `element-plus` | `~2.14.4` | Stable                        | 未公布固定 EOL | Vue 3；官方声明 API stable，并提供 Element UI 迁移资料             |    |
| `view-ui-plus` | `~1.3.24` | Stable                        | 未公布固定 EOL | Vue 3/iView lineage；生态明显小于 Element Plus               |    |

Pinia 4.0.3 在调研截点仅发布数天，因此虽然它是稳定 `latest`，**不建议把“Vue 3 首次上线”和“Vuex→Pinia”绑定在一个提交中**。Pinia 官方明确支持 Vuex 和 Pinia 在一个项目中共存并逐 module 迁移。

---

# 4. 推荐目标及不选其他候选的原因

## 4.1 Vue 2 + Vite 是否适合作为短期桥梁

**结论：适合，但只适合作为限定生命周期的迁移桥。**

理由：

1. Vue 2.7 官方确实提供 Vite 支持，官方 Vue 2 changelog 明确指出 2.7 的 Vite 支持通过 `@vitejs/plugin-vue2` 提供。
2. 它能够把两个互相独立的问题拆开：

   * Webpack 3/Babel 6/Yarn → pnpm/Vite；
   * Vue 2 → Vue 3。
3. 对 xju-OJ 尤其有价值，因为现有 Webpack 配置还包含 DLL、CommonsChunkPlugin、旧 loader、旧 Babel 等大量与 Vue 业务逻辑无关的技术债。
4. 但 Vue 2 已 EOL，plugin-vue2 已归档，且 peer dependency 截止 Vite 7，因此这个状态**不能长期停留**。

### 桥接硬边界

Stage 1 固定：

```text
Vue               2.7.16
Vite              7.3.6
@vitejs/plugin-vue2 2.3.4
Node              24.x LTS
pnpm              11.22.0
```

**禁止**强行给 `plugin-vue2` 打 Vite 8 patch 作为生产基线。Vite 8 support PR 在仓库归档前仍未合并。

---

## 4.2 为什么不一次性直接 Vue 3 + Vite 8

一次性升级会同时改变至少六层行为：

```text
Yarn node_modules layout
        ↓
pnpm strict dependencies
        ↓
Webpack 3 → Vite
        ↓
Rollup/esbuild semantics → Rolldown semantics
        ↓
Vue 2 → Vue 3 runtime/template behavior
        ↓
iView/Element/编辑器/Router/Store 全部变化
```

出现问题时很难定位。

尤其 Vite 8 是一次重要 bundler 架构切换：官方称其将之前 esbuild + Rollup 双 bundler 收敛为 Rolldown。

因此推荐：

> **先用 Vite 7 把 Webpack/Yarn 技术债拆掉；再在已稳定的 Vite 开发环境迁 Vue 3；最后把 Vite 7→8 作为单独、容易回滚的构建工具升级。**

---

## 4.3 Element UI 2 → Element Plus

**明确推荐。**

Element Plus 是 Vue 3 生态中最直接的 Element UI 继任方案。官方说明：

* 面向 Vue 3；
* 首个 production-ready stable 版本在 2022 年已经发布；
* API 已稳定；
* 提供 Element UI → Element Plus breaking change/migration 支持。

因此管理端：

```text
Element UI 2
      ↓
Element Plus 2.14.x
```

是本次迁移中风险最低的 UI 库决策之一。

---

## 4.4 iView 2 → View UI Plus 还是 Element Plus

这里不建议仅按“名字最像”决策。

### View UI Plus 优点

* 明确来自 iView/View UI lineage；
* Vue 3；
* API/组件名称更可能与现有 iView 页面接近；
* 当前仍有 1.3.24 发布版本。

### 风险

npm 截点显示其生态规模只有约 71 个 dependents、每周下载量仅几千级，明显小于 Element Plus。其开发依赖中仍同时存在 Vue CLI、旧 Babel/Karma/Webpack 等历史工具，说明项目本身现代化程度并不完全等于“Vue 3 + Vite”。

### 推荐决策

用户端先做组件 inventory，然后实施 POC：

```text
若 View UI Plus：
  ≥ 90% 当前关键组件可直接迁
  无项目级 monkey patch
  Vue 3.5 + Vite E2E 全通过
        ↓
  使用 View UI Plus

否则
        ↓
  用户端也迁 Element Plus
```

这不会“合并两个 SPA”。两个 SPA 完全可以独立入口但共享同一 UI 依赖。

长期运维角度，如果两种方案迁移成本接近，**Element Plus 更值得作为统一组件平台**；如果 iView 页面非常多且 View UI Plus 能显著降低模板重写量，则可以保留两套 UI。

---

# 5. Vue 2 专有语法迁移影响

| Vue 2 模式                           | Vue 3 状态      | 迁移方式                                   | xju-OJ 风险  |
| ---------------------------------- | ------------- | -------------------------------------- | ---------- |
| `.native`                          | Removed       | 普通 listener + 组件 `emits`               | 中          |
| `.sync`                            | Removed       | `v-model:xxx` + `update:xxx`           | 高          |
| `slot-scope`                       | 旧语法           | Stage 1 先改为 `v-slot`                   | 中          |
| filters                            | Removed       | imported formatter / computed / method | 中高         |
| `Vue.prototype`                    | Global API 改变 | `app.config.globalProperties`，长期再服务化   | 高          |
| `new Vue()`                        | Removed       | `createApp()`                          | 高          |
| `Vue.util.*`                       | 私有 API        | 必须消除                                   | 高          |
| `value` + `$emit('input')` v-model | 默认契约改变        | `modelValue` + `update:modelValue`     | **编辑器高风险** |
| `vuex-router-sync`                 | 不应继续依赖        | 直接读 `router.currentRoute`/route meta   | 中高         |

Vue 3 官方 migration guide 明确：`.sync` 被新的 `v-model` argument 取代，组件默认 v-model 从 `value/input` 改为 `modelValue/update:modelValue`。

全局 API 也迁移到 app instance；官方对应关系包括：

```text
Vue.prototype -> app.config.globalProperties
Vue.extend    -> removed
new Vue       -> createApp(...)
```

filters 已从 Vue 3 删除，官方建议优先使用 computed/method。

### 对当前编辑器的具体影响

现有 `CodeMirror.vue` 和 `Simditor.vue` 都实现：

```text
props: value
emit: input
```

所以 Vue 3 切换时，这两个组件至少需要本地 compatibility adapter，不能简单替换 Vue 版本后期待 `v-model` 原样工作。

---

# 6. 当前依赖逐项处置表

## 6.1 框架/基础设施

| 当前依赖               | 当前状态              | Stage 1       | 最终状态                        | 处置        |
| ------------------ | ----------------- | ------------- | --------------------------- | --------- |
| Vue 2.x            | EOL               | 固定 `2.7.16`   | `~3.5.41`                   | **升级**    |
| Vue Router 3       | legacy line       | 保留/固定 `3.6.5` | `~5.2.0`                    | **升级**    |
| Vuex 3             | Vue 2 状态库         | 保留            | Vuex `4.1.0` 临时 → Pinia 4.x | **分阶段替换** |
| vue-i18n 7         | 老版本               | 暂保留           | `~11.4.8`                   | **升级**    |
| Webpack 3          | 已远离现代生态           | 删除            | Vite                        | **替换**    |
| Babel 6            | 老工具链              | 能删则删          | 默认不需要                       | **删除**    |
| Yarn Classic       | 老 package manager | 删除            | pnpm `11.22.0`              | **替换**    |
| `vuex-router-sync` | Vuex/Router 耦合    | 保留至 Vue 3 前   | 无                           | **删除**    |

Vue Router 当前 `latest` 为 5.2.0，同时 3.6.5 标为 `legacy`。

Vuex 官方已经将 Pinia 定义为默认状态管理方案，但明确表示 Vuex 3/4 仍维护，并允许 Vuex/Pinia 共存，因此用 Vuex 4 作为 Vue 3 第一个生产版本的过渡层是合理选择。

## 6.2 UI/网络/可视化

| 当前依赖          | 推荐目标                                  | 发布/支持状态                | 支持结束      | 处置                    |
| ------------- | ------------------------------------- | ---------------------- | --------- | --------------------- |
| axios 0.18    | `~1.19.0`                             | Stable                 | 未公布固定 EOL | **升级，保留 API wrapper** |
| iView 2       | View UI Plus `~1.3.24` 或 Element Plus | Stable                 | 未公布固定 EOL | **替换**                |
| Element UI 2  | Element Plus `~2.14.4`                | Stable                 | 未公布固定 EOL | **替换**                |
| ECharts 3     | `~6.1.0`                              | Stable                 | 未公布固定 EOL | **升级**                |
| vue-echarts 2 | `~8.1.0`                              | Stable，v8 为 Vue 3 line | 未公布固定 EOL | **升级**                |

Axios 升级时不得把现有 API wrapper 顺手重写成另一套响应模型；`baseURL='/api'`、CSRF cookie/header 名和 `{error,data}` 处理应先保持不变。当前这些行为已经集中在 API 层，适合利用 characterization test 锁死。

ECharts 最终推荐 6.1.x、Vue-ECharts 8.1.x；vue-echarts v8 已转为 Vue 3 line，若 Stage 1 仍处于 Vue 2，应暂时保持当前 chart stack 或使用其 Vue 2 兼容线，不要提前上 v8。

## 6.3 编辑器/监控/工具依赖

| 当前依赖                    | 推荐目标                                            | 状态                  | 处置策略        |
| ----------------------- | ----------------------------------------------- | ------------------- | ----------- |
| `vue-codemirror-lite`   | CodeMirror 6 + 本地 Vue adapter                   | CodeMirror 6 stable | **替换**      |
| `tar-simditor`          | Tiptap 3 + 本地 EditorAdapter                     | Tiptap 3 stable     | **替换**      |
| `tar-simditor-markdown` | Tiptap extension / 明确 markdown conversion layer | 随 editor POC        | **替换**      |
| `raven-js`              | `@sentry/vue ~10.70.0`                          | 当前正式 SDK            | **替换**      |
| `vue-analytics`         | 本地 `analytics` adapter                          | 不再让 Vue 插件绑定业务      | **删除/替换**   |
| `moment`                | Native `Intl` 优先；复杂日期用 Day.js `~1.11.23`        | Stable              | **替换**      |
| highlight.js 9          | `~11.12.0`                                      | Stable              | **升级**      |
| Font Awesome 4          | FA 7.3.x 或 Element Plus icon                    | Stable              | **替换**      |
| 隐式 `jquery`             | Stage 1 显式声明                                    | 最终随 Simditor 删除     | **临时保留后删除** |
| 隐式 `codemirror` v5      | Stage 1 显式声明                                    | 最终 CM6              | **临时保留后替换** |

不推荐从 `vue-codemirror-lite` 再迁到另一个高度绑定 Vue 生命周期的小众 wrapper。CodeMirror 6 本身是模块化 editor toolkit，建议 xju-OJ 自己维持几十行薄 adapter，使：

```text
OJ Vue component API
        ↓
Local EditorAdapter
        ↓
CodeMirror 6
```

这样未来 Vue/CodeMirror 任一侧升级都不会把业务代码再次锁死。CodeMirror 当前 npm basic package 为 6.0.2。

富文本推荐以 Tiptap 3 为候选，因为它基于 ProseMirror 且提供 Vue 3 integration；但**只有在历史 HTML corpus round-trip 通过后才能落地**。截点 `@tiptap/vue-3` 为 3.30.1。

---

# 7. 推荐的三阶段迁移路径

# P0：行为冻结与兼容性基线

P0 不改产品框架。

必须先完成：

1. 两个 SPA 的 route inventory。
2. iView/Element 组件使用量统计。
3. 搜索：

   * `.native`
   * `.sync`
   * `slot-scope`
   * `Vue.filter`
   * `Vue.prototype`
   * `Vue.util`
   * `new Vue`
   * `require.context`
   * dynamic `require`
   * `process`
   * `Buffer`
4. npm/yarn dependency tree 中 undeclared dependency 审计。
5. 为 login/session/CSRF/提交/后台编辑器建立 Playwright characterization tests。
6. 保存一批真实问题描述、公告、比赛说明，形成 editor HTML corpus。
7. 保存生产 bundle size、首屏、build time 作为性能基线。

**P0 未完成，不进入 Vue 3。**

---

# Stage 1：pnpm + Vite 7 + Vue 2.7.16

## 目标

只解决：

```text
Node 14        -> Node 24 LTS
Yarn Classic   -> pnpm 11
Webpack 3      -> Vite 7
Vue 2.x        -> 固定 2.7.16
```

业务框架/UI 尽量不动。

### 为什么固定 Vue 2.7.16

官方 `plugin-vue2` 要求 `Vue ^2.7.0`；2.7.16 又是 Vue 2 最终版本。

### Stage 1 应删除

```text
webpack
webpack-dev-server
webpack-merge
CommonsChunk/DLL build
html-webpack-plugin
extract-text-webpack-plugin
uglifyjs-webpack-plugin
url-loader
file-loader
旧 Babel pipeline
Yarn lock
```

只有在发现项目仍依赖特殊 Babel transform 时才保留现代 Babel 插件，不应机械地把 Babel 6 整套搬到 Vite。

### Stage 1 成功标准

同一 commit 业务代码下：

```text
Webpack build 行为
       ≈
Vite build 行为
```

而不是“UI 顺便重做”。

---

# Stage 2：Vue 3 产品迁移

建议：

```text
Vue              3.5.41
Vue Router       5.2.0
Vue I18n         11.4.8
Vuex             4.1.0（暂时）
Admin UI         Element Plus 2.14.4
User UI          View UI Plus POC / Element Plus
Vite             暂留 7.3.6
```

`@vitejs/plugin-vue 6.0.8` peer dependency 支持 Vite 5～8，因此 Vue 3 与 Vite 7 可以正常组合，不必为了 Vue 3 同时切 Rolldown。

### 推荐使用 `@vue/compat` 的方式

`@vue/compat 3.5.41` 可以作为**诊断和暂时兼容手段**，但不是最终架构。截点其稳定版本与 Vue 3.5.41 对齐。

Stage 2 退出门槛：

> **production build 中不能仍依赖大量 compat warnings 作为正常运行方式。**

---

# Stage 3：最终平台清理

Stage 2 稳定后，再依次执行：

```text
Vite 7.3 -> 8.2
Vuex 4   -> Pinia
CodeMirror 5 wrapper -> CodeMirror 6
Simditor -> Tiptap
ECharts  -> 6
vue-echarts -> 8
raven-js -> @sentry/vue
moment -> Intl/Day.js
FA4 -> modern icons
vue-analytics -> analytics adapter
```

每一类都应能单独回滚。

---

# 8. 目标 package.json 依赖类别和版本范围

## 8.1 包管理和运行时约束

推荐：

```json
{
  "packageManager": "pnpm@11.22.0",
  "engines": {
    "node": ">=24.11 <25",
    "pnpm": ">=11.22 <12"
  }
}
```

实际 Docker 镜像应进一步固定到经过 CI 验证的 **Node 24 patch + digest**。

不建议在 `package.json` 写：

```text
node >= 24
```

因为这会在未来悄悄接受 Node 25/26/27，失去生产可重复性。

## 8.2 Stage 1

```text
dependencies
  vue                    2.7.16
  vue-router             3.6.5
  vuex                   3.x
  vue-i18n               7.x
  axios                  当前先保留或单独升级
  iview                  当前版本
  element-ui             当前版本
  ...

devDependencies
  vite                    7.3.6
  @vitejs/plugin-vue2     2.3.4
  vitest                  4.1.x（仅适合不依赖 Vue3 VTU 的逻辑测试）
```

对 EOL bridge 依赖建议**精确 pin**而不是 `^`。

## 8.3 最终应用依赖

| 类别          | 推荐范围                                      |
| ----------- | ----------------------------------------- |
| Framework   | `vue ~3.5.41`                             |
| Router      | `vue-router ~5.2.0`                       |
| I18n        | `vue-i18n ~11.4.8`                        |
| HTTP        | `axios ~1.19.0`                           |
| Admin UI    | `element-plus ~2.14.4`                    |
| User UI     | `view-ui-plus ~1.3.24`，仅通过 POC 后          |
| State       | Stage 2 `vuex 4.1.0`；Stage 3 Pinia 4.x    |
| Chart       | `echarts ~6.1.0`, `vue-echarts ~8.1.0`    |
| Monitoring  | `@sentry/vue ~10.70.0`                    |
| Dates       | `dayjs ~1.11.23`，仅确有需求时                   |
| Highlight   | `highlight.js ~11.12.0`                   |
| Icons       | Font Awesome 7.3.x 或 UI library icons     |
| Rich editor | Tiptap Vue 3 3.30.x，POC 后                 |
| Code editor | CodeMirror 6 + required language packages |

## 8.4 最终开发依赖

```text
vite                    ~8.2.1
@vitejs/plugin-vue      ~6.0.8
vitest                  ~4.1.10
@vue/test-utils         ~2.4.11
@playwright/test        ~1.62.1
```

截至截点，Vitest 4.1.10 是 stable/latest，而 Vitest 5 仍处于 beta，因此不应追预发布主线。

Vue Test Utils 2.4.11 是当前 Vue 3 component testing stable line。

Playwright 1.62.1 是 stable/latest，并覆盖 Chromium、Firefox、WebKit。

---

# 9. 目标 Vite 双入口目录结构

推荐：

```text
frontend/
├── index.html
├── admin/
│   └── index.html
│
├── src/
│   ├── entries/
│   │   ├── oj/
│   │   │   └── main.js
│   │   └── admin/
│   │       └── main.js
│   │
│   ├── pages/
│   │   ├── oj/
│   │   └── admin/
│   │
│   └── shared/
│       ├── api/
│       ├── auth/
│       ├── config/
│       ├── ui/
│       ├── editors/
│       ├── analytics/
│       └── monitoring/
│
├── vite.config.mjs
├── package.json
└── pnpm-lock.yaml
```

Vite 官方支持多个 HTML entry，并按照 HTML 文件本身的 resolved path 输出，因此：

```text
frontend/index.html
frontend/admin/index.html
```

可自然得到：

```text
dist/index.html
dist/admin/index.html
```

无需自己写 HtmlWebpackPlugin 等价物。

### Vite 7 与 Vite 8 配置差异

Stage 1 Vite 7 可使用：

```text
build.rollupOptions.input
```

最终 Vite 8 已转 Rolldown，新配置应使用：

```text
build.rolldownOptions.input
```

`build.rollupOptions` 在 Vite 8 中只是 deprecated alias。

---

# 10. Vite base、CDN 和运行时域名设计

## 推荐规则

```text
Vite base = "/"
API       = "/api"
public    = "/public"
assets    = "/assets/..."
```

Vite 官方 `base` 默认就是 `/`，而且 full URL base 会被固化进 build；因此**不要把域名写进 Vite base**。

错误方向：

```text
base: "https://oj.example.edu/"
VITE_API=https://api.example.edu
```

这会造成：

```text
改域名
  ↓
必须重新 vite build
```

推荐：

```text
Frontend image
   ↓
只包含相对 URL
   ↓
Nginx / ingress / DNS
决定真正域名
```

### CDN

如果未来有 CDN：

优先：

```text
https://oj.example.edu/assets/...
        ↓
CDN/edge 根据 /assets 路径缓存
```

而不是在 JS bundle 中写：

```text
https://cdn-old-domain.example/assets/...
```

这样修改域名/CDN provider 不要求重建 frontend。

### runtime-config

若确有运行时配置需求，可以提供：

```text
/runtime-config.js
```

只存非秘密信息，例如：

* Sentry DSN/environment；
* analytics ID；
* feature flag；
* branding。

必须 `no-store` 或 `no-cache`。

**不得放 token、password、backend secret。**

### `/public/` 特别处理

Vite 自带 `publicDir="public"`，其内容会复制到 build 根目录。当前项目的 `/public/` 却属于服务端数据路径，因此建议：

```text
publicDir: false
```

避免未来开发人员误把 Vite public directory 与现有 `/public/` API/资源命名空间混淆。Vite 官方允许 `publicDir:false`。

---

# 11. Vite dev proxy 与 Django Session/CSRF

## 11.1 原则

浏览器仍访问：

```text
http(s)://frontend-dev-host:5173/api/...
```

而不是：

```text
http://backend:8000/api/...
```

Vite 仅在服务器内部代理：

```text
browser
   ↓ same origin
Vite :5173
   ↓ proxy
Django :8000
```

Vite 官方 `server.proxy` 会把匹配路径直接代理给 target。

## 11.2 `/api`

建议保持：

```text
/api -> backend
```

不 rewrite。

Axios 继续：

```text
baseURL = "/api"
xsrfCookieName = "csrftoken"
xsrfHeaderName = "X-CSRFToken"
```

因此：

```text
Set-Cookie: csrftoken=...
      ↓
浏览器存储
      ↓
后续 Axios POST
      ↓
X-CSRFToken: ...
Cookie: csrftoken=...; sessionid=...
```

与生产模型一致。

## 11.3 Cookie

Vite proxy 默认会转发浏览器 Cookie。

但必须实测：

* `sessionid`
* `csrftoken`
* `SameSite`
* `Secure`
* cookie Path
* Set-Cookie response

如果生产 Django 使用 `Secure` Cookie，而本地 Vite 是 HTTP，则应优先使用本地 HTTPS/统一开发入口，而不是为了调试去改变生产 cookie 策略。

## 11.4 Referer/Origin

应尽量保持：

```text
changeOrigin: false
```

这样 Host 不会被 Vite 伪装成 backend target。

但要理解：

> 开发 Referer 的值本来就会是 Vite 开发域名，而不是生产域名。

例如：

```text
Referer: https://oj-dev.example/
Origin:  https://oj-dev.example
```

这是正确行为。

Django 开发配置需要允许该 hostname；如 HTTPS CSRF origin 校验要求，应仅给开发环境加入对应 trusted origin。

**不要因此把生产 `/api` 改为跨域 API。**

## 11.5 `/public`

因为生产 `/public/` 是 Nginx 对数据卷的 alias，而不是 Vite static assets，开发环境更推荐：

```text
Vite /public/
       ↓
本地统一 dev gateway / Nginx
       ↓
真实 public volume
```

而不是让 Vite 自己拥有一个同名 `public/` directory。

---

# 12. pnpm / Corepack 使用方式

## 12.1 本地开发

`package.json` 固定：

```json
{
  "packageManager": "pnpm@11.22.0"
}
```

Node 24 环境可：

```bash
corepack enable
pnpm install
```

`pnpm-lock.yaml` 必须提交。

### Stage 1 lockfile 切换规则

只有在以下全部通过后才删除 `yarn.lock`：

```text
pnpm install
pnpm lint
pnpm test
pnpm build
Playwright characterization suite
```

完成后仓库只保留：

```text
pnpm-lock.yaml
```

不要长期同时维护 Yarn/pnpm 两份 lockfile。

## 12.2 CI

必须：

```text
pnpm install --frozen-lockfile
```

禁止 CI 自动修改 lock。

pnpm 的严格依赖模型会使未声明依赖失败，这是好事，不应全局开启 `shamefully-hoist` 绕过。pnpm 官方明确将“package 只能访问自己 manifest 声明的 dependency”作为核心特性。

---

# 13. Docker：pnpm fetch、offline install 和 BuildKit 缓存

建议 frontend builder 分成：

```text
toolchain
    ↓
lockfile fetch
    ↓
offline dependency install
    ↓
source
    ↓
build
    ↓
nginx runtime
```

而不是：

```text
COPY . .
RUN pnpm install
```

## 推荐逻辑

```dockerfile
# concept only

COPY package.json pnpm-lock.yaml ./

RUN --mount=type=cache,target=/pnpm/store \
    pnpm fetch

COPY . .

RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --offline --frozen-lockfile

RUN pnpm build
```

pnpm 官方专门推荐 `pnpm fetch` 用于 Docker/CI lockfile-only dependency layer，并支持先填充 store、随后 `--offline` 安装。BuildKit cache mount 也是官方 Docker 文档推荐方案。

### Cache key

建议逻辑上隔离：

```text
frontend-pnpm11-node24-linux-amd64
frontend-pnpm11-node24-linux-arm64
```

避免 native dependency 跨平台复用。

### 基础镜像

可以维护：

```text
xju-oj/frontend-build-base
```

只包含：

* Node 24 LTS；
* pnpm 11.22；
* CA cert；
* 必需编译工具。

**不要把项目 `node_modules` 烘进通用 base image。**

否则 lockfile 一变，所谓“基础镜像”反而成为手工依赖快照。

真正应该长期复用的是：

```text
toolchain image
+
pnpm content-addressable store
+
BuildKit cache
```

### 缓存命中目标

修改：

```text
src/pages/oj/views/Problem.vue
```

时应：

```text
pnpm fetch layer: HIT
offline install: HIT/高复用
app build: 重跑
```

修改：

```text
pnpm-lock.yaml
```

时才允许依赖层失效。

---

# 14. Nginx 最终规则

## 14.1 history fallback

语义必须保持：

```nginx
location = /admin {
    return 301 /admin/;
}

location /admin/ {
    try_files $uri $uri/ /admin/index.html;
}

location / {
    try_files $uri $uri/ /index.html;
}
```

同时 `/api`、`/public` 要位于 SPA fallback 之前并使用更明确匹配，防止被 Vue history 捕获。

## 14.2 静态缓存

Vite hashed assets：

```text
/assets/app.a81c9....js
/assets/vendor.92f....css
```

建议：

```text
Cache-Control: public, max-age=31536000, immutable
```

HTML：

```text
/index.html
/admin/index.html
```

建议：

```text
Cache-Control: no-cache
```

因为 HTML 指向带 hash 的 JS/CSS，不能长缓存。

Vite 官方明确指出新部署删除旧 chunk 时可能导致旧页面 dynamic import 失败，并明确建议 HTML 使用 `Cache-Control: no-cache`。

## 14.3 N/N-1 assets

最好保留至少上一版本 hashed assets 一段时间：

```text
release N assets
release N+1 assets
```

并结合：

```text
window.addEventListener('vite:preloadError', ...)
```

在确认属于 version skew 时 reload。

Vite 官方 troubleshooting 同样建议保留旧 chunks 一段时间以避免版本倾斜。

## 14.4 `/public/`

不要默认：

```text
immutable
```

因为当前 `/public/` 是否采用 content-addressed filename 尚未核实。

如果文件名可能原地覆盖：

```text
/public/avatar.jpg
```

那么一年 immutable cache 会产生严重陈旧问题。

---

# 15. 破坏性变更与高风险项

## 15.1 一级风险：必须阻止上线

### Vue 2 → Vue 3

* `Vue.prototype`
* `new Vue()`
* `Vue.util`
* filters
* `.native`
* `.sync`
* v-model contract
* slot syntax
* event/emits behavior

官方 migration guide 将这些列为 Vue 3 breaking changes。

### UI

Element UI/iView 的：

* Form validation；
* Modal/Dialog lifecycle；
* Table；
* Pagination；
* Select；
* Upload；
* notification/message；
* Loading service；

必须逐一行为测试，不能用“页面截图差不多”代替验收。

### 编辑器

最高风险不是 UI，而是：

```text
历史 HTML
↓
新 editor parse
↓
serialize
↓
数据库内容变化
```

必须 corpus round-trip。

### CSRF

任何导致：

```text
csrftoken 消失
X-CSRFToken 缺失
sessionid 不发送
/api 跨域
```

的变化都属于停止条件。

---

## 15.2 二级风险

### pnpm

当前已经确认有至少：

```text
jquery
codemirror
```

两个隐式 direct dependency。

很可能还有更多。

### Vite

老包可能依赖：

* CommonJS side effects；
* Node global；
* loader magic；
* `require.context`；
* dynamic require；
* Webpack alias；
* CSS/Less import quirks。

必须在 Stage 1 暴露，而不是拖到 Vue 3。

### Vite 8 浏览器基线

Vite 当前默认 production browser baseline 包括：

```text
Chrome >= 111
Edge >= 111
Firefox >= 114
Safari >= 16.4
```

如果学校机房存在长期冻结的旧 Chrome/Edge，应在 Stage 3 前明确浏览器 SLA。

---

# 16. 测试和验收标准

# 16.1 测试组合

推荐：

```text
Vitest
  ↓
纯 JS / utility / store / formatter

Vue Test Utils
  ↓
Vue component 行为

Playwright
  ↓
真实 browser
  ↓
真实 Django Session/CSRF/Nginx/history
```

不能用 Vitest mock axios 证明 CSRF 没坏。

真正的 Session/CSRF 兼容边界必须由浏览器 E2E 验证。

---

# 17. 每阶段必须通过的用户端和管理端 E2E

## P0 / Stage 1：用户端

必须覆盖：

1. `/` 正常打开。
2. 用户端所有主要 history deep link 直接刷新不 404。
3. 匿名访问题目列表。
4. 题目详情。
5. 登录。
6. 登录后刷新仍保留 session。
7. logout 后 session 失效。
8. POST/PUT 请求包含 `csrftoken` + `X-CSRFToken`。
9. 故意提供错误 CSRF 时仍被 Django 拒绝。
10. API `{error,data}` 处理行为完全一致。
11. problem list pagination 请求/响应完全一致。
12. `/public/...` 文件访问。
13. 代码编辑器：

    * 输入；
    * language mode；
    * tab；
    * multiline；
    * submit。
14. 提交代码。
15. 等待判题结果。
16. 展示判题状态/时间/内存等字段。
17. Contest：

    * list；
    * detail；
    * problem；
    * submit；
    * rank。
18. 登录失效后 modal/redirect 行为。
19. 全局 Loading/error/message 行为。

## P0 / Stage 1：管理端

必须覆盖：

1. `/admin` → `/admin/`。
2. `/admin/` 登录页面。
3. 管理端 deep link 刷新不 404。
4. admin session。
5. session expiry。
6. 用户 CRUD。
7. Problem：

   * 创建；
   * 修改；
   * 删除；
   * testcase/metadata。
8. CodeMirror 内容编辑。
9. Simditor：

   * HTML 打开；
   * 编辑；
   * 保存；
   * reload。
10. `/api/admin/upload_image/`。
11. `/api/admin/upload_file`。
12. announcement CRUD。
13. contest CRUD。
14. contest problem CRUD。
15. SPJ compile。
16. judge server 页面。
17. SMTP/website config 等当前可见后台功能。

## Stage 2：Vue 3 额外 E2E

在 Stage 1 全部测试基础上增加：

### Vue 语义

* 无 `.native` 遗留；
* 无 `.sync` 遗留；
* 无 `slot-scope` 遗留；
* 无 template filter；
* 无 `new Vue`；
* 无 `Vue.util`；
* compat warning = 0 或仅有书面接受的暂时项。

### UI

用户端与管理端分别验证：

```text
Input
Select
Checkbox
Radio
Form validation
Table
Pagination
Modal/Dialog
Tooltip
Dropdown
Upload
Loading
Message
Notification
Tabs
Date/Time controls
```

### Router

重点验证：

```text
route guard
history
scroll restoration
page title
auth redirect
```

因为当前页面 title 依赖 `vuex-router-sync` 写入 `state.route`。

### Editor

真实历史 corpus：

```text
old DB HTML
   ↓
load
   ↓
do nothing
   ↓
save
   ↓
semantic/normalized diff
```

未经白名单的 HTML 改动必须为 0。

---

## Stage 3 E2E

额外：

1. Chromium。
2. Firefox。
3. WebKit。
4. 学校实际 Chrome/Edge 版本。
5. Vite 8 production build。
6. 首屏、route lazy chunks。
7. N→N+1 部署时打开旧 tab，再点击 lazy route。
8. HTML `no-cache`。
9. hashed asset `immutable`。
10. `/public` cache 行为。
11. runtime-config 修改无需 rebuild。
12. 修改域名无需 rebuild。
13. frontend image rollback。
14. clean clone + frozen lock build。
15. `pnpm fetch` 后 offline install。
16. source-only change 不重新下载全部 dependencies。
17. lockfile change 正确 invalidates dependency layer。

---

# 18. 停止条件

出现任意一个条件，本阶段不得继续合并至生产：

### Stage 1

* Vue 2 + Vite 需要维护自定义 Vite 8 fork 才能运行；
* 只能通过永久 `shamefully-hoist` 才能安装；
* `/api` 被改成跨域；
* CSRF/session 行为改变；
* `/public/` 被 Vite public directory 覆盖；
* `/admin/` history refresh 失败；
* bundle 中出现无法解释的运行时差异。

### Stage 2

* 仍大量依赖 `@vue/compat` warning；
* View UI Plus 需要项目级 monkey patch；
* Element Plus 表单/上传关键流程无法等价；
* editor 历史数据无法 round-trip；
* API wrapper 被迫改变 `{error,data}` 或 pagination；
* `vuex-router-sync` 移除后 title/auth/route 行为仍未测试覆盖。

### Stage 3

* Vite 8 browser baseline 与实际机房浏览器不兼容；
* 新部署频繁造成 stale-chunk 白屏；
* Pinia 与 Vuex 同步期间出现双状态源；
* Docker dependency cache 只有在复制完整源码后才能使用；
* frontend rollback 需要数据库 migration 才能完成。

---

# 19. 回滚原则

## 19.1 每个阶段必须是可部署版本

禁止：

```text
Webpack3
Vue2
iView2
ElementUI2
Vuex3
Simditor
Docker
Nginx
       ↓
一个巨大 commit
       ↓
Vue3 + Vite8 + Pinia + 新 UI + 新 editor
```

推荐：

```text
P0 tests
  ↓
pnpm
  ↓
Vite7
  ↓
Vue3
  ↓
Admin UI
  ↓
User UI
  ↓
Vite8
  ↓
Editor
  ↓
Pinia
```

实际可以合并若干小 commit，但每个 stage 的 tag 必须可独立部署。

## 19.2 镜像回滚

frontend image 使用：

```text
xju-oj/frontend:<git-sha>
```

或：

```text
xju-oj/frontend:<release>
```

根目录部署配置只改变 tag 即可：

```text
FRONTEND_IMAGE_TAG=...
```

不要使用不可追溯的 `latest` 作为生产部署唯一标识。

## 19.3 不在前端升级中做数据 migration

特别是 rich text：

> 新 editor 第一次上线不得批量“格式化”数据库中的历史 HTML。

如果以后确实需要 normalize，应作为单独：

```text
backup
→ dry-run
→ diff
→ migration job
→ rollback
```

的数据工程。

## 19.4 N/N-1 runtime config compatibility

如果 frontend N 读取：

```text
window.__RUNTIME_CONFIG__
```

则 N+1 修改 schema 时至少保持 N 可以继续读，否则 image rollback 可能因为 runtime config 已变化而无法启动。

---

# 20. 待本仓库实测的问题

以下事项目前不能仅凭公开代码静态确认：

| 问题                                           | 为什么必须实测                                                                             |
| -------------------------------------------- | ----------------------------------------------------------------------------------- |
| 实际 resolved `vue` 是否确为 2.7.16                | package.json 仍声明 `^2.5.16`，lock 已看到 `@vue/compiler-sfc 2.7.16`；需确认最终 Vue resolution |
| `.native` 数量                                 | GitHub code search 未必覆盖固定 SHA 全量                                                    |
| `.sync` 数量                                   | 同上                                                                                  |
| `slot-scope` 数量                              | 同上                                                                                  |
| filters 使用量                                  | 入口明确注册，但 template 使用量需统计                                                            |
| `Vue.prototype` 使用量                          | 已确认存在，但需要完整 inventory                                                               |
| `Vue.util` 使用点                               | 属于 Vue 3 硬 blocker                                                                  |
| iView 组件矩阵                                   | 决定 View UI Plus vs Element Plus                                                     |
| Element UI 组件矩阵                              | 决定 Element Plus 工作量                                                                 |
| 自定义 Less theme                               | Vite/CSS/UI replacement 高风险                                                         |
| `require.context` 等 Webpack magic            | Vite blocker                                                                        |
| 隐式依赖数量                                       | 当前至少已确认 jquery/codemirror                                                           |
| Moment locale/timezone/plugin 使用             | 决定能否直接换 Intl/Day.js                                                                 |
| vue-analytics 实际 provider                    | 决定替代 adapter                                                                        |
| Raven/Sentry sourcemap 行为                    | 关系错误定位                                                                              |
| 历史 Simditor HTML corpus                      | editor migration 最大风险                                                               |
| Markdown plugin 的真实语义                        | 不能只按 package name 猜                                                                 |
| HTML sanitizer/XSS pipeline                  | 新 editor 不得削弱安全边界                                                                   |
| `/public/` 文件是否原地覆盖                          | 决定 cache policy                                                                     |
| 所有用户端 history path                           | Nginx/Playwright                                                                    |
| 所有 `/admin/` history path                    | Nginx/Playwright                                                                    |
| 实际支持浏览器                                      | 决定 Vite 8 target                                                                    |
| CSP                                          | Vite modules/runtime-config/Sentry                                                  |
| 生产 CDN 是否存在                                  | 决定 assets 路由                                                                        |
| Django `ALLOWED_HOSTS`                       | Vite dev proxy                                                                      |
| `CSRF_TRUSTED_ORIGINS`                       | HTTPS dev                                                                           |
| SESSION/CSRF cookie `Secure/SameSite/Domain` | 开发/生产 E2E                                                                           |
| frontend runtime Nginx 是否 envsubst           | 决定部署配置注入                                                                            |
| 根 compose build context                      | 与 frontend 独立镜像衔接                                                                   |
| BuildKit CI cache backend                    | 决定远程缓存策略                                                                            |

特别注意一个仓库事实冲突：

`package.json` 的 Vue range 并没有精确锁到 2.7，而 Yarn lock 已出现 `@vue/compiler-sfc@2.7.16`。

因此迁移第一步应把“当前真实 dependency graph”导出留档，再生成 pnpm lock，避免把“Yarn 当前无意间解析出的版本变化”误认为 Vite 回归。

---

# 21. 推荐最终部署形态

前端目标应是一个完全独立的 immutable image：

```text
frontend image
├── nginx
├── dist/
│   ├── index.html
│   ├── admin/index.html
│   └── assets/*
└── nginx template
```

运行时从根部署配置注入：

```text
listen address
external port
server_name/domain
backend upstream
public volume path
image tag
optional runtime config
```

而不是把这些值编译到 JavaScript。

根层：

```text
./deploy.sh
   │
   ├── validate deployment config
   ├── validate docker/buildx
   ├── build/pull frontend image
   ├── build/pull backend image
   ├── build/pull server image
   ├── initialize required dirs/config
   └── docker compose up -d
```

frontend modernisation 本身不需要改变：

```text
Django app label
DB tables/migrations
Redis DB layout
JudgeServer contract
/test_case
Judger UID/GID/seccomp
```

这也是为什么 frontend 应先独立完成：它的主要兼容边界全部可以通过 HTTP/browser E2E 锁死，而不必同时触碰 backend/server。

---

# 22. 最终推荐技术栈

```text
Node
└── 24.x LTS

Package Manager
└── pnpm 11.22.0

Build
└── Vite 8.2.x
    └── @vitejs/plugin-vue 6.0.x

Framework
└── Vue 3.5.x
    ├── Vue Router 5.2.x
    └── Vue I18n 11.4.x

State
├── Vuex 4.1.0              # Vue3 首次迁移临时层
└── Pinia 4.x               # 后续独立迁移

Admin UI
└── Element Plus 2.14.x

User UI
├── View UI Plus 1.3.x      # POC通过才采用
└── Element Plus 2.14.x     # 更保守长期备选

HTTP
└── Axios 1.x
    └── 继续封装 /api + CSRF + response envelope

Charts
├── ECharts 6.1.x
└── vue-echarts 8.1.x

Editors
├── CodeMirror 6 + local adapter
└── Tiptap 3 + local adapter

Observability
└── @sentry/vue 10.x

Testing
├── Vitest 4.1.x
├── Vue Test Utils 2.4.x
└── Playwright 1.62.x

Runtime
└── Nginx
    ├── /
    ├── /admin/
    ├── /api/
    ├── /public/
    └── /assets/
```

---

# 23. 最终决策

### 应做

**采用三阶段方案。**

第一阶段：

```text
Node24 + pnpm11 + Vite7 + Vue2.7.16
```

只完成工具链现代化。

第二阶段：

```text
Vue3.5 + Router5 + i18n11
+ Element Plus
+ View UI Plus/Element Plus user UI
+ Vuex4 transition
```

完成产品框架迁移。

第三阶段：

```text
Vite8 + Pinia + modern editors/charts/Sentry/date/icons
```

完成长期平台清理。

### 不应做

不建议：

```text
Vue2 + Vite8
```

因为官方 Vue2 Vite plugin peer range不支持 Vite 8 且项目已经归档。

不建议：

```text
直接 Vue3.6 RC
```

因为调研截点 Vue 3.6 仍为 RC/Beta，3.5.41 才是正式 `latest`。

不建议：

```text
Node26 Current
```

作为当前生产基线，因为 Node 官方建议生产使用 LTS/Maintenance，而 Node 26 截点仍是 Current。

不建议：

```text
Vue3 + Vite8 + Pinia + 两套 UI + 两个 editor
```

在一个不可回滚版本中同时落地。
