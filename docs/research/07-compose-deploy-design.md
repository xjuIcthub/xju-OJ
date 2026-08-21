# xju-OJ 最终 Docker Compose 与 `deploy.sh` 生产级现代化专项调研报告

**固定研究基线**

* 仓库：`xjuIcthub/xju-OJ`
* 分支：`main`
* 提交：`2d84d089bcd8ea90d5836c00d7c46e6de47697fc`
* 调研截点：**2026-08-20**
* 本报告范围：最终 Docker Compose、镜像组织、运行拓扑、配置/Secret、初始化、健康检查、BuildKit 缓存、部署与回滚
* 本报告不修改代码、不创建 PR

---

# 1. 执行摘要

## 1.1 最终结论

推荐将 xju-OJ 明确拆成：

**3 个业务模块 → 3 个可发布应用镜像 → 4 个长期运行的业务容器。**

| 层次             | 推荐结果                                                                         |
| -------------- | ---------------------------------------------------------------------------- |
| 业务模块           | `frontend`、`backend`、`server`                                                |
| 应用镜像           | `xju-oj-frontend`、`xju-oj-backend`、`xju-oj-server`                           |
| 长期运行容器         | `frontend`、`backend-api`、`backend-worker`、`judge-server`                     |
| 一次性 backend 角色 | `bootstrap-runtime`、`migrate`、`configure-judge-token`、`create-initial-admin` |
| 基础设施           | `postgres`、`redis`                                                           |
| 宿主机公开端口        | **仅 frontend**                                                               |
| backend        | Compose 内网 `backend-api:8000`                                                |
| JudgeServer    | Compose 内网 `judge-server:8080`                                               |
| 浏览器 API        | 始终为同源 `/api`                                                                 |

这里最关键的是：**“三个镜像”并不等于“三个容器”。** `backend-api` 和 `backend-worker` 应当使用完全相同的 backend 镜像，只通过 `command`/entrypoint mode 区分进程角色；迁移和初始化也复用同一镜像执行一次性容器。

固定提交实际上已经朝这个方向演进：backend Dockerfile 只生成一个 Python 应用镜像，而入口脚本已经支持 `api`、`worker`、`migrate`、`bootstrap-runtime`、`configure-judge-token`、`create-initial-admin` 等模式。

因此，不应重新引入 supervisord 将 API 与 Dramatiq Worker 塞回一个容器。

## 1.2 推荐最终生产拓扑

```text
                          Internet / Campus Network
                                    │
                         HTTP / HTTPS only
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │ frontend                  │
                    │ Nginx + Vite static files │
                    │ :80 / :443 in container   │
                    └──────────┬────────────────┘
                               │ edge network
                     /api      │
                               ▼
                    ┌───────────────────────────┐
                    │ backend-api               │
                    │ SAME backend image        │
                    │ Gunicorn :8000            │
                    └──────┬─────────┬──────────┘
                           │         │
                    core   │         │ heartbeat
                           │         ▼
              ┌────────────┘   ┌──────────────────┐
              │                │ judge-server      │
              │                │ SAME server image │
              │                │ Flask/Gunicorn    │
              │                │ internal :8080    │
              │                └─────────┬────────┘
              │                          │
              │                    /test_case:ro
              │                    /judger
              │                    /log
              │
      ┌───────▼─────────┐
      │ backend-worker  │
      │ SAME backend    │
      │ image           │
      │ Dramatiq        │
      └───────┬─────────┘
              │
        ┌─────┴──────────────┐
        ▼                    ▼
┌───────────────┐    ┌─────────────────┐
│ PostgreSQL    │    │ Redis           │
│ internal 5432 │    │ internal 6379   │
│ persistent    │    │ DB1 + DB4       │
└───────────────┘    └─────────────────┘


一次性任务，不长期运行：

xju-oj-backend image
       │
       ├─ bootstrap-runtime
       ├─ migrate
       ├─ configure-judge-token
       └─ create-initial-admin
```

最终应形成 **7 类运行角色**：

1. `frontend`
2. `backend-api`
3. `backend-worker`
4. `backend-migrate/bootstrap`，一次性
5. `judge-server`
6. `postgres`
7. `redis`

---

# 2. 当前仓库事实

## 2.1 根 Compose 仍属于旧部署模型

固定提交下的根 `docker-compose.yml` 仍然：

* 使用 `redis:4.0-alpine`
* 使用 `postgres:10-alpine`
* Judge 使用远程 `judge:1.6.1`
* backend 使用远程 `backend:1.6.1`
* backend 直接发布宿主机 `80 -> 8000`
* backend 直接发布宿主机 `443 -> 1443`
* JudgeServer 不发布宿主端口
* `/test_case` 已为只读
* `/judger`、`/log` 使用宿主目录
* Judge 容器具有 `read_only: true`、`tmpfs:/tmp` 和既有 `cap_drop`

这些均由固定提交的根 Compose 直接确认。

因此，**最终 Compose 不能在旧文件上继续堆补丁；应替换为“本仓库构建/拉取三个应用镜像 + Compose 编排运行角色”的模型。**

## 2.2 backend 已经具备“一个镜像，多角色运行”的基础

backend Dockerfile：

* Python 3.12 Alpine
* 单镜像
* `ENTRYPOINT=/app/deploy/entrypoint.sh`
* 默认 `CMD ["api"]`
* 已使用 BuildKit cache mount

入口脚本则已经明确区分：

```text
bootstrap-runtime
migrate
configure-judge-token
create-initial-admin
api
worker
manage
```

**已核实事实：** 这与最终推荐的 `backend-api`、`backend-worker`、一次性 migrate 容器完全一致。

## 2.3 Redis DB 分工已经写死在应用设置中

当前 Django 设置明确：

* Session/cache 使用 Redis **DB 1**
* Dramatiq Broker 使用 Redis **DB 4**
* Dramatiq Result Backend 使用 Redis **DB 4**

因此 Redis 升级和 Compose 重构必须保持：

```text
redis://redis:6379/1 → Session / cache / waiting_queue
redis://redis:6379/4 → Dramatiq broker / result
```

不得趁现代化迁移顺手改 DB 编号。

## 2.4 frontend 已经具备正确的同源网关方向

当前 frontend Nginx 已经：

* `/api` → `http://backend-api:8000`
* `/api/` → `backend-api:8000`
* `/admin` → `/admin/`
* `/admin/` 保留 SPA history fallback
* `/public/` 单独映射
* `/` 为前端 SPA fallback

这说明最终方案**不需要重新发明浏览器到后端的寻址方式**，只需要把当前静态 Nginx 配置模板化。

## 2.5 JudgeServer 安全边界必须原样保住

仓库 `server/README.md` 已明确：

* `judge-server/` 负责 `/judge`、`/compile_spj`、`/ping` 和 heartbeat
* `judger/` 是 C/Seccomp 核心
* `/test_case` 必须只读
* `/judger`、`/log`、`/test_case` 权限边界不能弱化
* 用户代码不能以 root 运行
* Token 继续 SHA-256 摘要
* JudgeServer 与 Judger 必须保持单一源码边界

当前 JudgeServer 镜像创建了固定运行用户：

