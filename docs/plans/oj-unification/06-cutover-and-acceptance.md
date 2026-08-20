# 阶段 06：灰度切换、全链路验收与旧目录清理

## 目标

在不丢用户、题目、测试数据、提交、排名、Session/队列和判题结果的前提下，将流量从旧拓扑切换到新三模块拓扑；完成可回滚观察窗口后，才删除旧目录、旧 Compose 和隐式上游依赖。

## 进入条件

- 阶段 00–05 的提交已合并到待发布分支，工作树干净。
- 新 `frontend`、`backend`、`server` 镜像均有不可变 tag/digest。
- 新 Compose 已在与生产相似的隔离环境完成一次全链路测试。
- PostgreSQL、Redis、backend runtime、test_case、public、secret/证书的恢复演练已成功。
- 已指定切换负责人、回滚负责人、观测窗口和业务冻结窗口；没有这些责任边界时不要切生产。

## 步骤 06.1：发布前冻结与双份备份

在停止旧流量或暂停提交前，记录：

```text
发布 commit 与三镜像 digest
当前数据库 migration 状态
User/Problem/Contest/Submission/JudgeServer 行数
待判队列长度和 Pending/Judging 数量
test_case 目录数量及总 hash/大小
public 上传目录清单/大小
当前 JUDGE_SERVER_TOKEN 是否一致（只比对 hash，不打印原值）
当前 Compose 服务与卷
```

执行安全备份：

```bash
pg_dump -Fc -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -f "$BACKUP_DIR/onlinejudge-before-cutover.dump"

tar -czf "$BACKUP_DIR/backend-runtime-before-cutover.tgz" \
  "$RUNTIME_ROOT/backend/config" \
  "$RUNTIME_ROOT/backend/public" \
  "$RUNTIME_ROOT/backend/test_case" \
  "$RUNTIME_ROOT/backend/ssl"
```

Redis 备份/持久化必须按部署方式执行；如果无法确认 DB 1 Session 和 DB 4 Dramatiq 的一致性，先暂停新提交并记录队列，不能直接切换。

不要把下面内容放入日志：

```text
POSTGRES_PASSWORD
JUDGE_SERVER_TOKEN
secret.key
TLS private key
用户 Session/Cookie
```

## 步骤 06.2：在备用端口启动新栈

新栈先以独立 Compose project 和非生产宿主端口启动，使用同一份**数据库备份恢复出的验证库**或只读/克隆环境，不要一开始让新 worker 消费生产队列：

```bash
docker compose -p xju-oj-canary \
  --env-file deploy/.env.canary \
  -f deploy/compose.yaml \
  run --rm backend-migrate

docker compose -p xju-oj-canary \
  --env-file deploy/.env.canary \
  -f deploy/compose.yaml \
  up -d backend-api server frontend
```

先不启动 canary worker，完成 API/Server/静态服务检查后，再在隔离队列启动 worker。若使用同一生产 Redis，必须明确队列归属和暂停旧 worker，否则会重复消费；默认策略是使用克隆数据/Redis。

## 步骤 06.3：执行分层验收

### A. 容器、网络和安全

```bash
docker compose -p xju-oj-canary ps
docker compose -p xju-oj-canary config
docker inspect <frontend-container> <backend-api-container> <server-container>
```

检查：

- frontend 是唯一公开入口；
- backend-api/worker/server 没有宿主公网端口；
- server `read_only`、tmpfs、cap_drop 和卷模式正确；
- frontend 没有 secret/config/test_case/judger 挂载；
- backend API/Worker 用户、目录 owner 和日志权限正确；
- 镜像内没有 Token、数据库密码、生产证书或未锁定源码下载残留。

### B. 静态页面和 API 网关

```bash
curl -fsS http://<canary-host>/ | grep -q '<html'
curl -fsS http://<canary-host>/admin/ | grep -q '<html'
curl -fsS http://<canary-host>/problem >/dev/null
curl -fsS http://<canary-host>/status/demo >/dev/null
curl -fsS http://<canary-host>/public/website/favicon.ico >/dev/null
curl -fsS http://<canary-host>/api/website/ >/tmp/website.json
```

