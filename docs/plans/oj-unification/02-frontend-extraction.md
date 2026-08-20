# 阶段 02：独立 frontend 构建、静态服务与同源网关

## 目标

让 `frontend/` 成为可独立安装、构建、打包、部署的浏览器模块；后端不再下载或内嵌前端 `dist`，浏览器由 frontend 容器提供静态资源和 `/api`、`/public` 反向代理。第一轮保持 Vue 双入口和现有 API 调用，不做 Vue 3/Vite 重写。

## 进入条件

- 阶段 01 的目录提交已完成。
- `frontend/package.json`、`frontend/yarn.lock` 和 `src/` 内容与原 `OnlineJudgeFE/` hash 一致。
- 阶段 00 的 `docs/contracts/api-compatibility.md` 已列出前端实际调用的端点。
- 已确定一套能复现当前依赖树的 Node/Yarn 版本；在版本未验证前不得擅自更新依赖。

## 当前事实与风险

- `frontend/src/pages/oj/index.js` 和 `frontend/src/pages/admin/index.js` 是两个 Webpack 入口。
- 用户端使用 Vue Router history 模式，管理端基址是 `/admin/`；两者都必须支持浏览器刷新。
- `src/pages/oj/api.js`、`src/pages/admin/api.js` 的 Axios `baseURL` 均为 `/api`，并使用 `X-CSRFToken`/`csrftoken`。
- `build/webpack.base.conf.js` 依赖 `build/vendor-manifest.json` 和 DLL 产物；第一次构建必须先执行 `build:dll`。
- `config/index.js` 的代理目标来自 `TARGET`，并人为设置 Referer；不能只改成裸跨域请求。
- 旧 `deploy/Dockerfile` 使用 Node 6，旧 CI 使用 Node 8.12；当前锁文件包含比项目声明更新的转依赖。必须先验证再锁定。
- `OnlineJudge/Dockerfile` 下载 `oj_2.7.5/dist.zip` 的旧逻辑将在阶段 03 删除，不要在 frontend 中继续发布隐式上游包。

## 步骤 02.1：锁定构建运行时，不升级业务依赖

创建 `frontend/.nvmrc` 或构建镜像中的明确版本（选定值必须以阶段 00 的实测为准）。建议验证矩阵：

```text
Node 8.12（历史 CI 兼容基线）
Node 14.21.x（较新的可维护兼容候选）
Yarn 1.22.x
```

每个候选环境执行：

```bash
cd frontend
rm -rf node_modules dist static/js/vendor.dll.*.js build/vendor-manifest.json
yarn install --frozen-lockfile
npm run build:dll
npm run build
```

选择标准：

1. 安装不改写 `yarn.lock`；
2. DLL manifest 和 `dist/index.html`、`dist/admin/index.html` 生成；
3. 生产资源引用不含失效路径；
4. 构建重复两次的文件清单/非时间戳内容一致；
5. 不需要把 `npm install` 作为替代锁文件安装。

如果 Node 8 由于 TLS、原生依赖或锁文件失败，不要直接升级所有包；记录失败并选定经过验证的兼容 Node，后续另开依赖现代化任务。

## 步骤 02.2：把构建入口变成可脱离 Git 的模块

审查并按需修改：

| 文件 | 处理 |
|---|---|
| `frontend/config/dev.env.js` | `git rev-parse HEAD` 在发布 tar 中可能失败；改为优先读取 `GIT_COMMIT`，无 Git 时使用 `unknown` 或 package 版本，不能阻断构建 |
| `frontend/config/index.js` | `TARGET` 为空时给出明确错误；保留 `/api`、`/public` 代理和 Referer 语义 |
| `frontend/build/webpack.base.conf.js` | 保留两个入口和 alias；确认 `~ -> src/components` 未被实际代码依赖，必要时修正为真实组件目录并单独提交 |
| `frontend/build/webpack.dll.conf.js` | 第一轮保留 DLL 以降低行为变化；将 manifest/产物写入忽略目录或构建临时目录 |
| `frontend/package.json` | 只增加可复现的 `build:ci`（安装后执行 DLL + build）或 `test:build`，不升级依赖、不改产品版本 |
| `frontend/yarn.lock` | 只允许由锁定版本的 Yarn 生成；迁移阶段禁止手工编辑 |

修改后执行：

```bash
cd frontend
GIT_COMMIT=layout-check yarn run build:ci
find dist -maxdepth 3 -type f -print | sort
rg -n '__STATIC_CDN_HOST__|/api|/public|admin/index' dist
```

若生产构建仍需要 `build/vendor-manifest.json`，把它明确列为 build:ci 的中间产物，不提交生成文件。

## 步骤 02.3：建立 frontend Dockerfile

建议新增 `frontend/Dockerfile`，使用多阶段构建：

```text
build stage：固定 Node/Yarn，工作目录 /src，复制 package.json/yarn.lock，冻结安装，build:dll + build
runtime stage：Nginx，复制 /src/dist 到静态根目录
```

要求：

