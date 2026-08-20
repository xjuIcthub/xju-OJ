# 阶段 03：独立 backend API、迁移任务与 Dramatiq Worker

## 目标

将 `backend/` 从“内嵌前端 Nginx、Gunicorn、Dramatiq 的一体容器”变成独立的 Django 业务模块：同一镜像按不同命令启动 API、Worker 和一次性迁移/bootstrap；frontend 负责浏览器入口，backend 不再下载或服务前端 `dist`。

## 进入条件

- 阶段 01 已完成目录收敛，`backend/manage.py`、`backend/oj/` 和各 Django app 仍保持原名。
- 阶段 02 的 frontend 静态服务和 `/api` 代理在隔离环境可用，或者至少 Nginx 配置已经过语法验证。
- 阶段 00 已备份数据库、Redis 和 `test_case`/`public` 数据，并完成 API/判题协议清单。
- 已明确开发与生产的 `RUNTIME_ROOT`，且它不在 Git 受控源码树中。

## 当前行为必须理解

| 现状 | 来源 | 迁移要求 |
|---|---|---|
| Django 设置包 | `backend/manage.py`、`backend/oj/{settings,wsgi}.py` | 保持 `oj.settings`、`oj.wsgi`，不改 app label |
| 业务 API | `backend/oj/urls.py` 与各 app `urls/` | `/api/*`、`/api/admin/*` 不变 |
| 响应包装 | `backend/utils/api/api.py` | 保持 `error`/`data` 形状、分页规则、parser 行为 |
| Session/缓存/待判队列 | Redis DB 1 | 保持 Session、cache 与 `waiting_queue` 语义 |
| Dramatiq | Redis DB 4 | API 与 Worker 可拆进程，但 broker/result/actor 不变 |
| 判题调度 | `backend/judge/{tasks,dispatcher}.py` | Server endpoint、请求头、状态码、队列语义不变 |
| 运行时数据 | `/data` | `test_case`、`public`、`config`、`ssl`、`log` 分开管理 |
| 旧启动 | `deploy/entrypoint.sh` + Supervisor + Nginx | 迁出前端/Nginx，拆成显式命令 |

## 步骤 03.1：定义 backend 进程模型

目标 Compose 服务模型：

```text
backend-migrate  # 一次性：初始化目录、检查配置、migrate、受控创建初始管理员
backend-api      # Gunicorn：只提供 Django HTTP API，内部端口 8000
backend-worker   # python manage.py rundramatiq：只消费/执行异步任务
```

禁止再在单一 `backend` 容器内使用 Supervisor 同时托管 Nginx、Gunicorn、Dramatiq。这样做的原因是：

- 前端已经有独立 Nginx；
- API 与 Worker 可分别扩缩容、重启和观测；
- 迁移只运行一次，避免 API/Worker 启动竞争；
- 进程日志和健康状态可按职责定位。

共享的 `backend` 镜像仍可以包含三种命令，避免复制 Python 依赖层。

## 步骤 03.2：重构 backend Dockerfile，但不升级框架

基于现 `backend/Dockerfile` 新建目标镜像，按以下原则修改：

1. **删除**下载 `OnlineJudgeFE` `dist.zip` 的 downloader stage 和 `COPY --from=downloader /app/dist`。
2. **删除** Nginx、Supervisor 及 frontend 静态文件依赖；前端已迁到 `frontend/`。
3. 保留 Django、Pillow、PostgreSQL 客户端/编译依赖及 `deploy/requirements.txt` 中固定版本，除非基线构建已证明必须修复一个具体兼容问题。
4. 继续将源码复制至稳定工作目录（可保持 `/app`），使 `manage.py`、`oj.wsgi`、`docs/data.json` 的相对路径按实际修改后可用。
5. 增加 `.dockerignore`，排除 `__pycache__`、coverage、runtime 数据、密钥、测试构建输出、node_modules 和无关模块。
6. 用非 root 运行 API/Worker；仅在需要对数据目录做权限初始化的受控 bootstrap 步骤使用必要权限。
7. 不在镜像层中写入 `SECRET_KEY`、`JUDGE_SERVER_TOKEN`、数据库密码、Sentry DSN 或证书。

推荐验收：

```bash
docker build --file backend/Dockerfile --tag xju-oj/backend:layout-check backend
docker image inspect xju-oj/backend:layout-check
```

