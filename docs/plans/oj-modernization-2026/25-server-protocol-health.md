# Step 25：Server 协议与健康状态

## 目标

确保工具链/镜像重建不改变 Judge 协议，并将本机 liveness 与 backend heartbeat readiness 解耦。

## 进入条件

- Step 23 build stages 可运行。
- Step 24 目标工具链在至少 amd64 上通过基础 corpus。
- 旧 server image 可用于逐字段比较。

## 不变量

### HTTP 与 Token

- `POST /judge`
- `POST /compile_spj`
- `POST /ping`
- `POST /api/judge_server_heartbeat/`
- `X-Judge-Server-Token`：原始 Token 的 SHA-256 hex digest 语义不变。
- Judge 包装仍为 `{"err": ..., "data": ...}`；backend API 不得误改为同一字段名。

### Judge 结果

保持：

```text
cpu_time memory real_time result signal exit_code error
output_md5 output test_case
```

保持结果码：`-2 CE`、`-1 WA`、`0 AC`、`1 CPU TLE`、`2 Real TLE`、`3 MLE`、`4 RE`、`5 System Error`。

`/compile_spj` 成功仍为 `{"err": null, "data": "success"}`；`/ping` 仍包含 `action=pong`、hostname、judger_version、cpu_core、cpu、memory 等字段。

## 健康设计

- Docker healthcheck 只请求本机 `/ping`，表示 JudgeServer 进程存活。
- heartbeat 单独记录 connected/degraded 状态；backend 暂时不可达不能导致 JudgeServer unhealthy/restart。
- backend healthcheck 使用 `/api/website/` 和 Redis/DB smoke；worker 使用进程/worker smoke。
- 不形成 backend-api → judge health → heartbeat → backend-api 的循环依赖。

## Secret 注入

当前 JudgeServer 只读取环境 `TOKEN`；另加 `TOKEN_FILE` 支持：

1. 文件存在且权限可读时读取原始 Token。
2. 没有 file 时才读取 `TOKEN`（生产优先 file）。
3. 计算 SHA-256 后比较 header。
4. 日志只显示“configured/missing/invalid”，不显示原始或 digest。

## 测试矩阵

- `/ping` 正确/错误/缺失 Token；backend down 时仍成功。
- `/judge` AC/CE/WA/各类 TLE/MLE/RE/system error。
- `/compile_spj` 成功/非法代码。
- heartbeat 正常/错误 Token/backend down/recovery/degraded。
- 字段、结果码、错误名和包装逐字段比旧镜像。
- `/test_case` 的 create/truncate/rename/unlink/chmod 全部被阻止。

## 计划命令

```bash
pytest -q server/judge-server/tests
bash server/judger/tests/runtest.sh
curl -fsS http://127.0.0.1:<test-port>/ping \
  -H 'X-Judge-Server-Token: <test-only-value>'
```

测试 Token 只来自隔离 Secret；生产 server 不发布 host port。

## 验收

- `/ping` 本地可用与 heartbeat degraded 独立。
- 旧/新 server 对协议 golden 的差异为零或逐项批准。
- Token file/environment 两种测试路径行为明确，日志脱敏。
- Judge 协议和 backend heartbeat 在内部网络上可达，无循环健康依赖。

## 停止条件

- backend down 导致容器重启/被判定死亡。
- Token digest、包装、字段或结果码改变。
- 测试需公开 8080、写 `/test_case` 或放宽权限。

## 回滚

切回旧 server image 和健康检查；不改变 backend API、数据库和 test_case 数据。

## 完成标志

提交格式建议：

```text
fix(server): separate liveness from backend heartbeat
```

下一步启用容器 hardening 和多架构门禁。