- 构建上下文为 `frontend/`，不读取 backend、server 或宿主密钥；
- 不从 GitHub 下载上游 dist；
- 不在镜像内运行 Django、Dramatiq、编译器或 JudgeServer；
- 生成 `index.html` 和 `admin/index.html`；
- 默认只暴露 Nginx 端口，API 上游通过运行时配置或 Compose 服务名提供。

由于 Nginx 配置需要同一份镜像在开发/生产使用，选择一种明确策略：

1. 构建时固定内部上游名 `backend-api:8000`；或
2. 用环境变量模板 + entrypoint 渲染；

第一轮优先选择固定 Compose 服务名，避免在静态前端镜像中引入复杂模板逻辑。

## 步骤 02.4：重写 frontend Nginx 路由

把旧 `frontend/deploy/nginx.conf` 改成目标配置（可迁移至 `frontend/nginx/nginx.conf`），至少包含：

```nginx
root /usr/share/nginx/html;

location = /admin {
    return 301 /admin/;
}

location /api {
    proxy_pass http://backend-api:8000;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    client_max_body_size 200m;
}

location /public/ {
    alias /data/public/;
}

location /admin/ {
    try_files $uri $uri/ /admin/index.html;
}

location / {
    try_files $uri $uri/ /index.html;
}
```

实际 `proxy_pass` 的尾斜杠、`alias` 的路径和 `/admin` 重写必须用容器内 `curl`/浏览器验证；不能仅凭 Nginx 语法通过就算成功。

安全要求：

- frontend 只读挂载 `runtime/backend/public`；不挂载 `config/secret.key`、测试数据、数据库或 `/judger`；
- `/api/judge_server_heartbeat/` 仍由 backend 接收，不能让 frontend 把它转发到外部公开地址；
- 不把 `JUDGE_SERVER_TOKEN` 注入 frontend 环境或静态 JS；
- 上传请求仍走 `/api`，保持 Django 的认证和大小限制。

## 步骤 02.5：保留 API/认证兼容

第一轮只做必要的路径修正，以下行为不得改变：

- 两个 API 客户端 `baseURL` 继续为 `/api`；
- Axios 的 `xsrfHeaderName` 和 `xsrfCookieName` 继续匹配 Django；
- 用户端登录失效仍根据统一错误包装显示登录模态框；
- 管理端登录失效仍跳转 `login`；
- 上传组件的绝对 `/api/admin/...` 路径继续同源；
- localStorage 的 `authed` 只作为 UI 提示，不被当成安全凭据；
- 路由名称、`/admin/` base 和 history mode 不变。

用 `rg` 检查是否误改成跨域或 Bearer：

```bash
rg -n "baseURL|xsrf|Authorization|Bearer|/api|/public" frontend/src frontend/config frontend/nginx
```

如果希望以后启用真正跨域部署，另建 API v2/CORS 计划；本阶段不得同时引入 Cookie `SameSite`、CORS、CSRF 和认证协议变化。

## 步骤 02.6：前端验收与 UI 冒烟

### 构建验收

```bash
cd frontend
yarn install --frozen-lockfile
npm run lint
npm run build:dll
npm run build
find dist -type f -print | sort
```

### 静态路由验收

在 frontend 容器和 backend-api 可达的隔离 Compose 中：

```bash
curl -I http://127.0.0.1/
curl -I http://127.0.0.1/admin/
curl -I http://127.0.0.1/problem
curl -I http://127.0.0.1/status/anything
curl -I http://127.0.0.1/public/website/favicon.ico
curl -i http://127.0.0.1/api/website/
```

预期：

- `/` 和 `/admin/` 返回对应 HTML；
- history 路由刷新不是 404；
- `/public` 能读默认 favicon/头像但不能读 `/data/config/secret.key`；
- `/api/website/` 的响应包装未被 Nginx 改写。

### 浏览器冒烟清单

使用 Playwright 或人工浏览器逐项记录：

1. 首页公告、题目列表、题目详情；
2. 登录、注册/验证码（若开启）、退出；
3. 个人资料、头像上传、Session 管理、CSRF 写请求；
4. 提交代码后状态页和详情页；
5. 比赛详情、密码、题目、排名、公告；
6. `/admin/login`、仪表盘、用户、题目、比赛、JudgeServer 页面；
7. 题目测试数据上传、导入/导出、富文本图片/文件上传；
8. 确认浏览器 Network 中没有跨域错误、Token、内部服务名或 secret。

## 阶段产物

```text
frontend/Dockerfile
frontend/nginx/nginx.conf（或明确的 frontend/deploy/nginx.conf）
frontend/.dockerignore
frontend/.nvmrc（或等价构建版本声明）
更新后的 frontend/README.md
docs/contracts/frontend-build.md
```

## 停止条件与回滚

- 构建必须依赖未记录的 Node/npm 版本；
- `yarn.lock` 被无意修改；
- `/admin` 刷新、CSRF、上传或 `/public` 失败；
- 静态 JS 中出现 `JUDGE_SERVER_TOKEN`、数据库连接或内部路径；
- 新 Nginx 需要读取后端源码/数据以外的敏感卷。

回滚只恢复 frontend 相关提交和旧的后端静态资源配置；不要删除旧 `dist` 或 runtime 数据。阶段 03 未完成前，保留旧 backend 镜像的前端嵌入方式作为运行回退。
