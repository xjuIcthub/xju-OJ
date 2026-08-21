# Step 05：Vite 7 双入口桥接

## 目标

在 Vue 2.7.16 和旧 UI 仍可用的前提下，用 Vite 7.3.6 替换 Webpack 开发/生产构建，保持两个独立 SPA 和所有同源路径。

## 进入条件

- Step 04 的 pnpm lock、隐式依赖和 Node 24 构建通过。
- Step 01 的 `/api`、`/public`、history、Session/CSRF golden 已存在。
- 暂不升级 Vue、Router、Vuex、i18n、UI 或编辑器。

## 文件范围

新增/修改：

- `frontend/vite.config.mjs`
- `frontend/index.html`
- `frontend/admin/index.html`
- `frontend/src/entries/oj/main.js`
- `frontend/src/entries/admin/main.js`
- `frontend/src/shared/config/**`
- `frontend/package.json`
- `frontend/nginx/nginx.conf`（只在路径需要时）

保留至 Step 06 验收后再删除：

- `frontend/build/**`
- `frontend/config/**`
- Webpack/Babel 配置和 `yarn.lock`

## 双入口合同

```text
frontend/index.html       -> dist/index.html
frontend/admin/index.html -> dist/admin/index.html
```

Vite 配置要求：

- `rollupOptions.input` 同时声明两个入口。
- `base = "/"`。
- `publicDir = false`，避免把 Vite `public/` 与服务端 `/public/` 混淆。
- alias、Less、字体、图片和旧 loader 行为逐项迁移。
- 不把生产域名、API 独立域名或 Secret 编译进 JS。

## 代理合同

开发服务器只代理：

- `/api` → backend 测试地址。
- `/public` → backend/frontend 测试静态地址。

必须保留 Cookie、`X-CSRFToken`、Referer、Origin、Host/Forwarded 的测试行为。生产仍由 Nginx 做同源代理，不在本 Step 引入 CORS。

## 实施顺序

1. 先将现有两个入口改为 Vite 可识别的 HTML/JS，不做组件改写。
2. 迁移 alias、环境变量、CSS/Less、静态资源和动态 import。
3. 复制旧 dev proxy 语义并增加请求日志脱敏。
4. 生成两个 dist，运行同一套浏览器合同。
5. 对 bundle、路由、资源 URL 做差异审查。

## 计划命令

```bash
cd frontend
pnpm add -D vite@7.3.6 @vitejs/plugin-vue2@2.3.4
pnpm install --frozen-lockfile
pnpm run dev -- --host 127.0.0.1
pnpm run build
find dist -maxdepth 2 -type f -name 'index.html' -print
```

若项目脚本不同，先在 `package.json` 增加明确的 `dev`/`build`，不要依赖旧 `build/*.js` 的隐式行为。

## 验收

- `dist/index.html` 和 `dist/admin/index.html` 都存在且可独立刷新。
- `/admin` 301、`/admin/` fallback、用户端 deep link 全通过。
- `/api` 仍为相对路径，Cookie/CSRF 与旧基线逐字段一致。
- `/public` 不被静态构建目录覆盖。
- Vue 2 页面、表单、上传、编辑器、图表功能没有因构建迁移改变。
- 开发和生产构建不读取生产 Secret。

## 停止条件

- 需要 fork `plugin-vue2` 才能维护桥接，或 Vite 7 无法稳定构建现有页面。
- Vite `publicDir` 覆盖服务端 `/public`。
- API 变为跨域、CSRF 失效或 history 刷新返回 404。
- 构建产物依赖机器上的 `node_modules` 或未锁定的全局工具。

## 回滚

保留旧 Webpack 构建入口和 `yarn.lock`，回滚只切回旧构建命令/旧 frontend 镜像；不改后端、数据库或 API。

## 完成标志

提交格式建议：

```text
build(frontend): add Vite 7 dual-entry bridge
```

Vite 7/Vue2 只作为短期桥接，不得在此 Step 顺手进入 Vue3。
