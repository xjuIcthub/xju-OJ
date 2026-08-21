# Step 01：行为合同与特征测试

## 目标

在任何依赖、框架或镜像升级前，把现有行为转成可重复的黑盒/golden 测试。测试先记录现状，不先修正旧行为。

## 进入条件

- Step 00 的版本锁和兼容合同已提交。
- 测试环境使用现有 `main` 镜像/源码，不能混入新版本。
- 测试数据使用脱敏 fixture；不得把生产用户、Token、密码或 dump 放入 Git。

## 新增测试资产

建议目录：

```text
docs/contracts/
  api-response-golden.json
  route-contract.md
  judge-protocol.md
  data-identity.md
frontend/tests/e2e/
backend/tests/contracts/
server/judge-server/tests/fixtures/
server/judger/tests/corpus/
```

可复用已有：

- `backend/deploy/runtime_smoke.py`
- `backend/deploy/health_check.py`
- `server/judge-server/tests/tests.py`
- `server/judger/tests/runtest.sh`

## 测试范围

### 浏览器和网关

- `/`、`/admin`、`/admin/`、至少一个用户端和管理端 deep link 刷新。
- `/api/website/` 的状态码、Content-Type、包装和分页。
- `/public/` 读取；不存在资源不进入错误的 SPA fallback。
- 登录、刷新、注销、Session 过期。
- 首次 GET 获取 `csrftoken`；合法 `X-CSRFToken` 成功；错误/缺失 token 被拒绝。
- Host、Referer、Origin、Cookie、`/api` 相对路径。

### Backend 数据和异步

- `showmigrations --plan`、app label、表名、`DEFAULT_AUTO_FIELD` 快照。
- PostgreSQL 关键模型的 schema、JSON/JSONB、sequence、索引和约束清单。
- Redis DB1/DB4 的连接 URL、key namespace、TTL 和 waiting_queue 结构。
- enqueue、成功、失败、retry、timeout、SIGTERM/restart、result key/TTL/serialization。

### Judge

- `/ping`：正确、错误、缺失 Token；backend 不可达时仍应成功。
- `/judge`：AC、CE、WA、CPU TLE、real TLE、MLE、RE、system error。
- `/compile_spj` 成功和非法代码。
- heartbeat 正常、Token 错误、backend down/recovery。
- 保存所有结果字段：`cpu_time`、`memory`、`real_time`、`result`、`signal`、`exit_code`、`error`、`output_md5`、`output`、`test_case`。
- 保存 Judge 的 `err/data` 包装与 backend API 的 `error/data` 差异。
- `/test_case` 写入、其他 workspace 读取、网络访问、进程/文件限制负向样例。

## 计划命令

```bash
cd backend
python manage.py check
python manage.py showmigrations --plan
python manage.py makemigrations --check --dry-run
python manage.py test
cd ..

# 仅在隔离测试 Compose 中
# docker compose -f <test-compose> up -d
# python backend/deploy/runtime_smoke.py --base-url <internal-url>
# curl -fsS http://<judge>/ping -H 'X-Judge-Server-Token: <test-only-derived-value>'
```

命令中的 Token 只能来自临时测试 Secret；不要把值写进脚本、日志或文档。

## 输出物

- 端点/路由清单。
- API JSON 和 HTTP 状态 golden。
- Session/CSRF cookie/header golden。
- migration/schema/sequence/Redis manifest。
- Judge 结果码和字段 golden。
- 现有测试收集数；不要直接采用报告里未实跑的“119 个测试”。
- 已知失败列表，逐项标为历史问题或本轮 blocker。

## 验收

- 基线测试可在干净环境重复运行两次，输出一致。
- 所有合同都有至少一个正向和一个负向样例。
- 测试不会连接真实生产数据或写入真实 Redis/数据库。
- golden 文件不包含凭据、个人信息或大体量运行数据。

## 停止条件

- 无法把当前行为与预期差异区分。
- 测试需要放宽 CSRF、Token、`/test_case` 权限或容器安全。
- 当前 baseline 本身无法完成基本 API/判题 smoke；先登记环境 blocker，不进入升级。

## 回滚

删除新增测试资产不会影响运行代码；保留失败记录，不能通过删除测试来“变绿”。

## 完成标志

提交格式建议：

```text
test: characterize OJ API session and judge contracts
```

后续任何 Step 都必须执行与此合同相关的最小回归。
