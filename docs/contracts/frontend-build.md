# Frontend 构建与静态服务契约

## 选定运行时

阶段 02 选择并锁定：

| 项目 | 值 | 证据 |
|---|---|---|
| Node | `14.21.3` | `frontend/.nvmrc`；官方 `node:14.21.3-buster` 隔离构建成功 |
| Yarn | `1.22.x` | 宿主通过 Corepack `1.22.22` 冻结安装成功；Node 14 镜像内 `1.22.19` 冻结安装成功 |
| package | `onlinejudge@2.7.6` | `frontend/package.json` |
| `package.json` SHA-256 | `a85f1c572746a491df98e11fb25de780db1f6dc61df92153920ec99a2f999e4d` | 阶段 02 改动后 |
| `yarn.lock` SHA-256 | `1e344a057d83de5c5aa6f41186d0f623db99e1d8e3800f700e89fd7ef354fccb` | 与阶段 00 完全一致 |
| build 脚本 | `yarn run build:ci` | `build:dll` 后执行 `build`；不改依赖版本 |

选择理由：Node 8.12 是历史 CI 基线，但当前环境没有该运行时；Node 14.21.3 是计划候选且通过了真实 frozen install、DLL 和双入口 production build。Node 24.16.0 的 frozen install/lint 也可运行，但未加兼容参数的 DLL 构建因旧 UglifyJS 与 OpenSSL 3 报 `error:0308010C`，不将 `NODE_OPTIONS=--openssl-legacy-provider` 作为默认发布方案。

## 可复现构建步骤

在宿主已有 Yarn 时：

```bash
cd frontend
node --version                 # 14.21.3
COREPACK_HOME=/tmp/xju-corepack corepack yarn install --frozen-lockfile
COREPACK_HOME=/tmp/xju-corepack corepack yarn run lint
COREPACK_HOME=/tmp/xju-corepack corepack yarn run build:ci
```

镜像构建上下文只允许是 `frontend/`：

```bash
docker build --build-arg GIT_COMMIT=layout-check -t xju-oj-frontend:layout-check frontend
```

`frontend/Dockerfile` 的 build stage 使用 `node:14.21.3-buster`，执行 `yarn install --frozen-lockfile` 和 `yarn run build:ci`；runtime stage 只包含 Nginx、`dist/` 和 `frontend/nginx/nginx.conf`。`frontend/.dockerignore` 额外排除 `.env*`、密钥/证书后缀、`config.yaml`、`application-prod.yml`、`runtime/` 和 `data/`，镜像不读取 backend、server、宿主密钥或数据库/Redis 数据。

## 阶段 02 实测记录

- 宿主 Node `24.16.0` + Corepack Yarn `1.22.22`：`yarn install --frozen-lockfile` 成功，lock hash 未变；`yarn run lint` 成功。
- 宿主 Node 24 未设置兼容参数时，`build:dll` 失败于旧 UglifyJS/OpenSSL；使用 `NODE_OPTIONS=--openssl-legacy-provider` 后 DLL/build 成功。该结果只作为风险记录。
- Node `14.21.3` 官方镜像 + 内置 Yarn `1.22.19`：在隔离临时副本执行 `yarn install --frozen-lockfile`、`yarn run build:dll`、`yarn run build` 全部成功；生成 `dist/index.html` 和 `dist/admin/index.html`。
- 生产构建重复执行两次：文件清单 79 个，文件内容 SHA-256 一致；生成的 `dist/`、DLL、manifest 和 `node_modules/` 均被忽略，未进入 Git。
- `frontend/config/dev.env.js` 现在优先读取 `GIT_COMMIT`；无 Git 时回退到 `unknown`，不阻断 tar/source-only 构建。现有 Git 环境和显式 `GIT_COMMIT=stage02-check` 均已 smoke check。
- `frontend/build/dev-server.js` 在 `TARGET` 未设置时给出明确错误；`/api`、`/public` 代理仍保留原 Referer 语义。
- 使用 `xju-oj-frontend:stage02` 镜像、Nginx 容器挂载 bootstrap public 资源和 Node HTTP backend stub 做了实际路由冒烟：`/`、`/admin/`、`/problem`、`/status/anything`、favicon 和 `/api/website/` 均返回预期 200；`/admin` 返回 301 到 `/admin/`，API body 为 `{"error":null,"data":...}`。
- Nginx `nginx -t` 在为隔离测试提供 `backend-api` hosts 映射后成功；没有 hosts 映射时仅因 upstream DNS 不存在而无法做静态语法启动检查。
- Docker build 通过显式构建环境 proxy 成功；未传 proxy 的一次尝试因 Docker builder 继承不可达本地 proxy 而失败，已归档为环境前置条件。

## 静态入口与代理契约

`frontend/nginx/nginx.conf` 固定以下行为：

| 请求 | 处理 |
|---|---|
| `/`、用户端 history 路由 | `/usr/share/nginx/html` 下静态文件，不存在时回退 `/index.html` |
| `/admin` | 301 到 `/admin/` |
| `/admin/`、`/admin/*` | 静态管理端资源，不存在时回退 `/admin/index.html`；保持 Vue Router base `/admin/` |
| `/api`、`/api/*` | 同源反向代理到 `http://backend-api:8000`；保留原 `/api` 前缀、Host、真实 IP、X-Forwarded-*、Cookie 和 `X-CSRFToken` |
| `/public/*` | 只读 alias `/data/public/`；只挂载公开资源，不挂载 `config/secret.key`、测试数据、数据库、Redis 或 `/judger` |

上传请求继续通过 `/api`，所以 Django Session、CSRF、中间件、统一 `error/data` 包装和特殊上传包装不由 frontend 改写。`JUDGE_SERVER_TOKEN` 不进入 frontend build args、环境变量或静态 JS。

## 路由验收命令

在隔离 Compose 中把 `frontend` 连接到 `backend-api` 后执行：

```bash
curl -I http://127.0.0.1/
curl -I http://127.0.0.1/admin/
curl -I http://127.0.0.1/problem
curl -I http://127.0.0.1/status/anything
curl -I http://127.0.0.1/public/website/favicon.ico
curl -i http://127.0.0.1/api/website/
```

预期：用户端和管理端 history 刷新返回 HTML；公开 favicon 可读；`/api/website/` 仍返回 Django `{"error": ..., "data": ...}`；frontend 无法读 `/data/config/secret.key` 或 `/test_case`。

## 不变约束

- 不改 Vue 双入口、Vue Router history、`/admin/` base、Axios `/api`、`csrftoken`/`X-CSRFToken`。
- 不把 frontend 改成跨域认证、Bearer、CORS 或 Vue 3/Vite。
- 不改 backend API、数据库表名、Django app label、JudgeServer 协议或结果字段。
- 不把旧 `frontend/deploy/nginx.conf` 当作新镜像配置；它保留作迁移前兼容参考，新镜像使用 `frontend/nginx/nginx.conf`。
- `frontend/dist` 中允许出现既有 `/api/admin/test_case` 等浏览器 API 路径；禁止出现 Token 值、数据库连接、secret 文件内容或 `backend-api:8000` 内部服务名。
