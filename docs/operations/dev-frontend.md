# 全栈前端快速迭代

## 目标

开发时让 Vue/Vite 前端运行在宿主机，后端逻辑和判题依赖继续由 Docker 提供。这样修改
`frontend/` 后只触发 Vite HMR，不需要重建前端镜像；backend、worker、judge-server、
PostgreSQL 和 Redis 保持与部署栈相同的服务边界。

## 启动

在仓库根目录运行：

```bash
./deploy.sh --dev frontend
```

行为如下：

1. 按普通部署流程校验 env、准备 secrets、执行 bootstrap/migrate 和 judge token 初始化；
2. 仅启动 `postgres`、`redis`、`backend-api`、`backend-worker`、`judge-server`；
3. 使用开发 Compose override 将 backend-api 仅绑定到 `127.0.0.1:8000`；
4. 在 `frontend/` 执行 `pnpm dev`，默认绑定 `127.0.0.1:5173`；
5. Vite 将 `/api`、`/public` 代理到本地 backend，浏览器仍使用同源路径；
6. Vite 的 `/runtime-config.js` 从同一次部署解析出的非秘密运行时配置生成，并在启动时读取 backend 的 `/api/auth/providers/`；Authentik 开关和本地登录/注册开关与实际 backend 保持一致。

首次启动如果没有依赖目录，会自动执行冻结安装：

```bash
cd frontend && pnpm install --frozen-lockfile
```

然后访问 `http://127.0.0.1:5173/`。Ctrl-C 只停止 Vite 前台进程，不会删除或停止
Docker 数据库、Redis、worker 或 judge-server；需要停止后端时执行定向命令：

```bash
docker compose stop backend-api backend-worker judge-server redis postgres
```

## 配置边界

- 开发模式的 HTTP 端口只绑定 loopback，禁止设置为 `0.0.0.0` 或公网地址；
- `compose.dev.yaml` 不参与生产 `./deploy.sh`，生产仍只有 frontend 服务发布主机端口；
- 开发 backend 使用 `OJ_DEV_MODE=1`，只额外信任本机 Vite origin（例如
  `http://127.0.0.1:5173`），生产 CSRF trusted origins 不放宽；
- OIDC 仍按当前 `.env` 配置执行。若使用生产 Authentik callback，浏览器会跳转到已经配置的
  `auth.icthub.top`，本地 Vite 只负责前端资源和 API 代理；
- 不要把本地 `.env`、secret 文件、Cookie、OIDC code 或 token 提交到仓库。

## 验证

```bash
sh -n deploy.sh
pnpm --dir frontend run lint:modern
pnpm --dir frontend run test:routes
pnpm --dir frontend run build
```

运行中可检查：

```bash
curl --fail http://127.0.0.1:8000/api/website/
curl --fail http://127.0.0.1:5173/
docker compose ps
```
