# 统一 OJ 仓库实施总计划

> **状态：仅规划，尚未执行模块迁移。**
>
> **目标：** 将当前四份源码组织为以 `frontend/`、`backend/`、`server/` 为三个一级主模块的单仓库；代码、镜像和运行时职责真正前后端分离，同时保留现有 OJ 行为、数据和判题协议。
>
> **执行原则：** 先建立可复现基线和兼容层，再做目录与部署切换；不要将目录整理、技术栈升级、数据库重构和协议重写混在一次发布中。

## 1. 如何使用本计划

后续新对话应从本文件开始，并且**按编号只执行一个子计划**。每个子计划都定义了：

- 进入条件与禁止事项；
- 目标目录/文件以及具体改动；
- 可复现的验证命令；
- 阶段提交点、停止条件和回滚方法。

执行顺序不可跳跃：

| 阶段 | 细化计划 | 目的 | 预估实施量* |
|---|---|---|---:|
| 0 | [00-baseline-and-contracts.md](00-baseline-and-contracts.md) | 固化源码、数据、接口和运行基线 | 4–8 小时 |
| 1 | [01-layout-git-and-licenses.md](01-layout-git-and-licenses.md) | 纳管源码并完成无行为变化的目录收敛 | 6–12 小时 |
| 2 | [02-frontend-extraction.md](02-frontend-extraction.md) | 独立前端构建、静态服务和同源反向代理 | 8–16 小时 |
| 3 | [03-backend-api-and-worker.md](03-backend-api-and-worker.md) | 拆开 Django API、迁移任务和 Dramatiq Worker | 12–20 小时 |
| 4 | [04-server-judge-and-sandbox.md](04-server-judge-and-sandbox.md) | 收敛 JudgeServer 与 Judger 为 `server/` | 10–18 小时 |
| 5 | [05-compose-ci-and-docs.md](05-compose-ci-and-docs.md) | 统一 Compose、镜像发布、CI 与开发文档 | 10–18 小时 |
| 6 | [06-cutover-and-acceptance.md](06-cutover-and-acceptance.md) | 数据切换、灰度、回归、清理旧目录 | 12–20 小时 |

\* 估算合计约 **62–112 工程小时**。旧前端依赖能否在选定 Node 版本稳定复现、以及生产数据和判题队列规模会是最大的时间变量；先跑阶段 0 的证据收集后再确认排期。

## 2. 本次调研结论

### 2.1 当前工作树不是已纳管的四模块 monorepo

当前 Git `HEAD` 为 `0283f8a`（`Initial commit: OJ platform with Docker compose`），索引中仅有：

```text
.gitignore
README.md
README.en.md
docker-compose.yml
```

`OnlineJudgeFE/`、`OnlineJudge/`、`JudgeServer/`、`Judger/` 都是**未跟踪目录**。因此：

1. 当前不能把目录移动当作普通 `git mv` 重命名；
2. 未先提交源码基线就整理目录，会丢失可审计的原始快照；
3. 根 `.gitignore` 的 `data/` 模式会忽略任意名为 `data` 的子目录，包括 `OnlineJudge/data/` 中的运行时文件和模板资源；
4. 阶段 0/1 必须先做清单、哈希和人工检查，再创建一次“原始四模块导入”提交。

### 2.2 当前四模块与职责

| 当前目录 | 技术与主要职责 | 目标归属 |
|---|---|---|
| `OnlineJudgeFE/` | Vue 2、Vue Router、Vuex、Axios、Webpack 3；用户端与 `/admin` 两个入口 | `frontend/` |
| `OnlineJudge/` | Django 3.2、PostgreSQL、Redis、Dramatiq；业务 API、账户、题目、比赛、提交、调度 | `backend/` |
| `JudgeServer/` | Flask/Gunicorn 判题服务、语言编译配置、心跳和 `/judge` 协议 | `server/judge-server/` |
| `Judger/` | C/Seccomp 沙箱、Python/Node/Lua bindings、核心安全测试 | `server/judger/` |

`JudgeServer/Judger/` 在当前工作树中是一个**空目录**；其 `.gitmodules` 只是历史子模块声明。真实的 Judger 源码位于顶层 `Judger/`。现有 `JudgeServer/Dockerfile` 仍使用 `COPY Judger/ /app/`，所以若直接以 `JudgeServer/` 为 build context 构建会缺失源码。这是 `server/` 重组必须解决的关键路径错误。

### 2.3 当前生产拓扑与核心问题

现有根 `docker-compose.yml` 启动：

```text
oj-backend（预构建 backend 镜像，内部又运行 Nginx + Gunicorn + Dramatiq）
  ├── oj-postgres
  ├── oj-redis
  └── oj-judge（预构建 JudgeServer 镜像）
```