* `compiler`: UID 901
* `code`: UID 902
* `spj`: UID 903

入口脚本还明确设置 `/judger/run` 和 `/judger/spj` 权限。

**因此 Compose 重构不能为了“安全硬化”而盲目添加可能破坏 setuid/setgid/Seccomp 的限制。先保持现边界，再单独做 Judge security hardening 测试。**

---

# 3. 官方支持与版本矩阵

> 以下状态均以 **2026-08-20** 为访问日期。
> Vue/Vite/pnpm 的具体升级版本应由 frontend 专项报告决定；这里仅讨论部署层直接依赖。

| 组件                    | 2026-08-20 官方状态                       |           支持结束 | 本报告推荐                   | 原因                                                              |
| --------------------- | ------------------------------------- | -------------: | ----------------------- | --------------------------------------------------------------- |
| Docker Engine 29.7.2  | 正式发布，2026-08-05；Docker 不称其为 LTS       |    官方未公布固定 EOL | **29.7.2**              | 当前 29 系列补丁，含 BuildKit 0.32.2，修复 29.7.0 pull 回归。                 |
| Docker Compose 5.5.0  | Latest 正式 release，2026-08-17；无 LTS 概念 |    官方未公布固定 EOL | **5.5.0，先经 staging 验证** | 新 digest reconciliation 与本项目镜像追踪高度相关；但首次使用可能重建已有容器，必须纳入升级计划。    |
| Nginx 1.30.4          | 官方明确称 **stable**，2026-07-15           |     官方未给固定 EOL | **1.30.4 stable**       | 与 1.31.3 mainline 相比，gateway 场景优先 stable；1.30.4 含 2026-07 安全修复。 |
| PostgreSQL 18.4       | Supported/current                     | **2030-11-14** | **最终目标 18.4**           | 五年支持窗口最长，已经 GA 近一年；19 仍为 Beta，不用于生产。                            |
| PostgreSQL 10.23      | EOL                                   | **2022-11-10** | 仅迁移过渡                   | 当前 Compose 为 PostgreSQL 10，已经长期 EOL。                            |
| Redis Open Source 8.2 | **GA**                                | **2030-09-01** | **8.2.7**               | 8.2 官方有明确长期 EOL；8.4/8.6/8.8 EOL 仍 TBD。                          |
| Redis 8.8             | GA                                    |            TBD | 暂不选                     | 功能更新但无明确 EOL，OJ 用不到新功能。                                         |

### 重要术语说明

Redis Open Source 官方版本管理页对 8.2 的状态写的是 **GA**，而不是 LTS。Redis Cloud 的另一套产品生命周期才将 8.2 标为 LTS，因此**本报告不把 Redis Open Source 8.2 擅自称为 LTS**。

PostgreSQL 官方同样使用“Supported”及五年支持周期，而不是 Django 风格的 LTS 名称。

### Redis 8 的许可证变化

Redis 8 起可选择：

* RSALv2
* SSPLv1
* AGPLv3

而 Redis 7.2 及以前为 BSD-3-Clause。

这对普通自建 OJ 使用 Redis 官方二进制通常不会阻止部署，但因为是从 Redis 4 的 BSD 时代跨到 Redis 8，**正式升级前应由项目维护者确认组织的开源许可证接受政策。**

---

# 4. 推荐目录树

```text
xju-OJ/
├── compose.yaml
├── compose.dev.yaml
├── compose.tls.yaml                 # 可选：frontend 自终结 TLS
├── .env.example
├── deploy.sh
│
├── deploy/
│   ├── nginx/
│   │   ├── default.conf.template
│   │   ├── tls.conf.template
│   │   └── snippets/
│   │       ├── proxy.conf
│   │       └── security-headers.conf
│   ├── health/
│   │   └── README.md                # 健康语义说明，不一定需要脚本
│   ├── smoke/
│   │   ├── http-smoke.sh
│   │   └── judge-smoke.sh
│   └── ops/
│       ├── record-release.sh
│       └── rollback.sh
│
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── ...
│
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── deploy/
│   │   └── entrypoint.sh
│   └── ...
│
└── server/
    ├── Dockerfile                   # 推荐最终统一 server build context
    ├── .dockerignore
    ├── judge-server/
    └── judger/
```

## 为什么建议将最终 server Dockerfile 放在 `server/`

当前 JudgeServer Dockerfile 中存在：

```dockerfile
COPY Judger/ /app/
```

而仓库当前明确要求源码边界是：

```text
server/judge-server/
server/judger/
```

并明确禁止重新复制第二份 Judger 源码。

因此最终最稳妥的构建上下文是：

```text
context: ./server
dockerfile: Dockerfile
```

让 Dockerfile 明确从：

```text
judger/
judge-server/server/
```

构建一个最终 `xju-oj-server` 镜像。

这是当前迁移中的一个**必须实测项**。

---

# 5. Compose 服务、网络和卷设计

## 5.1 服务表

| Compose service           | 镜像                  | 长期运行 | 宿主端口                | 主要依赖                              | 主要挂载                             |
| ------------------------- | ------------------- | ---: | ------------------- | --------------------------------- | -------------------------------- |
| `frontend`                | `xju-oj-frontend`   |    是 | **HTTP/HTTPS only** | backend-api                       | `/public:ro`、可选 TLS secrets      |
| `backend-api`             | `xju-oj-backend`    |    是 | **无**               | postgres/redis                    | backend runtime                  |
| `backend-worker`          | 同一 `xju-oj-backend` |    是 | **无**               | postgres/redis，建议 judge ready 后启动 | backend runtime                  |
| backend migrate/bootstrap | 同一 `xju-oj-backend` |    否 | 无                   | postgres/redis                    | backend runtime + secrets        |
| `judge-server`            | `xju-oj-server`     |    是 | **无**               | backend-api                       | `/test_case:ro`、`/judger`、`/log` |
| `postgres`                | 官方 PostgreSQL       |    是 | **无**               | 无                                 | postgres data                    |
| `redis`                   | 官方 Redis            |    是 | **无**               | 无                                 | redis data                       |

**禁止出现：**

```yaml
backend-api:
  ports:
    - "8000:8000"

judge-server:
  ports:
    - "8080:8080"
```

Compose 网络内的服务并不依赖宿主 `ports` 才能互相通信，因此 `8000` 和 `8080` 只需要容器内部监听。

## 5.2 网络

推荐两个网络：

```text
edge
  frontend
  backend-api

core
  backend-api
  backend-worker
  judge-server
  postgres
  redis
```

这样：

* frontend 无法直接连接 PostgreSQL
* frontend 无法直接连接 Redis
* frontend 无法直接连接 JudgeServer
* backend-api 是 edge 与 core 的唯一业务桥梁
* 浏览器永远只看到 frontend

不建议第一阶段设置 `internal: true` 强制断互联网，因为 backend 是否需要 SMTP、Webhook、CDN 或其他外部服务仍需仓库实测。

## 5.3 持久化目录

推荐以：

```text
${RUNTIME_ROOT}/
├── backend/
│   ├── public/
│   ├── upload/
│   ├── test_case/
│   └── ...
├── postgres/
├── redis/
├── judge/
│   ├── judger/
│   └── log/
├── secrets/
└── deployments/
    ├── current.json
    ├── previous.json
    └── history/
```

