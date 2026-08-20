# frontend

这是单仓库中的浏览器静态入口，保留原 OnlineJudgeFE 的 Vue 2、Vue Router、Vuex、Axios 和 Webpack 3 基线。

- 用户端和 `/admin/` 管理端仍是两个 history 入口。
- Axios 的同源基址继续是 `/api`，CSRF Cookie/Header 继续使用 `csrftoken`/`X-CSRFToken`。
- `/public` 由部署层发布后端运行时公开资源；前端不直接读取测试数据。
- 当前阶段只完成目录收敛；Node/Yarn、依赖版本、API 路径和旧构建方式不升级。构建入口仍是 `npm run build:dll` 与 `npm run build`，精确版本见 `docs/contracts/version-matrix.md`。

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

Install nodejs **v8.12.0** first.

### Linux

```bash
npm install
# we use webpack DllReference to decrease the build time,
# this command only needs execute once unless you upgrade the package in build/webpack.dll.conf.js
export NODE_ENV=development 
npm run build:dll

# the dev-server will set proxy table to your backend
export TARGET=http://Your-backend

# serve with hot reload at localhost:8080
npm run dev
```
### Windows

```bash
npm install
# we use webpack DllReference to decrease the build time,
# this command only needs execute once unless you upgrade the package in build/webpack.dll.conf.js
set NODE_ENV=development 
npm run build:dll

# the dev-server will set proxy table to your backend
set TARGET=http://Your-backend

# serve with hot reload at localhost:8080
npm run dev
```

## Screenshots

[Check here.](https://github.com/QingdaoU/OnlineJudge)

## Browser Support

Modern browsers and Internet Explorer 10+.

## LICENSE

[MIT](http://opensource.org/licenses/MIT)