检查镜像 history 和 build context，确保不再包含 `frontend/dist`、上游下载的 dist 或运行时目录。

## 步骤 03.3：参数化运行时目录与种子资源

### 目标数据布局

由 Compose 或部署环境提供：

```text
${RUNTIME_ROOT}/
├── backend/
│   ├── config/secret.key
│   ├── public/avatar/
│   ├── public/upload/
│   ├── public/website/
│   ├── test_case/
│   ├── log/
│   └── ssl/                     # 仅在确需自签名兼容时保留
├── postgres/
├── redis/
└── judge-server/
    ├── log/
    └── run/
```

挂载规则：

| 消费者 | 可读写路径 | 只读路径 | 禁止挂载 |
|---|---|---|---|
| `backend-migrate`/`backend-api`/`backend-worker` | `runtime/backend` | 无 | JudgeServer 工作目录 |
| `frontend` | 无 | `runtime/backend/public` | config、test_case、log、ssl |
| `server` | `runtime/judge-server/log`、`runtime/judge-server/run` | `runtime/backend/test_case` | backend config、public 上传目录 |

### 设置与 bootstrap

- 保留 `DATA_DIR` 这个 Django 语义名称，但让生产配置从 `OJ_DATA_DIR` 或等价 `RUNTIME_ROOT` 派生，默认仍可兼容 `/data`；
- 把默认 `avatar/default.png`、`website/favicon.ico` 从旧 `backend/data/` 改为 `backend/resources/bootstrap/`；
- bootstrap 只在目标文件缺失时复制种子资源，不能覆盖真实上传文件；
- `TEST_CASE_DIR` 继续对应 `DATA_DIR/test_case`，因为 `Problem.test_case_id` 和 JudgeServer 都依赖这一约定；
- `LOG_PATH` 保持可写，但日志不作为镜像层或 Git 输入；
- 确保 `public` 目录的权限允许 frontend Nginx 只读读取，而 `test_case` 仍只对 backend/server 必需用户可读。

使用目录与权限测试验证，而不是仅测试路径存在：

```bash
find "$RUNTIME_ROOT/backend" -maxdepth 3 -printf '%M %u:%g %p\n' | sort
```

## 步骤 03.4：拆分 bootstrap、migration 与初始管理员

当前 `backend/deploy/entrypoint.sh` 会在每次启动中：生成 secret、自签 HTTPS、运行 migrate、创建 `root/rootroot`、写 JudgeServer Token、重置 task number。该行为不能原样复制到 API/Worker。

实现三个明确动作：

### A. `bootstrap-runtime`

- 创建必要目录；
- 仅在缺失时生成 `secret.key`；
- 复制无秘密种子资源；
- 校验目录 owner/mode；
- **不**自动生成生产 HTTPS 证书（TLS 由 frontend/外部反向代理负责）；
- **不**运行迁移、不启动 server、不覆盖现有 Token。

### B. `migrate`

- 先运行 `python manage.py check`；
- 执行 `python manage.py migrate --no-input` 一次；
- 用显式环境变量或一次性管理命令设置 `SysOptions.judge_server_token`，且不将值回显；
- 重置 `JudgeServer.task_number` 前须确认没有仍在运行或排队的提交；该动作应在切换窗口进行，而非每次容器重启；
- 所有操作均返回非零退出码以阻止 API/Worker 启动。

### C. `create-initial-admin`（仅新安装）

- 禁止硬编码 `root/rootroot`；
- 仅在数据库为空且显式提供初始管理员配置时运行；
- 环境变量或秘密管理系统传入一次性凭据，不写日志；
- 升级已有生产数据库时默认跳过，绝不重置已有管理员密码。

为此新增或重构的脚本应有 `--dry-run`/检查模式，并为新安装与升级路径分别测试。

## 步骤 03.5：启动 API 和 Worker

### API

用 Gunicorn 直接运行：

```bash
gunicorn oj.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --threads "$GUNICORN_THREADS"
```

实际 `oj.wsgi` 的 import 形式先在容器中验证；不要因示例中的冒号语法改变 Python 包名。API 端口只暴露给 frontend 所在 Docker 网络，除开发 profile 外不映射宿主机。

### Worker

保留 actor 和 broker 语义：

```bash
python manage.py rundramatiq --processes "$DRAMATIQ_PROCESSES" --threads "$DRAMATIQ_THREADS"
```