统一管理。

### 建议挂载

| 宿主                                  | 容器                      | 模式     | 属性                    |
| ----------------------------------- | ----------------------- | ------ | --------------------- |
| `${RUNTIME_ROOT}/backend`           | `/data`                 | RW     | backend API/worker    |
| `${RUNTIME_ROOT}/backend/public`    | frontend `/data/public` | **RO** | `/public/`            |
| `${RUNTIME_ROOT}/backend/test_case` | judge `/test_case`      | **RO** | 强制兼容边界                |
| `${RUNTIME_ROOT}/judge/judger`      | `/judger`               | RW     | Judge scratch/runtime |
| `${RUNTIME_ROOT}/judge/log`         | `/log`                  | RW     | Judge log             |
| `${RUNTIME_ROOT}/postgres`          | PostgreSQL PGDATA       | RW     | **关键数据**              |
| `${RUNTIME_ROOT}/redis`             | `/data`                 | RW     | **关键数据**              |

### `/judger` 的特殊性质

当前 JudgeServer entrypoint 每次启动都会执行清理 `/judger/*`。

因此：

**`/judger` 是运行工作区，不应放测试数据、Secret 或不可恢复文件。**

`deploy.sh` 绝不能把 `/judger` 和整个 `${RUNTIME_ROOT}` 混为一谈执行递归删除。

---

# 6. backend API 与 Worker 是否应该同容器

## 6.1 不推荐

把 Gunicorn 与 Dramatiq Worker 强行放入同一个容器，会产生：

* 两个生命周期不同的长进程
* API 与 Worker 无法独立重启
* API 与 Worker 无法独立扩容
* 一个 Worker OOM/崩溃可能导致 API 一起重启
* 一个 API 部署动作会强制中断正在执行的后台任务
* healthcheck 无法明确表达到底在检查哪个角色
* PID 1 需要 supervisord/s6 等额外进程管理器
* 日志和资源限制难以区分
* Kubernetes/Compose 等容器编排层无法分别调度

Docker 官方容器实践同样建议一个容器承担一个主要 concern；需要多个进程虽然技术上可行，但不应成为默认架构。

## 6.2 推荐折中

**一个 backend 镜像，两个长期容器。**

```text
xju-oj-backend:${RELEASE_TAG}
        │
        ├── backend-api
        │      command: api
        │
        ├── backend-worker
        │      command: worker
        │
        └── one-shot
               migrate
               bootstrap-runtime
               configure-judge-token
               create-initial-admin
```

这既满足“backend 只维护一个 Dockerfile/一个镜像”，又保持生产进程边界。

当前仓库 entrypoint 已经直接支持这个模型，因此这是**低风险顺势改造，而不是重新架构 backend**。

---

# 7. `.env.example` 推荐变量表

`.env` 应保存**非 Secret 配置和 Secret 文件路径**，不能保存真正的生产密码/token。

| 变量                            |           必填 | 示例                                      | 用途                                |
| ----------------------------- | -----------: | --------------------------------------- | --------------------------------- |
| `COMPOSE_PROJECT_NAME`        |            是 | `xju-oj`                                | Compose project namespace         |
| `APP_DOMAIN`                  |            是 | `oj.example.edu`                        | Nginx server_name                 |
| `PUBLIC_BASE_URL`             |            是 | `https://oj.example.edu`                | backend 生成绝对 URL / trusted origin |
| `HTTP_BIND_ADDRESS`           |            是 | `0.0.0.0`                               | frontend host binding             |
| `HTTP_PORT`                   |            是 | `80`                                    | host HTTP                         |
| `HTTPS_PORT`                  |       TLS 模式 | `443`                                   | host HTTPS                        |
| `RUNTIME_ROOT`                |            是 | `/srv/xju-oj`                           | 数据根目录                             |
| `IMAGE_REGISTRY`              |            是 | `registry.example.edu/xju-oj`           | 镜像仓库                              |
| `RELEASE_TAG`                 |            是 | `2026.08.20-abc1234`                    | 不可变 release tag                   |
| `DEPLOY_MODE`                 |            是 | `pull`                                  | `build` / `pull`                  |
| `POSTGRES_DB`                 |            是 | `onlinejudge`                           | DB 名                              |
| `POSTGRES_USER`               |            是 | `onlinejudge`                           | DB 用户                             |
| `POSTGRES_PASSWORD_FILE`      |            是 | `/etc/xju-oj/secrets/postgres-password` | 宿主 Secret 文件                      |
| `DJANGO_SECRET_KEY_FILE`      |            是 | `/etc/xju-oj/secrets/django-secret`     | Django secret                     |
| `JUDGE_SERVER_TOKEN_FILE`     |            是 | `/etc/xju-oj/secrets/judge-token`       | Judge token                       |
| `INITIAL_ADMIN_USERNAME`      |           首装 | `root`                                  | 首次管理员                             |
| `INITIAL_ADMIN_PASSWORD_FILE` |           首装 | `/etc/xju-oj/secrets/admin-password`    | 管理员密码                             |
| `TLS_MODE`                    |            是 | `external`                              | `external` / `frontend`           |
| `TLS_CERT_FILE`               | frontend TLS | `/etc/.../fullchain.pem`                | TLS cert                          |
| `TLS_KEY_FILE`                | frontend TLS | `/etc/.../privkey.pem`                  | TLS key                           |
| `DEPLOY_WAIT_TIMEOUT`         |            否 | `180`                                   | Compose wait timeout              |
| `RELEASE_RETENTION`           |            否 | `3`                                     | 保留可回滚镜像数                          |

生产 `.env` 中：

```dotenv
POSTGRES_PASSWORD_FILE=/etc/xju-oj/secrets/postgres-password
```

可以。

下面这种不应使用：

```dotenv
POSTGRES_PASSWORD=real-production-password
JUDGE_SERVER_TOKEN=real-token
```

Docker 官方明确建议敏感信息使用 Compose secrets，Secret 按服务授权并挂载至 `/run/secrets/<name>`；官方 PostgreSQL 镜像也支持 `_FILE` convention。

---

# 8. 必填变量与 `${VAR:?message}`

不能只靠 `deploy.sh` 手写检查；**Compose 文件自身也应 fail closed。**

例如：

```yaml
name: "${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME is required}"

services:
  frontend:
    image: "${FRONTEND_IMAGE_REF:?frontend image reference is required}"
    ports:
      - "${HTTP_BIND_ADDRESS:?HTTP_BIND_ADDRESS is required}:${HTTP_PORT:?HTTP_PORT is required}:80"

  postgres:
    environment:
      POSTGRES_DB: "${POSTGRES_DB:?POSTGRES_DB is required}"
      POSTGRES_USER: "${POSTGRES_USER:?POSTGRES_USER is required}"

volumes:
  backend-data:
    driver_opts:
      device: "${RUNTIME_ROOT:?RUNTIME_ROOT is required}/backend"
```

Docker Compose 官方定义：

```text
${VAR:?error}
```

表示变量未定义**或为空字符串**时直接报错退出。

特别建议对以下变量使用 `:?`：

