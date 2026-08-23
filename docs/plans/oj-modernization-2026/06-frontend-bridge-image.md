# Step 06：Frontend 桥接镜像与 Nginx

## 目标

把 Vite 桥接产物放入独立 frontend 镜像，建立同源 Nginx 网关和可缓存的构建层；暂不改 Compose 最终拓扑。

## 进入条件

- Step 05 两个 Vite 入口和浏览器合同通过。
- Step 03 已确认 Ubuntu `>=22.04` 宿主可运行 BuildKit。
- backend 测试地址和 public/test_case fixture 可用。

## 文件范围

修改：

- `frontend/Dockerfile`
- `frontend/nginx/nginx.conf`
- `frontend/package.json`

新增：

- `frontend/docker-entrypoint.d/` 或等效 runtime-config 模板
- `frontend/.dockerignore`
- 可选 `frontend/nginx/nginx.conf.template`

## 镜像分层

目标为多阶段但不发布 frontend-deps 基础镜像：

```text
frontend-deps   Node24 + pnpm11 + package.json + pnpm-lock + pnpm fetch
frontend-build  offline install + 源码 + Vite build
frontend-runtime Nginx + dist + runtime config
```

依赖层必须先复制 lockfile，使用 BuildKit cache mount；源码变更不能重新下载 npm 包。最终镜像不含 `node_modules`、`.env`、Secret 或 runtime 数据。

## Nginx 合同

顺序必须是：

```nginx
location = /admin { return 301 /admin/; }
location ^~ /api/ { proxy_pass http://backend-api:8000; }
location ^~ /public/ { alias /data/public/; }
location /admin/ { try_files $uri $uri/ /admin/index.html; }
location / { try_files $uri $uri/ /index.html; }
```

实际配置需保留 Host、X-Forwarded-*、Cookie、CSRF 相关 headers。缓存规则：

- hashed `/assets/`：长期 immutable。
- 两个 HTML：`no-cache`。
- `/runtime-config.js`：`no-store`/`no-cache`。
- `/public/`：未确认内容寻址前不设 immutable。
- 兼容窗口保留 N/N-1 assets。

## 运行时配置

域名、upstream、Sentry 环境、feature flag 等非秘密值用 `/runtime-config.js` 或 Nginx template 注入。Vite build 不写入生产绝对 API 域名。Token、密码、Django Secret 和证书私钥不能进入 runtime-config。

## 计划命令

```bash
docker buildx build --file frontend/Dockerfile --tag xju-oj/frontend:<git-sha> .
docker run --rm -p 127.0.0.1:18080:80 \
  -e APP_DOMAIN=localhost \
  xju-oj/frontend:<git-sha>
curl -fsSI http://127.0.0.1:18080/
curl -fsSI http://127.0.0.1:18080/admin/
```

命令只用于隔离测试；正式部署在 Step 28/29 才接入 Compose。

## 验收

- Dockerfile 不访问 frontend 之外的敏感路径。
- warm build 的 pnpm registry 下载为零或命中已记录 cache；源码-only 修改不触发依赖层。
- `/api` 和 `/public` 不落入 SPA fallback。
- `/admin` 重定向、两个 deep link、HTML/cache header、runtime-config 通过。
- frontend 容器不需要访问 PostgreSQL、Redis 或 JudgeServer。

## 停止条件

- Nginx 需要把 backend 或 JudgeServer 暴露到宿主才能工作。
- 域名变更必须重新编译 JS，且没有批准的例外。
- 运行镜像包含 `.env`、私钥、`node_modules` 或测试/用户数据。
- 为修复旧页面而在此 Step 修改 API/后端协议。

## 回滚

回滚到 Step 05 的旧 frontend 构建或旧镜像；不改 backend/数据库/Redis。

## 完成标志

提交格式建议：

```text
build(frontend): containerize Vite bridge with same-origin nginx
```

完成后才允许删除旧 frontend 部署路径，进入 Step 07。