确认：

- 用户端和管理端 history 路由刷新成功；
- `/api` 响应仍是 `error/data` 包装；
- `/public` 只暴露允许的静态资源；
- `secret.key`、test_case、日志不会通过 URL 读取；
- Nginx 不泄露 backend-api/server 内部地址到响应。

### C. 认证、CSRF、权限

用测试账户执行并记录结果：

1. 登录、退出、错误密码；
2. Session 列表、删除其他 Session 的权限边界；
3. 用户端 JSON 写请求带 CSRF；
4. 管理员 API 的普通用户拒绝、管理员允许、超级管理员专属操作；
5. `APPKEY` API 认证和失效 key；
6. TFA（若启用）、密码/邮箱变更、重置密码；
7. 头像、Simditor 文件/图片上传和大小限制；
8. CSRF 豁免的 heartbeat、上传、导入接口只允许其设计的认证方式。

不要用浏览器导出的真实生产 Cookie 做测试 fixture。

### D. OJ 业务回归

至少覆盖：

| 领域 | 验收场景 |
|---|---|
| 公告/网站 | 公开读取、管理员增删改、配置缓存刷新 |
| 题目 | 标签、列表、详情、公开/比赛题目、模板和语言限制 |
| 测试数据 | 上传、读取、导入、导出、孤立目录清理；数据库与磁盘 ID 一致 |
| 提交 | 新建、列表、详情、分享、权限、重判、错误状态 |
| 比赛 | 创建/编辑、密码、开始/结束、ACM/OI、公告、排名、IP 限制 |
| 管理 | 用户、SMTP（用测试 SMTP）、JudgeServer 状态、仪表盘 |
| 多语言 | C/C++/Python3/Java/Go/JavaScript；与阶段 04 一致 |

### E. 判题链路和故障恢复

按顺序验证：

1. server 启动并向 backend heartbeat 注册；
2. backend 管理页显示 server `normal`、版本、CPU/内存和 service URL；
3. 提交一份 AC；
4. 提交一份 WA、编译错误、超时/运行时错误；
5. 暂停 server，提交一份代码，确认 Submission 为可观察 Pending 且进入 waiting queue；
6. 恢复 server，确认 heartbeat/`process_pending_task()` 使任务重新派发；
7. 重启 backend-api，不重置管理员、Token 或队列；
8. 重启 backend-worker，确认任务不会静默丢失；
9. 运行 SPJ 编译和判题（若已有可用题目）；
10. 对比赛提交检查排名、统计和用户题目状态只更新一次。

判题响应和提交状态必须用阶段 00 的 contract fixture/测试比对，不要只看页面显示 AC。

## 步骤 06.4：数据一致性核对

切换前后在同一快照上比较：

```text
数据库 migration 版本
用户、题目、比赛、提交、公告、JudgeServer 行数
关键表主键集合和最近 N 条提交 ID
Submission result/info/statistic_info
Problem test_case_id、Problem statistic_info
ACM/OI rank submission_info
SysOptions keys（Token 只比 hash）
```

文件核对：

```text
每个 Problem.test_case_id 都对应 runtime/backend/test_case/<id>/info
每个 info 中的 test_cases 可读且输入/输出 hash 未变
public/avatar、public/upload、public/website 文件未丢失
config/secret.key 未被替换
```

若业务量大，使用哈希/计数/抽样清单而不是把源代码、邮箱或 Token 输出到日志。

## 步骤 06.5：灰度切换

推荐顺序：

1. 旧栈继续提供流量，新栈完成备用端口验收；
2. 暂停新提交或进入公告维护窗口，等待正在进行的判题任务完成；
3. 停止旧 API/worker 的写入入口，但保留旧 server/日志可回滚；
4. 将入口反向代理/DNS/端口切到新 frontend；
5. 启动新 backend-worker 和 server heartbeat；
6. 用内部测试账户完成一次登录、题目读取和 AC 提交；
7. 观察 API 5xx、Django error、Worker 异常、waiting queue、server heartbeat 和数据库连接；
8. 达到团队约定的观察窗口且无停止条件后恢复正常流量。

