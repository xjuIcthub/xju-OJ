# frontend

这是单仓库中的浏览器静态入口，保留原 OnlineJudgeFE 的 Vue 2、Vue Router、Vuex、Axios 和 Webpack 3 基线。

- 用户端和 `/admin/` 管理端仍是两个 history 入口。
- Axios 的同源基址继续是 `/api`，CSRF Cookie/Header 继续使用 `csrftoken`/`X-CSRFToken`。
- `/public` 由部署层发布后端运行时公开资源；前端不直接读取测试数据。
- Phase 1 bridge 使用 Node `24.19.0`、pnpm `11.22.0` 和 Vite `7.3.6`，保留 Vue 2/Router/Vuex/业务依赖；`yarn.lock` 与 Webpack 路径仍作为回滚资产。
- `pnpm-lock.yaml` 是当前桥接构建真源；`pnpm run build` 生成用户端和管理端双入口，`pnpm run build:legacy` 保留旧 Webpack 构建。
- 运行时域名和非秘密版本信息由 Nginx entrypoint 写入 `/runtime-config.js`，API 继续使用同源 `/api`，不把 Secret 编译进 bundle。

## 原始模块说明

以下保留原 OnlineJudgeFE 的开发说明。

### OnlineJudge Front End
[![vue](https://img.shields.io/badge/vue-2.5.13-blue.svg?style=flat-square)](https://github.com/vuejs/vue)
[![vuex](https://img.shields.io/badge/vuex-3.0.1-blue.svg?style=flat-square)](https://vuex.vuejs.org/)
[![echarts](https://img.shields.io/badge/echarts-3.8.3-blue.svg?style=flat-square)](https://github.com/ecomfe/echarts)
[![iview](https://img.shields.io/badge/iview-2.8.0-blue.svg?style=flat-square)](https://github.com/iview/iview)
[![element-ui](https://img.shields.io/badge/element-2.0.9-blue.svg?style=flat-square)](https://github.com/ElemeFE/element)
[![Build Status](https://travis-ci.org/QingdaoU/OnlineJudgeFE.svg?branch=master)](https://travis-ci.org/QingdaoU/OnlineJudgeFE)

>### A multiple pages app built for OnlineJudge. [Demo](https://qduoj.com)

## Features

+ Webpack3 multiple pages with bundle size optimization
+ Easy use simditor & Nice codemirror editor
+ Amazing charting and visualization(echarts)
+ User-friendly operation
+ Quite beautiful：)

## Get Started

Use Node **24.19.0** and pnpm **11.22.0**. Do not replace the frozen-lockfile install with `npm install`.

```bash
corepack pnpm@11.22.0 install --frozen-lockfile
pnpm run lint
pnpm run build

# the Vite dev-server requires a backend target and keeps /api + /public same-origin
export TARGET=http://Your-backend
pnpm run dev

# legacy rollback build, retained until Phase 3
pnpm run build:legacy
```

The bridge keeps `yarn.lock` and the old Webpack configuration. The `tar-simditor` Git subdependencies are inherited pinned legacy inputs and are explicitly deferred to the Phase 3 editor migration.

## Screenshots

[Check here.](https://github.com/QingdaoU/OnlineJudge)

## Browser Support

Modern browsers and Internet Explorer 10+.

## LICENSE

[MIT](http://opensource.org/licenses/MIT)