问题是：

- Compose 使用远程 `backend:1.6.1`、`judge:1.6.1` 镜像，**不构建当前本地四模块源码**；
- `OnlineJudge/Dockerfile` 会从上游下载 `OnlineJudgeFE` 的 `oj_2.7.5/dist.zip`，而当前前端 `package.json` 是 `2.7.6`；
- 后端 Nginx 同时提供前端资源、`/public` 文件和 `/api`，所以代码虽分目录，部署并非前后端分离；
- 前端 Dockerfile 使用 Node 6，历史 CI 使用 Node 8.12，依赖声明又会解析到较新的 Vue 2.7 生态，构建基线不一致；
- 后端 Dockerfile 使用 Python 3.12，历史 CI 用 Python 3.8；依赖和运行时版本也未形成统一锁定；
- 旧 CI 各自存在于模块内，镜像发布与源码目录的关系不透明。

### 2.4 现有运行时依赖图

```text
浏览器
  │  同源请求：/、/admin、/api、/public
  ▼
当前 backend 容器内的 Nginx
  ├── 静态 dist（来自上游下载的前端压缩包）
  ├── /public -> /data/public
  └── /api -> Gunicorn/Django
                    ├── PostgreSQL：业务数据
                    ├── Redis DB 1：Session/缓存 + waiting_queue
                    ├── Redis DB 4：Dramatiq broker/result
                    └── HTTP -> JudgeServer /judge、/compile_spj
                                      │
                                      ├── /test_case（后端数据目录只读挂载）
                                      ├── /judger/run、/judger/spj
                                      └── _judger -> /usr/lib/judger/libjudger.so
```

### 2.5 关键证据文件索引

| 关注面 | 证据文件 | 已确认事实 |
|---|---|---|
| 前端入口/构建 | `OnlineJudgeFE/package.json`、`build/webpack.base.conf.js`、`build/webpack.prod.conf.js` | Vue 双入口（`oj`/`admin`）、Webpack 3、DLL manifest 是生产构建前置条件 |
| 前端协议 | `src/pages/oj/api.js`、`src/pages/admin/api.js`、`src/pages/*/router*` | Axios 同源 `/api`、Django CSRF Cookie/Header、用户端与管理端 history 路由 |
| 前端代理 | `OnlineJudgeFE/config/index.js`、`deploy/nginx.conf` | 开发依赖 `TARGET`/Referer；旧生产 Nginx 上游和路径不能直接复用 |
| Django 入口 | `OnlineJudge/manage.py`、`oj/settings.py`、`oj/wsgi.py`、`deploy/supervisord.conf` | `oj.settings`/`oj.wsgi` 与 Supervisor 同时启动 API/Worker；迁移后保留包名 |
| API 兼容层 | `OnlineJudge/oj/urls.py`、各 app `urls/*.py`、`utils/api/api.py` | 所有业务挂 `/api`，自定义 `error/data` 包装、分页和 parser，不是标准 DRF ViewSet |
| 认证权限 | `account/middleware.py`、`account/decorators.py`、`account/views/oj.py` | Session、`APPKEY`、CSRF、中间件顺序和管理路径保护互相耦合 |
| 数据/异步 | `account/problem/contest/submission` models、各 `migrations/`、`judge/tasks.py`、`judge/dispatcher.py` | 迁移跨 app；Redis DB 1 承载 Session/cache/waiting_queue，DB 4 承载 Dramatiq broker/result |
| 文件资产 | `oj/settings.py`、`problem/views/admin.py`、`conf/views.py`、`deploy/entrypoint.sh` | `/data/test_case/<test_case_id>` 与数据库绑定；`/data/public` 由 Nginx 发布 |
| Backend 镜像 | `OnlineJudge/Dockerfile` | 当前会下载上游 `oj_2.7.5/dist.zip`，必须在 backend 独立后移除 |
| 判题协议 | `judge/dispatcher.py`、`conf/{serializers,views}.py`、`JudgeServer/server/{server,service,utils}.py` | `/judge`、`/compile_spj`、heartbeat 使用同一 Token 的 SHA-256 头和两种 JSON 包装 |
| Server 构建 | `JudgeServer/Dockerfile`、`JudgeServer/server/entrypoint.sh`、`JudgeServer/server/config.py` | 需要三类系统用户、固定 `/judger`/`/test_case`/`/log` 权限；旧 `COPY Judger/` context 已失配 |
| Sandbox | `Judger/CMakeLists.txt`、`bindings/Python/_judger/__init__.py`、`src/runner.h`、`tests/` | C/Seccomp 核心、Python binding、资源限制和安全测试必须保持独立边界 |
| 编排/发布 | 根 `docker-compose.yml`、三个模块 CI/workflows | 当前 Compose 只拉远程镜像；模块 CI 与发布 context 分散，不能证明本地源码可发布 |
| 许可证 | `OnlineJudge/LICENSE`、`OnlineJudgeFE/LICENSE`、`JudgeServer/LICENSE`、`Judger/LICENSE` | MIT 与 SATA 混合，不能在合并时用一份许可证覆盖全部代码 |

