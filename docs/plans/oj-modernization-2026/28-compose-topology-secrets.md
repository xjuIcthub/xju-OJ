# Step 28：Compose 拓扑与 Secrets

## 目标

把根 Compose 从旧远程镜像模型切到三业务镜像、多角色 backend、内网隔离、可配置端口/域名、持久卷和 fail-closed Secret 模型。

## 进入条件

- Step 06、12、23、26、27 的镜像/安全边界通过。
- Step 19–22 数据卷/备份路径已明确。
- 所有生产镜像已有 immutable digest；不要把本 Step 与数据库 major 切换同批发布。

## 服务

长期服务：

```text
frontend
backend-api
backend-worker
judge-server
postgres
redis
```

一次性服务/命令：

```text
backend-bootstrap
backend-migrate
configure-judge-token
create-initial-admin
```

backend-api/worker/migrate 共用 `xju-oj/backend`；不再用 Supervisor 合并 API 与 Worker。

## 网络和端口

```text
edge: frontend, backend-api
core: backend-api, backend-worker, judge-server, postgres, redis
```

- frontend 是唯一 `ports:` 服务，绑定 `${HTTP_BIND_ADDRESS}:${HTTP_PORT}:80`。
- backend-api 不发布 8000。
- judge-server 不发布 8080。
- postgres/redis 不发布 5432/6379。
- frontend 不能直连 Redis、PG、JudgeServer；backend-api 是业务桥。

## 配置变量

`.env.example` 只包含非秘密值和 Secret 文件路径：

```text
COMPOSE_PROJECT_NAME
APP_DOMAIN
PUBLIC_BASE_URL
HTTP_BIND_ADDRESS
HTTP_PORT
HTTPS_PORT
RUNTIME_ROOT
BACKUP_ROOT
IMAGE_REGISTRY
RELEASE_TAG
DEPLOY_MODE=build|pull
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD_FILE
DJANGO_SECRET_KEY_FILE
JUDGE_SERVER_TOKEN_FILE
INITIAL_ADMIN_PASSWORD_FILE
TLS_MODE
```

关键变量使用 `${VAR:?message}` fail closed；`RUNTIME_ROOT` 必须绝对且非 `/`。COMPOSE project name 是持久化身份，不随意改。

## 卷

- backend `/data` RW。
- frontend `/data/public` RO。
- judge `/test_case` RO、`/judger` scratch、`/log` RW。
- PG/Redis 使用参数化绝对路径和独立版本卷。
- Secret 用 Compose secrets 或 `_FILE`；不复制进 image/.env/日志。

backend bootstrap 缺少 Django Secret 必须失败；JudgeServer 增加 `TOKEN_FILE` 后计算相同 SHA-256 header。初始管理员和 Judge token 都是 create-once，不覆盖已有值。

## 健康与依赖

- PG：`pg_isready`。
- Redis：`redis-cli ping`。
- backend-api：`/api/website/`。
- worker：进程和 `runtime_smoke.py --worker`。
- Judge：本机 `/ping` liveness，heartbeat 独立 degraded。
- frontend：首页/healthz。

依赖方向不能形成 heartbeat 循环；`depends_on: condition: service_healthy` 只用于启动顺序，不代替业务 smoke。

## 计划文件

新增/修改：

- `compose.yaml`（或替换根 `docker-compose.yml`）
- `.env.example`
- `compose.dev.yaml`、可选 TLS override
- frontend Nginx template
- backend Secret/_FILE 读取
- JudgeServer `TOKEN_FILE`

## 验收

```bash
docker compose --env-file .env.example config --quiet
```

用测试 Secret 和隔离 runtime 启动全栈：只有 frontend 有宿主端口，`/api`、`/admin/`、`/public/`、DB1/DB4、Judge 内网 smoke 通过。

## 停止条件

- backend/server 有 host ports。
- `.env` 包含真实密码/Token，或 bootstrap 自动生成/覆盖 Secret。
- `/test_case` 非只读、PG/Redis 卷被覆盖、`down -v` 成为正常升级流程。
- health DAG 循环或 Judge backend down 会重启容器。

## 回滚

Compose manifest 本身按 Git SHA 版本化；失败时恢复旧 Compose/镜像 digest，保留所有卷、Secret、日志和部署记录。

## 完成标志

提交格式建议：

```text
feat(deploy): define isolated three-image compose topology
```