```text
COMPOSE_PROJECT_NAME
APP_DOMAIN
PUBLIC_BASE_URL
HTTP_BIND_ADDRESS
HTTP_PORT
RUNTIME_ROOT
IMAGE_REGISTRY
RELEASE_TAG
POSTGRES_DB
POSTGRES_USER
```

不要给 `RUNTIME_ROOT` 设计危险的默认值，例如：

```yaml
${RUNTIME_ROOT:-/}
```

---

# 9. Vite 构建变量与 Nginx 运行时变量的边界

这是实现“换域名不重建前端”的关键。

## 9.1 Vite：只保存真正的构建时配置

Vite 官方说明 `import.meta.env` 会在构建期间被**静态替换**；`VITE_*` 还会被暴露到浏览器 bundle。

因此不应这样设计：

```text
VITE_API_URL=https://old-domain.example/api
VITE_APP_DOMAIN=old-domain.example
```

否则每次换域名必须重新 `vite build`。

### 推荐

浏览器继续：

```text
/api/...
```

或者：

```javascript
window.location.origin
```

而不是写入绝对 backend URL。

Vite 构建期只负责类似：

```text
VITE_BUILD_VERSION
VITE_FEATURE_XXX
VITE_SENTRY_PUBLIC_DSN
```

这类真正属于 bundle 的配置。

## 9.2 Nginx：负责运行时网络配置

运行时变量：

```text
APP_DOMAIN
PUBLIC_BASE_URL
BACKEND_UPSTREAM
TLS mode
```

由 Nginx template 注入。

Docker 官方 Nginx 镜像已经内建 template/envsubst 功能：

```text
/etc/nginx/templates/*.template
        ↓ envsubst
/etc/nginx/conf.d/*.conf
```

因此 frontend 镜像应该内置：

```text
/etc/nginx/templates/default.conf.template
```

其中包含：

```nginx
server_name ${APP_DOMAIN};

location /api/ {
    proxy_pass http://backend-api:8000;
}
```

容器启动时再渲染。

### 结果

修改：

```dotenv
APP_DOMAIN=new.example.edu
HTTP_PORT=8080
```

后只需要：

```text
docker compose config --quiet
docker compose up -d --wait
```

**不执行 `docker compose build`。**

---

# 10. TLS 方案

## 10.1 方案 A：外部反向代理终结 TLS —— 默认推荐

适合：

* 一台服务器运行多个服务
* 已有 Caddy/Nginx/HAProxy/Traefik
* 学校统一网关
* 云负载均衡
* 证书集中管理
* ACME 已由外部系统负责

拓扑：

```text
Internet
    │ 443
    ▼
external reverse proxy
    │ HTTP / loopback
    ▼
frontend
    │
backend-api
```

此模式建议：

```dotenv
TLS_MODE=external
HTTP_BIND_ADDRESS=127.0.0.1
HTTP_PORT=18080
PUBLIC_BASE_URL=https://oj.example.edu
```

本 Compose 内：

* frontend 仍是唯一有 `ports:` 的业务容器
* backend/server 完全不发布
* TLS 私钥不进入 xju-OJ Compose

这是运维边界最干净的模式。

## 10.2 方案 B：frontend Nginx 自己终结 TLS

适合：

* 单机独立 OJ
* 没有外部 gateway
* 希望 `./deploy.sh` 后完整提供 80/443

使用：

```text
compose.yaml
+
compose.tls.yaml
```

证书作为只读 Secret/文件挂载：

```text
/run/secrets/tls_cert
/run/secrets/tls_key
```

不要：

* COPY 私钥进镜像
* 将私钥放 `.env`
* 将私钥写 Git
* deploy.sh 自动生成自签生产证书

---

# 11. Healthcheck 与依赖关系

Docker Compose 官方明确指出：

**`depends_on` 默认只等待容器 running，而不等待服务 ready。**

需要 readiness 时应使用：

```yaml
condition: service_healthy
```

一次性初始化可使用：

```yaml
condition: service_completed_successfully
```

## 11.1 推荐依赖 DAG

```text
postgres ──healthy──┐
                    ├──> backend-api healthy ──> frontend
redis ─────healthy──┘               │
                                    └──> judge-server healthy
                                               │
postgres ──healthy──┐                         │
redis ─────healthy──┼─────────────────────────┴──> backend-worker
```

**严禁：**

```text
backend-api waits judge healthy
judge health waits backend-api heartbeat
```

否则产生循环依赖。

## 11.2 当前 Judge health 的特殊问题

JudgeServer 当前 Docker HEALTHCHECK 实际运行 `service.py`。

`service.py` 会：

1. 读取 backend URL
2. 带 `X-JUDGE-SERVER-TOKEN`
3. 向 backend 发 heartbeat
4. backend 返回 `error=false` 才算成功

因此其语义实际上是：

**“JudgeServer → backend heartbeat readiness”**

而不是纯粹：

**“JudgeServer 本地 Flask liveness”**

最终推荐区分：

```text
liveness  → POST /ping 或本地进程检查
readiness → heartbeat backend
```

第一阶段即使不修改 Judge image，也必须保证依赖只单向：

```text
judge-server depends_on backend-api:service_healthy
```

backend-api 不能反向依赖 judge healthy。

## 11.3 推荐健康检查

| 服务             | Healthcheck                           |
| -------------- | ------------------------------------- |
| postgres       | `pg_isready -U ... -d ...`            |
| redis          | `redis-cli ping`                      |
| backend-api    | 当前 `deploy/health_check.py`           |
| backend-worker | PID1 存活 + `runtime_smoke.py --worker` |
| judge-server   | `/ping` + heartbeat readiness         |
| frontend       | localhost HTTP `/` 或 `/healthz`       |

当前 backend health check 已访问 `/api/website/` 并检查 JSON `error` 字段。

当前 runtime smoke 还明确检查 Redis DB 1 和 DB 4。

这两份现有脚本应继续利用，而不是重写另一套不一致的检查。

---

# 12. 初始化正确顺序

最终首次安装顺序应固定为：

```text
1. preflight
2. 创建 runtime 目录
3. 启动 postgres + redis
4. 等待 postgres + redis healthy
5. backend bootstrap-runtime
6. Django system check
7. Django migrate
8. configure Judge token（仅不存在时）
9. create initial admin（仅不存在 super admin 时）
10. 启动 backend-api
11. backend-api healthy
12. 启动 judge-server / heartbeat
13. 启动 backend-worker
14. 启动 frontend
15. docker compose --wait
16. external smoke
17. 记录成功 release digest
```

## 12.1 Judge token 初始化已经具备正确的“不覆盖”语义

当前 `configure_judge_token`：

* 支持 `JUDGE_SERVER_TOKEN_FILE`
* 如果已有 `judge_server_token`，**主动拒绝覆盖**
* 使用 transaction
* 不输出 token

这是正确的生产语义。

`deploy.sh` 普通升级不能把：

```text
Judge token 已存在
```

当作理由去删除再创建。

更不能执行：

```text
reset token
```

## 12.2 初始管理员命令也已经基本幂等

当前 `create_initial_admin`：