高风险优先级为：**数据/迁移与备份 > 判题沙箱权限 > API/CSRF/Session 兼容 > Compose 网络/卷 > 构建版本可复现 > 文档清理**。后续子计划按这个顺序设置停止条件，而不是先做目录美化。

## 3. 目标架构与边界

### 3.1 目标不是一次“重写”

第一轮统一交付的定义是：

- 三个一级主模块分别独立构建、测试和发布；
- 前端静态服务与后端 API/worker 使用独立容器；
- 判题服务与沙箱源码在 `server/` 内统一，但保持两个内部边界；
- 浏览器、已有数据库、已有测试数据、前端调用和 JudgeServer 协议均保持兼容；
- 不改 Django App label、数据库表名、`/api` 路径、响应包装或判题结果字段；
- 不在这次目录迁移中升级 Vue、Webpack、Django、PostgreSQL、Redis 或替换消息队列。

现代化（Vue 3/Vite、Django 升级、API v2、对象存储、可靠队列、Token 轮换等）应在稳定的三模块布局之后单独规划。

### 3.2 目标目录

```text
xju-OJ/
├── frontend/                         # 唯一的浏览器静态入口与网关
│   ├── src/                          # 保留现有 Vue 双入口源码
│   ├── build/  config/  static/
│   ├── nginx/                        # /、/admin、/api、/public 路由
│   ├── Dockerfile
│   ├── package.json
│   └── README.md
├── backend/                          # Django 业务 API 与异步任务
│   ├── oj/  account/  announcement/  conf/  contest/
│   ├── judge/  options/  problem/  submission/  utils/  fps/
│   ├── deploy/                       # API/worker/bootstrap 脚本；不再托管前端 Nginx
│   ├── resources/bootstrap/          # 默认头像、favicon 等可版本化种子资源
│   ├── Dockerfile
│   ├── manage.py
│   └── README.md
├── server/                           # 判题服务主模块
│   ├── judge-server/                 # 现 JudgeServer 的 Flask、client、tests
│   ├── judger/                       # 现顶层 Judger 的 C/Seccomp 和 bindings
│   ├── Dockerfile                    # 同时消费上述两个子树
│   ├── LICENSES.md
│   └── README.md
├── deploy/                           # 仓库级运行配置，不是第四业务模块
│   ├── compose.yaml
│   ├── compose.dev.yaml
│   ├── compose.legacy.yaml           # 仅兼容窗口保留
│   └── env.example
├── docs/
│   ├── contracts/
│   ├── operations/
│   └── plans/oj-unification/
├── .github/workflows/
├── .gitignore
├── README.md
└── README.en.md
```

### 3.3 目标容器拓扑

```text
Internet
  │ :80/:443
  ▼
frontend (Nginx)
  ├── /、/admin        -> frontend 静态产物
  ├── /api             -> backend-api:8000（同源转发）
  └── /public          -> 只读挂载的 runtime/backend/public

backend-migrate（一次性） -> PostgreSQL
backend-api（Gunicorn）   -> PostgreSQL + Redis
backend-worker（Dramatiq）-> PostgreSQL + Redis -> server:8080
server (JudgeServer)      -> read-only test_case + 私有工作卷
```

保留 `oj-postgres`、`oj-redis` 是运行基础设施，不把它们误称为第四或第五业务模块。第一轮继续让前端 Nginx 通过同域 `/api` 反向代理后端，从而保留 Django Session、`csrftoken`、`X-CSRFToken` 与相对 Axios 基址；不急于引入 CORS 或跨域 Cookie。

## 4. 必须保持的兼容契约