不得在这一阶段更换：

```text
Redis DB 1（Session/Cache/waiting_queue）
Redis DB 4（Dramatiq broker/result）
judge.tasks.judge_task actor 名称
waiting_queue key
JudgeDispatcher 的选择、计数、排名更新逻辑
```

API/Worker 的健康检查应按职责设计：API 可使用现存 `GET /api/website/` 作为端到端依赖检查；Worker 使用进程存活、连接预检和小型 actor 集成测试，不要假装 HTTP health 代表队列能消费。

## 步骤 03.6：保留业务与数据库兼容

不要改动下列路径或语义：

```text
backend/oj/urls.py
backend/utils/api/api.py
backend/account/middleware.py
backend/account/decorators.py
backend/judge/dispatcher.py
backend/judge/tasks.py
backend/conf/views.py
backend/*/migrations/
```

特别检查：

- `AUTH_USER_MODEL = 'account.User'`；
- 表名 `user`、`problem`、`contest`、`submission`、`judge_server` 等；
- 迁移 graph 中跨 app 依赖；
- `Submission.user_id` 的非 FK 历史语义；
- JSON 状态字段、题目 test case ID、比赛排行榜和统计更新；
- `APIView` 的 JSON/URL encoded parser、`{"error","data"}` 包装和 CSRF 豁免接口；
- `HTTP_APPKEY` API Key、Session、管理员中间件顺序；
- `JudgeServerHeartbeatAPI` 与 `JudgeDispatcher` 的 SHA-256 Token 行为。

目录移动后运行：

```bash
cd backend
python manage.py check --settings=oj.settings
python manage.py showmigrations --settings=oj.settings
python manage.py migrate --plan --settings=oj.settings
python manage.py makemigrations --check --dry-run --settings=oj.settings
python manage.py test utils.api account announcement conf contest options problem submission --settings=oj.settings
flake8 --config=./.flake8 .
```

任何 migration 差异都视为阻塞：本阶段不接受“重新生成所有迁移”作为修复。

## 步骤 03.7：添加最小 backend 集成测试

原有 app 测试重点是业务 API。为支撑进程拆分，补充最小集成测试（不重复现有内部实现）：

1. API 容器能连接 PostgreSQL 和 Redis，并返回 `/api/website/`；
2. 登录后同源 CSRF 写请求仍成功；
3. 提交创建后 `judge_task` 进入 Broker；
4. 无可用 JudgeServer 时，提交仍保持可观察 Pending，`waiting_queue` 行为与旧版一致；
5. Worker 与 Server 恢复后能消费一条待判任务；
6. `test_case` 未被 API 公开静态路径暴露；
7. backend-api 被重启不会重新执行 migration 或覆盖初始管理员/Token。

## 建议提交点

```text
refactor(backend): remove bundled frontend runtime
refactor(backend): split bootstrap migration api and worker commands
refactor(backend): externalize runtime data paths
 test(backend): cover API worker and runtime integration
```

## 验收门槛

- [ ] 后端镜像不下载、复制或服务 frontend `dist`。
- [ ] API、Worker、Migration 是独立可执行命令，迁移不会因 worker/API 重启重复运行。
- [ ] 初始管理员无硬编码弱口令，升级路径不会改变现有账户。
- [ ] `RUNTIME_ROOT` 数据目录、卷权限和种子资源行为明确且安全。
- [ ] 现有 Django 检查、迁移计划、全套 app 测试、flake8 成功。
- [ ] `/api` 响应、Session、CSRF、上传、公开资源、判题调度/heartbeat 契约不变。
- [ ] backend 在没有 frontend 源码或 Node 的镜像中可以独立构建和启动。

## 停止条件与回滚

- Django 检测到新的 migration；
- API/worker 同时迁移导致锁、重复初始化或写入 Token；
- 运行目录权限使 frontend 无法读 public 或 server 无法读 test case；
- 任何初始管理员/secret 以默认值、日志或镜像层存在；
- API contract 测试出现错误包装、Session、CSRF 或判题协议变化。

回滚方式：恢复上一版 backend 镜像与旧 Compose，恢复数据卷和 PostgreSQL 备份（若已执行不可逆操作），并在流量恢复前检查 Redis waiting queue 和 `Submission` 的 Pending/Judging 状态。不要通过删除 `django_migrations` 或盲目 `migrate zero` 回滚生产库。