* 如果已有 super admin，直接成功退出
* 从文件读取密码
* 要求密码至少 12 字符
* 不允许覆盖已有同名用户
* transaction 创建 user + profile

因此它适合作为**首装初始化操作**，不应成为每次部署的“重置管理员”。

## 12.3 当前 bootstrap-runtime 的一个高风险问题

当前 backend entrypoint 在 `secret.key` 不存在时会自行生成 secret。

这和最终生产原则冲突：

> production deploy 不应该在不知道 Secret 来源的情况下默默生成新 Django SECRET_KEY。

最终建议修改语义为：

```text
development:
  missing secret → 可生成

production:
  missing secret → fail closed
```

在完成该调整前，生产部署必须提前提供已有 Django secret，**这是一个停止条件。**

---

# 13. Secret 与 `_FILE` 设计

推荐顶层 Compose secrets：

```text
postgres_password
django_secret_key
judge_server_token
initial_admin_password
tls_cert
tls_key
```

按最小权限授权：

| Secret                 | postgres | backend-api | worker | migrate | judge | frontend |
| ---------------------- | -------: | ----------: | -----: | ------: | ----: | -------: |
| PostgreSQL password    |        ✓ |           ✓ |      ✓ |       ✓ |       |          |
| Django SECRET_KEY      |          |           ✓ |      ✓ |       ✓ |       |          |
| Judge token            |          |           ✓ |      ✓ |       ✓ |     ✓ |          |
| initial admin password |          |             |        |    首装 ✓ |       |          |
| TLS cert/key           |          |             |        |         |       | TLS 模式 ✓ |

Docker Compose Secret 按服务授权，并只读挂载文件。

## JudgeServer 当前需要补齐 `_FILE`

当前 JudgeServer `utils.py` 只读取：

```python
os.environ.get("TOKEN")
```

然后执行 SHA-256。

因此当前 server image **还没有 `TOKEN_FILE` 能力**。

最终现代化建议支持：

```text
TOKEN_FILE=/run/secrets/judge_server_token
```

读取文件内容以后再执行现有 SHA-256。

必须保持：

```text
实际 secret
    ↓
SHA-256
    ↓
X-Judge-Server-Token
```

不能改变协议摘要语义。

---

# 14. `deploy.sh` 分步骤伪代码

生产 `deploy.sh` 的职责是**编排现有可重复操作**，而不是成为另一个应用安装器。

```sh
#!/bin/sh
set -eu

# A. 确定仓库根目录
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

# B. 基础能力检查
require docker
docker info
docker compose version
verify compose version policy

# C. 配置文件
require .env
load only what shell needs
validate DEPLOY_MODE = build|pull
validate required secret FILE exists
validate files readable
validate RUNTIME_ROOT is absolute and not "/"

# D. Compose 自检
docker compose config --quiet

# E. 建立 runtime 目录
mkdir -p:
  RUNTIME_ROOT/backend
  RUNTIME_ROOT/postgres
  RUNTIME_ROOT/redis
  RUNTIME_ROOT/judge/log
  RUNTIME_ROOT/judge/judger
  RUNTIME_ROOT/deployments/history

# 不生成 Secret
# 不 echo Secret
# 不 cat Secret

# F. 保存“当前成功版本”为 rollback candidate
read current successful deployment metadata
DO NOT overwrite previous until new release succeeds

# G. 获取应用镜像
case DEPLOY_MODE:
  build:
    docker compose build
  pull:
    docker compose pull frontend backend-api backend-worker judge-server
    # API/worker 实际共享 backend image

# H. 基础设施 readiness
docker compose up -d postgres redis
docker compose wait/health

# I. backend bootstrap
docker compose run --rm backend-api bootstrap-runtime

# J. DB migration
docker compose run --rm backend-api migrate
if failure:
  stop deployment
  preserve database and logs
  exit nonzero

# K. 一次性初始化
if Judge token DB row does not exist:
    docker compose run --rm backend-api configure-judge-token

if no super admin:
    docker compose run --rm backend-api create-initial-admin

# L. 全栈
docker compose up \
    -d \
    --remove-orphans \
    --wait \
    --wait-timeout "$DEPLOY_WAIT_TIMEOUT"

# M. smoke
HTTP smoke
/API smoke
session/CSRF smoke
/public smoke
Judge ping/heartbeat smoke

# N. 成功之后才提交 release state
resolve actual frontend/backend/server image IDs + RepoDigests
write deployments/history/<release>.json atomically
move current → previous
new release → current

exit 0
```

Docker 官方 `compose up` 明确：

* 配置或镜像变化时会重建容器
* **mounted volumes 会被保留**
* `--remove-orphans` 只清理不再定义的服务容器
* `--wait` 等待 running/healthy
* 出错返回非零

---

# 15. `deploy.sh` 明确禁止的行为

无论首次安装还是普通升级，默认路径都不能执行：

```text
docker compose down -v
docker volume prune
docker system prune --volumes
rm -rf "$RUNTIME_ROOT"
rm -rf postgres
rm -rf redis
DROP DATABASE
initdb existing data dir
flushall
reset administrator
delete Judge token
overwrite Judge token
regenerate Django SECRET_KEY
```

`--remove-orphans` 可以保留，因为它删除的是旧服务容器，而不是数据库 volume；但部署前仍应通过 `docker compose config` 确认 project name 未意外变化。

`COMPOSE_PROJECT_NAME` 的变化尤其危险，因为 Compose 会认为这是另一套应用。Docker 官方说明 project name 会进入服务/资源 namespace。

因此生产运行后：

**`COMPOSE_PROJECT_NAME` 应视为持久化身份，不应随意修改。**

---

# 16. BuildKit 缓存与可复用基础镜像

## 16.1 推荐原则

三个最终业务镜像不变：

```text
frontend image
backend image
server image
```

但构建时可以复用：

```text
official base image
       ↓
toolchain/dependency layers
       ↓
application layers
```

这不违反“三个模块各一个镜像”，因为构建缓存/base layer 不是生产业务服务。

## 16.2 frontend

推荐 Dockerfile 层序：

```text
Node base
→ corepack / pnpm
→ COPY package.json + pnpm-lock.yaml
→ pnpm install --frozen-lockfile
→ COPY application source
→ pnpm build
→ Nginx stable runtime
```

BuildKit：

```text
--mount=type=cache,target=/pnpm/store
```

业务 `.vue/.ts/.css` 变化时不应该重新下载整个 node_modules 依赖树。

## 16.3 backend

目标 uv 后：

```text
Python base
→ system runtime deps
→ COPY pyproject.toml + uv.lock
→ uv sync/install locked dependencies
→ COPY application code
```

缓存：

```text
--mount=type=cache,target=/root/.cache/uv
```

当前 backend 已尝试为 pip 建 cache mount，但安装命令又使用 `--no-cache-dir`，因此这一层的缓存收益需要重新评估。

## 16.4 server

这是最值得缓存的模块。

分离：

```text
compiler toolchain base
→ Judger C/CMake build
→ Python binding wheel
→ JudgeServer Python deps
→ JudgeServer Python source
```

当前 Dockerfile已经对 apt 建 BuildKit cache，是正确方向。

普通 Flask Python 代码变化不应再次：