| 契约 | 当前证据 | 第一轮要求 |
|---|---|---|
| 浏览器 API 基址 | `OnlineJudgeFE/src/pages/{oj,admin}/api.js` 均使用 `/api` | 保持 `/api`，不改成跨域 URL |
| HTTP 响应 | `utils/api/api.py`：`{"error": ..., "data": ...}` | 字段、错误语义和 HTTP 使用方式不变 |
| 分页 | `limit`/`offset`，返回 `results`/`total` | 参数和返回键不变 |
| Session/CSRF | Django Session 在 Redis；前端使用 `csrftoken`/`X-CSRFToken` | 保持同源转发与 Cookie 行为 |
| 管理端路由 | Vue history base `/admin/` | `/admin/*` 刷新必须回退到 `/admin/index.html` |
| 公开文件 | `/public` -> 后端运行时 `data/public` | URL 不变；前端仅获得 `public` 只读挂载 |
| 测试数据 | `Problem.test_case_id` 对应 `/data/test_case/<id>` | 后端可写、server 只读；不暴露给前端 |
| 判题 HTTP | `POST /judge`、`POST /compile_spj`、`POST /ping` | 请求/响应形态与 `X-Judge-Server-Token` 不变 |
| 心跳 | `POST /api/judge_server_heartbeat/` | 保持 payload、SHA-256 token 头、服务名可达 |
| 判题结果 | `cpu_time`、`memory`、`result`、`test_case` 等 | 不改字段或结果码 |
| 数据库 | Django app label、`db_table`、迁移历史 | 不改 app 名、表名、迁移标识 |

完整样本及端点清单在阶段 0 生成到 `docs/contracts/`；该目录应成为以后版本化 API 的依据。

## 5. 关键决策

1. **目录收敛而非复制双写。** 完成基线提交后，以受控移动把四个目录变为三个主模块；不长期保留两份源代码或软链接。
2. **`server/` 内保留 `judge-server/` 与 `judger/`。** 这比把 Flask 和 C 核心扁平化低风险，也保留独立测试和许可证边界。
3. **前端拥有浏览器入口。** 后端不再下载 `dist.zip`、不再托管 Nginx 或 SPA 资源；前端 Nginx 负责静态资源、`/api` 代理和 `/public` 的受控只读发布。
4. **后端拆分进程但共用业务镜像。** API、Dramatiq worker、一次性迁移/初始化作为 Compose 中不同服务运行，避免 Supervisor 同时托管不相关职责。
5. **持久化路径可配置。** 默认使用仓库外或明确忽略的 `runtime/` 根，而非把环境数据混在源码目录；不把数据库、Redis、测试数据、密钥、上传文件或日志提交 Git。
6. **先兼容、后升级。** 当前 Vue 2/Webpack 3 与 Django 3.2 的升级不在目录切换提交中进行。每个升级必须有单独设计、契约测试和回滚策略。
7. **许可证不合并。** `frontend` 与 `backend` 的 MIT 文本、`server/judge-server` 与 `server/judger` 的 SATA 文本均保留；在 `server/LICENSES.md` 说明归属。

## 6. 不在本计划首轮交付中的事项

- 将 Vue 2/webpack 3 重写为 Vue 3/Vite；
- 将 Django app（如 `account`、`problem`）改名，或重建迁移历史；
- 变更 PostgreSQL/Redis 主版本，或更换 Dramatiq broker；
- 将 Session 改为 JWT、把 `/api` 改为跨域；
- 引入对象存储、Kubernetes、服务网格或独立 API Gateway；
- 改造 JudgeServer token 签名算法、外部调度协议或 Judger seccomp 规则；
- 以“清理”为理由删除可用的老数据、迁移或测试。

这些事项可在统一布局稳定后另立 RFC；其中硬编码初始管理员、固定 Sentry DSN、`ALLOWED_HOSTS=['*']`、token 明文存储、`service_url` 信任边界等安全问题必须登记为后续整改项，但不应与目录重组混成无法回滚的大改。

## 7. 全局完成标准

在阶段 6 结束前，必须同时满足：

1. 根目录只有 `frontend/`、`backend/`、`server/` 三个业务主模块，旧四个目录已从最终分支删除；
2. 所有源码（除明确忽略的运行时数据）已由 Git 纳管，`git status` 干净；
3. `docker compose -f deploy/compose.yaml config` 成功，且构建上下文只引用目标目录；
4. 前端可独立构建，并可直接刷新用户路由与 `/admin/*` 路由；
5. 后端可独立运行 `check`、迁移计划和原有测试；
6. API + Worker + Server 可完成一次 C/C++、解释型语言和 SPJ（若样例具备）的端到端判题；
7. `/api/website/`、登录/Session、上传、`/public`、题目、提交、比赛/排名、JudgeServer 心跳均通过回归；
8. PostgreSQL、Redis、测试数据、上传资源和密钥有经演练的备份/恢复记录；
9. 旧 Compose 镜像及数据备份在兼容窗口内仍可回滚；
10. 根 README、模块 README、环境变量示例、运维与许可证文档描述的是新路径而非上游四仓库布局。

## 8. 后续对话启动提示

执行时可以直接使用下面这句话：

```text
请阅读 docs/plans/oj-unification/README.md，并从 00-baseline-and-contracts.md 开始执行。严格保持现有 API、数据库表名和 JudgeServer 协议兼容；先完成该阶段的验收和提交，再进入下一阶段。
```