不要同时做数据库 schema 重构、依赖大升级、API v2、Token 算法替换或 PostgreSQL/Redis 主版本升级。

## 步骤 06.6：回滚流程（必须演练）

任一停止条件出现时，按固定顺序：

1. 停止新 frontend 流量和新 backend-worker；
2. 保存新栈日志、队列长度、最近提交和 server 状态；
3. 恢复旧 frontend/backend/judge 镜像与旧 Compose 配置；
4. 若只做目录/容器切换且无 schema 变化，优先复用原数据库与 runtime 数据；
5. 若已执行不可逆迁移或数据写入异常，停止写入并按批准的 PostgreSQL dump/runtime/Redis 恢复方案恢复；
6. 恢复旧 worker 前确认没有新旧 worker 同时消费同一队列；
7. 启动旧栈并检查 `/api/website/`、登录、题目、提交、heartbeat；
8. 对比 Pending/Judging 任务，必要时由管理员按清单重排队，禁止盲目批量重判；
9. 发布回滚公告并记录根因，修复后重新从隔离环境开始。

禁止用以下方式“回滚”：

```text
删除 django_migrations 记录
migrate app zero（未审查数据迁移）
FLUSHALL Redis
删除 runtime/test_case
覆盖生产 secret.key
```

## 步骤 06.7：兼容窗口后的清理

只有在新栈稳定、备份可恢复、业务负责人签字后才做：

1. 删除根旧 `docker-compose.yml` 或改名为已说明的 legacy 文件；
2. 删除旧 `OnlineJudgeFE/`、`OnlineJudge/`、`JudgeServer/`、`Judger/` 残留（迁移提交已确认无重复源）；
3. 删除失效 `.gitmodules`、旧模块 CI 和后端内嵌前端 downloader；
4. 删除不再使用的旧前端 release 下载脚本、Supervisor/Nginx 配置；
5. 清理旧镜像和旧运行卷前，保留规定的回滚备份；
6. 更新根 README、CHANGELOG 和版本发布说明；
7. `git grep` 确认没有旧目录/服务名的运行时引用。

最终检查：

```bash
find . -maxdepth 1 -mindepth 1 -type d -not -name .git -printf '%f\n' | sort
git grep -nE 'OnlineJudgeFE|OnlineJudge/|JudgeServer/|Judger/|oj-backend:|oj-judge:|oj_2\.7\.5|COPY Judger' -- ':!docs/plans/**' || true
git diff --check
git status --short --branch
```

## 最终验收清单

### 结构

- [ ] 根一级业务模块只有 `frontend`、`backend`、`server`。
- [ ] server 内保留 `judge-server`/`judger` 边界，只有一份 Judger 源码。
- [ ] 所有源码和文档已 Git 纳管，运行时数据未纳管。

### 构建/部署

- [ ] 三镜像可从本仓库构建，未下载隐式上游前端/判题源码。
- [ ] frontend/API/worker/server/数据库/Redis 服务边界和卷权限正确。
- [ ] CI、Compose、环境示例、发布 tag/digest 一致。

### 功能/协议

- [ ] 静态 history 路由、`/api`、`/public`、Session/CSRF、上传全部通过。
- [ ] 原有 API `error/data`、分页、错误码和管理员权限通过。
- [ ] heartbeat、`/ping`、`/judge`、`/compile_spj` 和结果字段通过。
- [ ] 多语言、SPJ、Pending/retry、ACM/OI 统计通过。

### 数据/运维/安全

- [ ] PostgreSQL、Redis、test_case、public、secret/证书备份和恢复已演练。
- [ ] server 沙箱安全约束未放宽，frontend 没有秘密和测试数据。
- [ ] 默认生产管理员凭据不再硬编码，Token/DSN/Host 配置边界明确。
- [ ] 回滚在备用环境或维护窗口实际演练过。

## 完成状态

阶段 06 完成后，才可以将本仓库称为“统一的前后端分离 OJ 单仓库”。后续若要做 Vue/Vite、Django 升级、API v2、数据库结构化、可靠队列或安全协议升级，应以当前三模块版本为基线另立计划，不再回到四目录/隐式镜像布局。