* apt install gcc
* 下载 Java
* 下载 Go
* 编译整个 C Judger

## 16.5 registry cache

Docker 官方推荐：

* 合理排序 layers
* cache mounts
* external cache
* CI 用 `cache-from` / `cache-to`

推荐每个模块独立 cache：

```text
${IMAGE_REGISTRY}/cache/frontend:buildcache
${IMAGE_REGISTRY}/cache/backend:buildcache
${IMAGE_REGISTRY}/cache/server:buildcache
```

使用 registry cache `mode=max`。

这样换部署机后也无需从零构建。

---

# 17. 首次安装、普通升级、配置变更、镜像回滚

## 17.1 首次安装

```text
准备 .env
    ↓
人工/Secret 管理系统创建生产 secrets
    ↓
./deploy.sh
    ↓
preflight
    ↓
mkdir runtime
    ↓
build/pull
    ↓
postgres + redis healthy
    ↓
bootstrap
    ↓
migrate
    ↓
Judge token create-once
    ↓
admin create-once
    ↓
up --wait
    ↓
smoke
    ↓
record release digest
```

首次部署前必须已有：

* PostgreSQL password
* Django SECRET_KEY
* Judge token
* initial admin password

deploy.sh 不负责随机生成这些生产 Secret。

## 17.2 普通业务升级

```text
RELEASE_TAG=new-release
./deploy.sh
```

流程：

```text
保留 current digest
→ build/pull new images
→ migrate
→ up
→ wait
→ smoke
→ 成功后才更新 current/previous
```

不执行：

```text
Judge token 初始化
管理员 reset
DB recreate
```

## 17.3 仅配置变更

例如：

```dotenv
APP_DOMAIN=new.example.edu
HTTP_PORT=8080
PUBLIC_BASE_URL=https://new.example.edu
```

执行：

```text
docker compose config --quiet
docker compose up -d --remove-orphans --wait
smoke
```

**没有 build。**

这是最终验收的强制条件。

## 17.4 镜像回滚

假设：

```text
current.json  → release B
previous.json → release A
```

发现 release B 有问题：

```text
读取 previous.json
↓
将 FRONTEND_IMAGE_REF / BACKEND_IMAGE_REF / SERVER_IMAGE_REF
指向 A 的 immutable digest
↓
docker compose up -d --remove-orphans --wait
↓
smoke
```

但是：

> **应用镜像回滚 ≠ 数据库 migration 自动回滚。**

如果 B 已执行不可逆 migration，则只能在确认旧代码能够读取新 schema 的情况下回滚应用镜像，否则必须走数据库恢复流程。

---

# 18. 镜像 digest 记录方案

不要只记录：

```text
RELEASE_TAG=latest
```

推荐：

```json
{
  "release": "2026.08.20-abc1234",
  "deployed_at": "...",
  "source_commit": "...",
  "images": {
    "frontend": {
      "reference": "...",
      "image_id": "sha256:...",
      "repo_digest": "...@sha256:..."
    },
    "backend": {
      "reference": "...",
      "image_id": "sha256:...",
      "repo_digest": "...@sha256:..."
    },
    "server": {
      "reference": "...",
      "image_id": "sha256:...",
      "repo_digest": "...@sha256:..."
    }
  }
}
```

存储：

```text
${RUNTIME_ROOT}/deployments/current.json
${RUNTIME_ROOT}/deployments/previous.json
${RUNTIME_ROOT}/deployments/history/...
```

### `DEPLOY_MODE=pull`

必须记录 registry 的：

```text
repository@sha256:digest
```

回滚时直接按 digest。

### `DEPLOY_MODE=build`

若镜像没有 push，则 registry RepoDigest 可能不存在。

此时至少记录：

```text
Docker image ID sha256:...
```

并在本地主机保留前几个成功 image，不得部署结束立即 `image prune -a`。

如果要求真正跨机器的一键回滚，则 production build 流程应：

```text
build → push immutable image → deploy by digest
```

而不是只保存在本机。

---

# 19. 开发模式：profiles 还是 override

## 推荐：**核心环境差异使用 override 文件，profiles 只控制可选工具。**

Docker 官方文档将 profiles 定义为选择性启用服务；未设置 profile 的核心服务应正常启动。

因此：

### `compose.yaml`

生产语义的唯一基线：

```text
frontend
backend-api
backend-worker
judge-server
postgres
redis
```

### `compose.dev.yaml`

覆盖：

```text
source bind mount
Vite dev server
Django autoreload
debug environment
dev ports
test DB
```

启动：

```text
docker compose \
  -f compose.yaml \
  -f compose.dev.yaml \
  up
```

### profile

只适合：

```text
debug tools
database admin UI
manual smoke runner
maintenance helpers
```

不建议：

```text
profile=production
profile=development
```

然后在一个大 Compose 里藏两套核心拓扑——长期会很难维护。

---

# 20. 域名和端口无重建修改方案

目标验收：

```text
旧：
APP_DOMAIN=oj.old.edu
HTTP_PORT=80

新：
APP_DOMAIN=oj.new.edu
HTTP_PORT=8080
```

允许：

```text
Nginx container recreate
backend-api container recreate
```

不允许：

```text
pnpm build
vite build
docker compose build frontend
```

实现机制：

```text
HTTP_PORT
    ↓ Compose host port mapping

APP_DOMAIN
    ↓ frontend env
    ↓ official Nginx envsubst
    ↓ generated nginx conf

PUBLIC_BASE_URL
    ↓ backend runtime env
    ↓ absolute URL / trusted-origin behavior

browser API
    ↓ always /api
```

因此前端 bundle 与部署域名彻底解耦。

---

# 21. Healthcheck 与 Smoke 验收清单

## 21.1 Compose health

### PostgreSQL

```text
pg_isready succeeds
```

### Redis

```text
redis-cli ping → PONG
```

同时 backend runtime smoke：

```text
DB1 ping/read/write/delete
DB4 ping
```

当前仓库已有对应逻辑。

### backend-api

```text
GET /api/website/
HTTP 2xx
JSON parse succeeds
error field semantics unchanged
```

### backend-worker

```text
worker process remains PID1
Redis DB4 reachable
Dramatiq broker consumer alive
```

### JudgeServer

至少：

```text
POST /ping
heartbeat succeeds
backend sees JudgeServer online
```

协议继续保持：

```text
/judge
/compile_spj
/ping
X-Judge-Server-Token SHA-256
```

### frontend

```text
GET /
GET /admin/
GET /public/<known-file>
GET /api/website/
```

## 21.2 外部 smoke

部署最终成功之前至少通过：

```text
1. frontend homepage 2xx
2. /admin/ history URL 不 404
3. /api 请求被 frontend proxy 到 backend
4. JSON 仍为 {"error":..., "data":...}
5. csrftoken 可获得
6. Session cookie 可复用
7. X-CSRFToken 对需要 CSRF 的请求继续有效
8. /public/ 可以访问已知资源
9. backend 8000 未发布到 host
10. judge 8080 未发布到 host
11. Judge /ping 成功
12. heartbeat 成功
13. Redis DB1 可用
14. Redis DB4 可用
15. worker 正常消费测试任务
```

完整 staging acceptance 再加入一个可控的实际判题：

