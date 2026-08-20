# JudgeServer 协议兼容契约

本文固定当前代码中的脱敏协议形态。所有示例值均为合成占位值；`<token_sha256>` 只表示配置 Token 的 SHA-256 十六进制摘要，不是可用凭据。来源限定为：

- `OnlineJudge/judge/dispatcher.py`
- `OnlineJudge/conf/{serializers.py,views.py}`
- `JudgeServer/server/{server.py,service.py,utils.py}`
- `JudgeServer/server/judge_client.py`
- `JudgeServer/client/{Python,go,PHP}` 及现有测试

## 共同规则

- Backend 与 JudgeServer 之间、JudgeServer 心跳与 Backend 之间均使用 HTTP POST。
- 请求头名称在现有代码中出现两种大小写：`X-Judge-Server-Token` 和 `X-JUDGE-SERVER-TOKEN`；HTTP 头名称大小写不敏感，兼容实现不得改变语义。
- 头值是同一个配置明文 Token 的 SHA-256 十六进制摘要，绝不在线上传输明文 Token。
- 判题服务响应包装是 `{"err": ..., "data": ...}`；Django API/心跳响应包装是 `{"error": ..., "data": ...}`，不可混用。
- 现有 Django API 还固定 `Content-Type: application/json;charset=UTF-8` 的 JSON 响应；文件下载和 Simditor 上传是显式例外。

## Backend -> JudgeServer

### `POST /judge`

请求头：

```http
X-Judge-Server-Token: <token_sha256>
Content-Type: application/json
```

请求体的兼容字段：

```json
{
  "language_config": {
    "compile": {"src_name": "main.c"},
    "run": {"exe_name": "main", "command": ["..."], "seccomp_rule": "..."}
  },
  "src": "<source>",
  "max_cpu_time": 1000,
  "max_memory": 268435456,
  "test_case_id": "<mounted-test-case-id>",
  "test_case": null,
  "spj_version": null,
  "spj_config": null,
  "spj_compile_config": null,
  "spj_src": null,
  "output": false,
  "io_mode": {"io_mode": "Standard IO", "input": "input.txt", "output": "output.txt"}
}
```

字段约束和来源：

| 字段 | 兼容要求 |
|---|---|
| `language_config` | 必须有 `run`；`run` 至少被服务端消费 `command`、`seccomp_rule`，可带 `env`、`memory_limit_check_only`；有编译配置时消费 `compile.src_name` 等字段 |
| `src` | 源码字符串；服务端按语言配置写入/编译 |
| `max_cpu_time` | 由后端问题时间限制传入；精确底层单位以 Judger 当前实现为准，目录迁移不得转换 |
| `max_memory` | Backend 按 `1024 * 1024 * memory_limit` 传递，保持当前字节语义 |
| `test_case_id` / `test_case` | 必须恰有一个为真值；挂载题库时用 `test_case_id`，动态测试用 `test_case` |
| `test_case` | 动态测试点数组，单项至少 `{input, output}`；SPJ 动态用例仍保持 `input` 字段 |
| `spj_version` / `spj_config` / `spj_compile_config` / `spj_src` | SPJ 编译和运行字段；`spj_config` 至少消费 `exe_name`、`command`、`seccomp_rule`；不得改名 |
| `output` | 当前 Backend 固定传 `false`；为 true 时服务端才尝试回传输出文本 |
| `io_mode` | 缺失时服务端默认为 `Standard IO`；`File IO` 时保留 `input`、`output` 文件名 |

成功响应（脱敏样本）：

```json
{
  "err": null,
  "data": [
    {
      "cpu_time": 12,
      "memory": 4096,
      "real_time": 15,
      "result": 0,
      "signal": 0,
      "exit_code": 0,
      "error": 0,
      "output_md5": "<md5-or-null>",
      "output": null,
      "test_case": "1"
    }
  ]
}
```

