# frontend

这是单仓库中的浏览器静态入口，Phase 3 最终运行栈为 Vue 3、Vue Router 5、Pinia、vue-i18n 11、Element Plus 和 Vite 8。

- 用户端和 `/admin/` 管理端保持两个 history 入口。
- Axios 同源基址继续是 `/api`，CSRF Cookie/Header 继续使用 `csrftoken`/`X-CSRFToken`。
- `/public` 由部署层发布后端运行时公开资源；前端不直接读取测试数据。
- Node 固定为 `24.19.0`，pnpm 固定为 `11.22.0`；`pnpm-lock.yaml` 是唯一依赖真源。
- CodeMirror 6 与 Tiptap 通过本地 adapter 保留旧 `value/input/change/update:value`、上传端点和历史 HTML/附件合同。
- `pnpm run build` 生成用户端和管理端双入口；Vue 2/Vite 7 的 Phase 2 immutable image 作为 N-1 回滚资产保留，不再从当前源码重建。
- 运行时域名和非秘密版本信息由 Nginx entrypoint 写入 `/runtime-config.js`，不把 Secret 编译进 bundle。

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
pnpm run lint:modern
pnpm run test:routes
pnpm run build

# the Vite dev-server requires a backend target and keeps /api + /public same-origin
export TARGET=http://Your-backend
pnpm run dev
```

Vue 2、Vuex、Element UI/iView、CodeMirror 5、Simditor、Webpack/Babel 6 和 Yarn Classic 已从最终源码与锁文件移除。

## Screenshots

[Check here.](https://github.com/QingdaoU/OnlineJudge)

## Browser Support

Modern browsers and Internet Explorer 10+.

## LICENSE

[MIT](http://opensource.org/licenses/MIT)
