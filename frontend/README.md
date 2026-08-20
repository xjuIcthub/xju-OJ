# frontend

这是单仓库中的浏览器静态入口，保留原 OnlineJudgeFE 的 Vue 2、Vue Router、Vuex、Axios 和 Webpack 3 基线。

- 用户端和 `/admin/` 管理端仍是两个 history 入口。
- Axios 的同源基址继续是 `/api`，CSRF Cookie/Header 继续使用 `csrftoken`/`X-CSRFToken`。
- `/public` 由部署层发布后端运行时公开资源；前端不直接读取测试数据。
- 当前阶段保留 Vue/Webpack 和业务依赖版本，不升级产品依赖。已验证的构建运行时为 Node `14.21.3`（见 `.nvmrc`）和 Yarn `1.22.x`；构建入口是 `yarn run build:ci`（DLL + production build），精确证据见 `docs/contracts/frontend-build.md`。
- Node 24 在旧 UglifyJS 上触发 OpenSSL 兼容错误，因此不作为默认构建运行时；不要用升级依赖掩盖该基线差异。

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

Use Node **14.21.3** and Yarn **1.22.x**. Do not replace the frozen-lockfile install with `npm install`.

```bash
corepack yarn install --frozen-lockfile
yarn run build:ci

# the dev-server requires a backend target and keeps /api + /public same-origin
export TARGET=http://Your-backend
yarn run dev
```

On Windows, set `TARGET` with the shell's environment-variable syntax before running `yarn run dev`. The first build runs the DLL step automatically; `yarn run build:ci` is the reproducible CI entry point.

## Screenshots

[Check here.](https://github.com/QingdaoU/OnlineJudge)

## Browser Support

Modern browsers and Internet Explorer 10+.

## LICENSE

[MIT](http://opensource.org/licenses/MIT)