```text
提交简单程序
→ worker dispatch
→ JudgeServer /judge
→ /test_case:ro
→ C/Seccomp Judger
→ result fields 回 backend
```

---

# 22. 数据与 Secret 安全边界

## 数据等级

### 一级：绝不能由 deploy.sh 删除

```text
PostgreSQL
Redis
backend/upload
backend/test_case
backend/public 用户内容
Django secret
Judge token
TLS key
```

### 二级：应持久化但可重建

```text
logs
deployment history
```

### 三级：运行 scratch

```text
/judger
tmpfs /tmp
```

## PostgreSQL

最终 PostgreSQL 10 → 18 属于**数据库 major upgrade**。

不能和：

* frontend Vue/Vite 重构
* backend Django/uv 重构
* Compose topology 重构

一起塞进一个不可回滚提交。

PostgreSQL 10 已于 2022-11-10 EOL，而 18.4 支持到 2030-11-14。

正确路径是：

```text
先把新 Compose 跑在现有 PG10 数据上
↓
验证应用拓扑
↓
完整 DB backup + restore drill
↓
独立维护窗口升级 PG
↓
应用契约回归
```

## Redis

同理：

```text
先保持现有 Redis
↓
完成应用部署层重构
↓
独立备份 RDB/AOF
↓
升级至 Redis 8.2.x
↓
验证 DB1 / DB4
```

不要把 Redis 4 → 8 和 PostgreSQL 10 → 18 同时进行。

---

# 23. 分阶段迁移路径

## Phase 0：契约冻结

冻结：

```text
/api
Session/CSRF
/admin/
/public/
API wrapper
pagination
Django labels/tables/migrations
Redis DB1/DB4
Judge protocol
/test_case:ro
Judger UID/GID/Seccomp
```

没有完整契约测试，停止。

## Phase 1：只改 Compose/镜像拓扑

暂不升级 PostgreSQL/Redis major。

实现：

```text
3 application images
backend-api + backend-worker split
frontend only public ports
runtime root
config/secrets structure
deploy.sh
health/smoke
rollback metadata
```

这是优先级最高的一层。

## Phase 2：BuildKit/cache

建立：

```text
pnpm cache
uv cache
server compile cache
registry cache
immutable release tag
digest tracking
```

## Phase 3：frontend runtime config

完成：

```text
Vite relative /api
Nginx envsubst
domain/port no rebuild test
```

## Phase 4：backend runtime/Secret 清理

完成：

```text
production missing secret → fail
_FILE support
worker/API health semantics
```

## Phase 5：Redis 独立升级

4 → 8.2.x。

## Phase 6：PostgreSQL 独立升级

10 → validated target 18.4。

## Phase 7：TLS/运维硬化

最后处理：

```text
TLS
backup automation
observability
resource limits
image signing/SBOM
security hardening
```

---

# 24. 破坏性变更与高风险项

| 风险                                | 级别 | 处理                             |
| --------------------------------- | -: | ------------------------------ |
| PostgreSQL 10 → 18                | 极高 | 独立 migration 项目                |
| Redis 4 → 8                       |  高 | 独立数据升级                         |
| Judge C/Seccomp build context     | 极高 | server 镜像构建测试                  |
| Judge UID/GID/capabilities        | 极高 | 不得未测试修改                        |
| Judge health→backend heartbeat    |  高 | 避免 depends_on 环                |
| Django secret 自动生成                |  高 | production fail closed         |
| Redis 8 licensing                 | 中高 | 组织许可证确认                        |
| Compose 5.5 digest reconciliation |  中 | staging 首次运行验证                 |
| Nginx runtime template            |  中 | config test + smoke            |
| `/public` 权限                      |  中 | frontend RO                    |
| migration rollback                |  高 | migration compatibility review |
| COMPOSE_PROJECT_NAME 改动           |  高 | 生产固定                           |

Compose 5.5.0 官方特别指出，新 digest reconciliation 在首次升级后可能重新创建现有容器。

因此从旧 Compose 首次切换时，本来就应安排一次明确维护窗口，而不是假设“升级 Compose CLI 完全无影响”。

---

# 25. 停止条件

任何一个条件成立，`deploy.sh` 必须退出非零，并且**不继续启动新业务版本**：

```text
docker 不存在
docker daemon 不可用
docker compose v2/v5 plugin 不可用
.env 不存在
必填变量为空
DEPLOY_MODE 非 build|pull
RUNTIME_ROOT 非绝对路径
RUNTIME_ROOT="/"
Secret 文件不存在
Secret 文件不可读
docker compose config --quiet 失败
镜像 build/pull 失败
PostgreSQL unhealthy
Redis unhealthy
Django check 失败
migration 失败
Judge token 首装失败
backend-api unhealthy
Judge heartbeat 失败
frontend smoke 失败
/api wrapper smoke 失败
Session/CSRF smoke 失败
发现 backend 发布 8000
发现 server 发布 8080
```

另外以下工程问题解决前，不应进入生产：

1. server Dockerfile 的 `Judger/` 构建上下文未厘清。
2. production Django secret 仍可能静默重新生成。
3. Judge token secret-file 注入路径尚未完整贯通 JudgeServer。
4. PostgreSQL 10 → 18 没有经过备份恢复演练。
5. Redis 4 → 8 没有 DB1/DB4 数据兼容测试。

---

# 26. 失败行为

## build/pull 失败

```text
现运行容器不动
现数据不动
current release 不动
退出非零
```

## migration 失败

```text
不启动新应用版本
保留 migration log
保留 DB 原状/已执行 migration 状态
退出非零
```

不能自动：

```text
DROP DB
restore old dump
reverse migration
```

这些都需要明确人工决策。

## `up --wait` 失败

执行：

```text
docker compose ps
docker compose logs --no-color
```

保存日志到：

```text
${RUNTIME_ROOT}/deployments/history/<attempt>/logs/
```

然后退出非零。

**不要自动 `down -v`。**

## smoke 失败

保持现场用于诊断。

如果数据库 schema 与前一版本向后兼容，可以自动/人工执行应用镜像 rollback。

否则停止并进入数据库恢复决策。

---

# 27. 回滚原则

## 原则一：应用镜像与持久数据分开

可以回滚：

```text
frontend image
backend image
server image
Nginx runtime config
```

不能因为应用失败就顺带回滚：

```text
PostgreSQL volume
Redis volume
uploads
test_case
secrets
```

## 原则二：成功后才移动 current pointer

部署 B 前：

```text
current=A
previous=<A以前版本>
```

部署 B 完整 smoke 成功后：

```text
previous=A
current=B
```

如果 B 失败：

```text
current 仍然=A
```

## 原则三：数据库 migration 必须设计 forward/backward compatibility window

理想状态：

```text
Release N schema
        ↓ additive migration
Release N+1 可以工作
Release N 仍能短时工作
```

然后等稳定后再删除旧字段。

不要：

```text
drop old column
+
deploy code relying on new column
```

放在同一不可回滚发布里。

---

# 28. 推荐最终部署行为

最终用户体验应该收敛为：

```bash
cp .env.example .env
# 人工填写配置和 Secret 文件路径

./deploy.sh
```