判题结果数组必须保留这些字段：`cpu_time`、`memory`、`real_time`、`result`、`signal`、`exit_code`、`error`、`output_md5`、`output`、`test_case`。Backend 依赖 `cpu_time`、`memory`、`result`、`test_case`；`result == 0` 表示测试点通过。现有结果码包括：`-2` 编译错误、`-1` 答案错误、`0` 通过、`1` CPU 超时、`2` 实时超时、`3` 内存超限、`4` 运行时错误、`5` 系统错误；该枚举来自 `Judger/src/runner.h` 与 `OnlineJudge/submission/models.py`，不得重编号。

错误响应（HTTP 状态码策略由部署层决定，当前服务端代码固定响应体）：

```json
{"err": "TokenVerificationFailed", "data": "<message>"}
{"err": "CompileError", "data": "<message>"}
{"err": "SPJCompileError", "data": "<message>"}
{"err": "JudgeClientError", "data": "<message>"}
{"err": "InvalidRequest", "data": "404"}
```

### `POST /compile_spj`

请求：

```http
X-Judge-Server-Token: <token_sha256>
Content-Type: application/json
```

```json
{
  "src": "<spj-source>",
  "spj_version": "<version>",
  "spj_compile_config": {"src_name": "spj-{spj_version}.c", "exe_name": "spj-{spj_version}"}
}
```

成功响应：`{"err": null, "data": "success"}`。编译失败保持 `SPJCompileError`/`data` 文本包装；Backend 会把 `err` 对应的 `data` 作为编译失败信息返回给管理端。

### `POST /ping`

请求体可为空；仍需携带同一摘要头。成功响应：

```json
{
  "err": null,
  "data": {
    "hostname": "example-judge",
    "judger_version": "2.1.1",
    "cpu_core": 4,
    "cpu": 0.0,
    "memory": 0.0,
    "action": "pong"
  }
}
```

`action: "pong"`、资源字段和 Judger 版本来源于 `server_info()`；不能在迁移时替换为另一套字段名。

## JudgeServer -> Backend 心跳

### `POST /api/judge_server_heartbeat/`

路由允许末尾 `/`（保留无尾斜杠兼容）。请求：

```http
X-JUDGE-SERVER-TOKEN: <token_sha256>
Content-Type: application/json
```

```json
{
  "hostname": "example-judge",
  "judger_version": "2.1.1",
  "cpu_core": 4,
  "memory": 0.0,
  "cpu": 0.0,
  "action": "heartbeat",
  "service_url": "http://oj-judge:8080"
}
```

Serializer 约束：`hostname` 最长 128；`judger_version` 最长 32；`cpu_core >= 1`；`memory`、`cpu` 为 0–100 浮点数；`action` 只能是 `heartbeat`；`service_url` 最长 256。`service_url` 只做字符串长度校验，当前代码不保证 URL 可达性或来源绑定。

成功响应：

```json
{"error": null, "data": null}
```

认证失败：

```json
{"error": "error", "data": "Invalid token"}
```

请求解析或字段失败保持 `invalid-<field>` + 说明的包装；未捕获服务端异常保持 `{"error":"server-error","data":"server error"}`。后端按 `hostname` 更新/创建 `JudgeServer`，写入版本、CPU 核数、CPU/内存占用、服务地址、来源 IP、最后心跳，并触发 waiting queue 处理。

## 兼容验证索引

- Backend 构造判题请求：`OnlineJudge/judge/dispatcher.py`
- Backend 心跳校验和持久化：`OnlineJudge/conf/views.py`
- 心跳字段校验：`OnlineJudge/conf/serializers.py`
- HTTP 路由与包装：`JudgeServer/server/server.py`
- 心跳客户端：`JudgeServer/server/service.py`
- Token 摘要和资源字段：`JudgeServer/server/utils.py`
- 判题结果消费：`JudgeServer/server/judge_client.py`、`OnlineJudge/judge/dispatcher.py`
- 现有测试：`OnlineJudge/conf/tests.py`、`JudgeServer/tests/tests.py`

当前测试没有覆盖所有结果码、`/judge` 完整成功字段、SPJ 错误边界、心跳无头/错误 action 和 `service_url` 信任边界；这些是后续契约测试项，不是本次目录基线阶段的行为变更许可。
