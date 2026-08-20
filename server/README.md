# server

`server/` 是判题服务主模块，内部保留两个不可混淆的边界：

- `judge-server/`：Flask/Gunicorn HTTP 服务、客户端和协议测试；对外保持 `POST /judge`、`POST /compile_spj`、`POST /ping` 以及心跳调用。
- `judger/`：C/Seccomp 核心和 Python/Node/Lua bindings；负责资源限制、系统调用规则和结果码。

## 运行约束

- JudgeServer 只读挂载后端测试数据 `/test_case`；`Problem.test_case_id` 与该路径的目录名保持绑定。
- `/judger`、`/log` 和 `/test_case` 的权限边界由当前镜像/入口脚本定义；不要让用户代码以容器 root 运行。
- `X-Judge-Server-Token` 继续使用配置 Token 的 SHA-256 摘要；协议字段、`err/data` 响应包装和测试点结果码见 `docs/contracts/judge-server-protocol.md`。
- `judge-server/` 与 `judger/` 必须独立测试和构建；不得再次引入空的 `judge-server/Judger/` 或复制第二份 Judger 源码。

## 许可证

`judge-server/LICENSE` 与 `judger/LICENSE` 保留各自的 SATA 文本和上游归属。边界说明见 [LICENSES.md](LICENSES.md)。