对于运维者而言，`./deploy.sh` 的语义必须稳定：

```text
validate
→ acquire images
→ initialize safely
→ migrate
→ start
→ wait
→ smoke
→ commit deployment metadata
```

而绝不能演化成：

```text
guess
→ regenerate
→ delete
→ recreate everything
```

---

# 29. 待本仓库实测的问题

1. `server/Dockerfile` 最终以 `server/` 为 context 时，Judger CMake/Python binding 是否可在 amd64/arm64 都成功构建。
2. JudgeServer 所需 compiler/code/spj UID/GID 与 bind mount ownership 在目标 Linux 主机上的实际行为。
3. 当前 `read_only`、`tmpfs /tmp`、`cap_drop` 集合是否完整兼容新的 Debian/runtime。
4. JudgeServer `/ping` 是否适合作为纯 liveness；若仍含认证，应确认 smoke 请求格式。
5. Dramatiq Worker 是否需要 backend data volume 中除 `test_case` 外的其他目录。
6. frontend 对 `/public` 是否确实只需只读。
7. Django 在新 `APP_DOMAIN` 下 `CSRF_TRUSTED_ORIGINS`、Secure cookie、proxy headers 的实际配置。
8. `PUBLIC_BASE_URL` 在现业务代码中有哪些真正使用点。
9. 当前 API `/api/website/` 是否可以长期作为 health endpoint，还是应增加无数据库副作用的 `/healthz`。
10. Judge token 的 backend DB 存储值与 JudgeServer SHA-256 请求头完整兼容。
11. production bootstrap 如何彻底禁止 secret.key 自动生成。
12. PostgreSQL 10 数据是否包含旧 MD5 password verifier；PostgreSQL 官方已提醒历史升级数据库可能残留 MD5 verifier。
13. Redis 4 的 RDB/AOF 是否应直接跨版本读取，还是通过中间版本/数据迁移。
14. Compose 5.5.0 第一次 digest reconciliation 对旧容器重建行为。
15. `docker compose up --remove-orphans` 切换旧 service name 时是否符合预期。
16. rollback image 本地 retention 是否足够，还是生产必须强制 push registry。
17. frontend direct TLS 与 external TLS 两种 overlay 在同一 `.env` 模型下是否都通过 smoke。

---

# 30. 推荐决策汇总

| 项目                     | 最终决定                                                   |
| ---------------------- | ------------------------------------------------------ |
| 应用镜像数                  | **3**                                                  |
| backend API/Worker 镜像  | **共用一个 backend image**                                 |
| backend API/Worker 容器  | **必须分开**                                               |
| 长期业务容器                 | frontend / backend-api / backend-worker / judge-server |
| migrate                | backend image 一次性运行                                    |
| public HTTP/HTTPS      | **frontend only**                                      |
| backend 8000           | internal only                                          |
| Judge 8080             | internal only                                          |
| Browser API            | `/api`                                                 |
| Nginx config           | runtime envsubst                                       |
| Vite domain/API origin | 不编译绝对生产域名                                              |
| runtime root           | 可配置、持久化                                                |
| Secrets                | 文件/Compose secret，不进 `.env` 明文                         |
| PostgreSQL target      | 18.4，独立阶段                                              |
| Redis target           | 8.2.7，独立阶段                                             |
| Nginx                  | 1.30.4 stable                                          |
| Docker Engine          | 29.7.2                                                 |
| Compose                | 5.5.0，经 staging 后采用                                    |
| BuildKit               | cache mounts + registry cache                          |
| rollback               | immutable digest + current/previous metadata           |
| dev/prod               | Compose override                                       |
| profiles               | 仅可选工具                                                  |
| deploy failure         | 非零退出、保留日志、绝不删卷                                         |

---

# 31. 官方来源清单

**访问日期均为 2026-08-20。**

### 仓库固定基线

* [xju-OJ 固定提交 2d84d089bcd8ea90d5836c00d7c46e6de47697fc](https://github.com/xjuIcthub/xju-OJ/tree/2d84d089bcd8ea90d5836c00d7c46e6de47697fc)
* 根旧 Compose：
* backend Dockerfile：
* backend entrypoint：
* frontend Nginx：
* Django Redis/Dramatiq 配置：
* JudgeServer Dockerfile：
* Judge entrypoint：
* server 边界说明：
* Judge token 实现：
* backend token 初始化：
* initial admin：
* backend health：
* runtime smoke：

### Docker / Compose

* [Docker Engine 29 release notes](https://docs.docker.com/engine/release-notes/29/) — 29.7.2、BuildKit 0.32.2。
* [Docker Compose v5.5.0 release](https://github.com/docker/compose/releases/tag/v5.5.0) — 2026-08-17、digest reconciliation。
* [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/) — `service_healthy` / `service_completed_successfully`。
* [Compose interpolation](https://docs.docker.com/reference/compose-file/interpolation/) — `${VAR:?error}`。
* [docker compose up reference](https://docs.docker.com/reference/cli/docker/compose/up/) — `--wait` / `--remove-orphans` / volume preservation。
* [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/) — `/run/secrets` 与 `_FILE`。
* [Build cache optimization](https://docs.docker.com/build/cache/optimize/) — layer/cache mount/external cache。
* [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/) — profiles 使用边界。

### Nginx / Vite

* [NGINX 2026 releases](https://nginx.org/2026.html) — 1.30.4 stable / 1.31.3 mainline。
* [NGINX official Docker image envsubst documentation](https://hub.docker.com/_/nginx) — `/etc/nginx/templates/*.template`。
* [Vite Env Variables and Modes](https://vite.dev/guide/env-and-mode) — `import.meta.env` 构建时静态替换。

### PostgreSQL

* [PostgreSQL Versioning Policy](https://www.postgresql.org/support/versioning/) — 支持周期、18.4、PG10 EOL。
* [PostgreSQL 18.4 release announcement](https://www.postgresql.org/about/news/postgresql-184-1710-1614-1518-and-1423-released-3297/) — 2026-05-14 安全更新。

### Redis

* [Redis Open Source version management](https://redis.io/docs/latest/operate/oss_and_stack/install/version-mgmt/) — 8.2 GA / EOL 2030-09-01。
* [Redis 8.2 release notes](https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/release-notes/redisce/redisos-8.2-release-notes/) — 8.2.7，2026-06。
* [Redis licensing](https://redis.io/legal/licenses/) — Redis 8 RSALv2 / SSPLv1 / AGPLv3。

---

# 32. 最终架构判断

本仓库最合理的生产部署现代化不是“把旧 `docker-compose.yml` 换几个新镜像标签”，而是建立一个稳定的发布边界：

```text
Source repository
      │
      ├── frontend ──────> immutable frontend image
      ├── backend ───────> immutable backend image
      └── server ────────> immutable server image
                              │
                              ▼
                         Docker Compose
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
          stateless apps   persistent data   secrets
               │              │              │
           reversible      never implicit    never generated/
          image rollout       delete           printed
```

其中：

**镜像是可回滚的，数据是受保护的，Secret 是外部提供的，配置是运行时注入的。**
这四条应成为最终 `compose.yaml` 和 `deploy.sh` 的设计底线。
