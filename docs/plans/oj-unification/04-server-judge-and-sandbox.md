# 阶段 04：收敛 server、JudgeServer 与 Judger

## 目标

把现有 `JudgeServer/` 与顶层 `Judger/` 统一纳入 `server/` 主模块，同时保持 Flask 判题 HTTP 协议、Python binding、C/Seccomp 安全边界和独立测试能力。第一轮只修正目录/build context/镜像边界，不重写沙箱，不修改结果码或语言配置。

## 进入条件

- 阶段 00 的 JudgeServer 协议样本和语言矩阵已完成。
- 阶段 01 已完成 `server/judge-server/` 与 `server/judger/` 目录移动。
- 明确 `server/judge-server/Judger/` 不是源码：当前是空目录，不能作为 build input。
- backend 阶段已确定实际 server 服务名、heartbeat URL 和 Token 来源；若未确定，先不要构建生产镜像。

## 当前事实

- `JudgeServer/server/server.py` 提供 Flask app，并接受 `POST /judge`、`POST /ping`、`POST /compile_spj`。
- `JudgeServer/server/utils.py` 从环境变量 `TOKEN` 读取明文，再在进程内计算 SHA-256；请求头比较的是 hash。
- `JudgeServer/server/service.py` 将 heartbeat 发到 `BACKEND_URL`，请求头为 `X-JUDGE-SERVER-TOKEN`。
- `JudgeServer/server/config.py` 在 import 时查找 `code`、`compiler`、`spj` 三个系统用户及固定工作目录：`/judger/run`、`/judger/spj`、`/test_case`、`/log`。
- `JudgeServer/server/judge_client.py` 通过 `_judger` Python binding 运行编译、Seccomp、资源限制和 SPJ；测试点并行度使用 `psutil.cpu_count()`。
- `Judger/bindings/Python/_judger/__init__.py` 调用 `/usr/lib/judger/libjudger.so`，版本常量 `0x020101`；C 核心定义资源限制、结果码和 Seccomp 规则。
- 现 `JudgeServer/Dockerfile` 的 `COPY Judger/ /app/` 只在“JudgeServer 内含子模块”旧布局下成立；当前根目录 build context 下也需要显式重写。

## 目标内部布局

```text
server/
├── judge-server/
│   ├── server/                 # 保留平面 Python 模块名，减少 import 变化
│   ├── client/                 # Python/Go/PHP SDK
│   ├── tests/
│   ├── README.md
│   └── LICENSE
├── judger/
│   ├── src/
│   ├── bindings/
│   ├── tests/
│   ├── CMakeLists.txt
│   ├── README.md
│   └── LICENSE
├── Dockerfile
├── LICENSES.md
└── README.md
```

不建议第一轮扁平化成 `server/src`、`server/api`、`server/bindings`：那会同时改变 CMake、Python import、测试路径、Docker COPY 和许可证归属，且没有收益。

## 步骤 04.1：清理历史子模块声明

确认当前 Git 索引没有 gitlink 后，删除：

```text
server/judge-server/.gitmodules
server/judge-server/Judger/（空目录，不应创建占位源码）
```

在 `server/README.md` 和 `docs/contracts/path-reference-inventory.md` 记录：

```text
历史 JudgeServer 项目曾以 Judger 子模块构建；本仓库现将真实源码纳入 server/judger，使用单仓库版本和审计提交，不再依赖未初始化子模块。
```

若未来确实要恢复外部子模块，另立决策，不能同时保留同名源码副本。

## 步骤 04.2：重写统一 Docker build context

新增 `server/Dockerfile`，以仓库根目录为 build context，或者以 `server/` 为 build context；二者只能选一种并在 Compose/CI 固化。建议使用 `server/` 作为 context，避免把 backend/frontend/运行时送入判题镜像：

```text
server/Dockerfile
COPY judger/ /src/judger/
COPY judge-server/server/ /app/
```

### 构建阶段

1. 保留 `debian:trixie-slim` 或经过基线验证的固定基础镜像；
2. 安装 CMake、gcc、Python、libseccomp-dev；
3. `cmake -S /src/judger -B /src/judger/build` 并构建 C 核心；
4. 在 `judger/bindings/Python` 构建 wheel；
5. 不从网络拉取 Judger 源码或其他未锁定源码。

### 运行阶段

1. 安装运行语言：C/C++、Java、Python、Go、Node，版本必须与 `backend/judge/languages.py` 的 description/compile command 相符；
2. 创建固定 UID/GID 的 `compiler`、`code`、`spj` 用户；
3. 复制 `libjudger.so` 到 `/usr/lib/judger/`；
4. 安装 `_judger` wheel 和 Flask/Gunicorn/psutil/requests；
5. 将 `judge-server/server/` 内容复制到 `/app/`，保持 `from config import ...`、`gunicorn server:app` 的平面 import 语义；
6. `entrypoint.sh` 创建并清空 `/judger/run`、`/judger/spj`，但只能清理 server 专属工作卷，不得清理 `/test_case` 或 backend 数据；
7. 镜像默认只监听 8080，不映射到公网。

构建检查：

```bash
docker build --file server/Dockerfile --tag xju-oj/server:layout-check server
docker run --rm --entrypoint /app/.venv/bin/python3 xju-oj/server:layout-check -c \
  'import _judger; print(_judger.VERSION)'
```

实际镜像若 Python 可执行路径不同，按镜像内真实路径调整，但必须检查 `_judger.VERSION`、`libjudger.so` 和三个系统用户均存在。

## 步骤 04.3：保留协议和认证实现

不要在目录迁移中改变：

```text
POST /judge
POST /compile_spj
POST /ping
X-Judge-Server-Token
{"err": null|..., "data": ...}
```

服务器端的请求处理必须继续：

- 仅接受 POST；
- 对非法 path 返回 `InvalidRequest`；
- Token 不匹配返回 `TokenVerificationFailed`；
- 编译错误返回 `CompileError`/`SPJCompileError`；
- 业务错误包装字段仍是 `err`、`data`；
- `ping` 返回 `action=pong` 与 server_info；
- heartbeat 使用 hashed token 调用 backend，成功响应必须包含 `error` 字段且为空。

为协议建立脱敏 fixture 和客户端测试：

```text
server/judge-server/tests/fixtures/ping-success.json
server/judge-server/tests/fixtures/invalid-token.json
server/judge-server/tests/fixtures/heartbeat.json
server/judge-server/tests/fixtures/judge-request-minimal.json
```

fixture 不包含真实 Token、真实源码密钥或生产 URL。

## 步骤 04.4：验证安全边界和文件权限

必须保留并验证以下约束：

| 边界 | 验收 |
|---|---|
| Server 容器只读根文件系统 | Compose `read_only: true`；可写仅是 tmpfs/`/judger`/`/log` |
| 测试数据 | `/test_case:ro`，server 不能修改输入/标准输出基准 |
| 编译/运行用户 | `compiler` 只编译，`code` 运行，`spj` 执行 SPJ |
| Seccomp | `c_cpp`、`c_cpp_file_io`、`general`、`golang`、`node` 规则名称不变 |
| 资源限制 | CPU、real time、memory、stack、output、process 数字段不变 |
| 工作目录 | 每次 submission 独立；非 DEBUG 结束后清理 |
| 网络暴露 | 只允许 backend 调用；开发 profile 才映射调试端口 |
| Token | 只注入 server 进程环境，不写镜像、日志或 frontend |

在隔离容器中检查：

```bash
docker inspect xju-oj/server:layout-check
mkdir -p runtime/backend/test_case runtime/judge-server/log runtime/judge-server/run
docker run --rm --read-only --tmpfs /tmp \
  --mount type=bind,src="$PWD/runtime/backend/test_case",dst=/test_case,readonly \
  --mount type=bind,src="$PWD/runtime/judge-server/log",dst=/log \
  --mount type=bind,src="$PWD/runtime/judge-server/run",dst=/judger \
  --entrypoint /bin/sh \
  xju-oj/server:layout-check \
  -ec 'id compiler; id code; id spj; test -r /test_case; test -w /log; test -w /judger'
```

不要在开发机直接运行需要 root/seccomp 的 Judger 二进制；优先使用仓库提供的 Docker 测试镜像。

## 步骤 04.5：迁移并保留 Judger 独立测试

从 `server/judger/` 运行：

```bash
cmake -S . -B build
cmake --build build --parallel "$(nproc)"
```

保留并修正（仅路径，不改测试语义）：

```text
server/judger/tests/runtest.sh
server/judger/tests/Dockerfile-16.04
server/judger/tests/Dockerfile-18.04
server/judger/tests/Python_and_core/
server/judger/tests/Nodejs_and_core/
server/judger/tests/test_src/integration/
server/judger/tests/test_src/seccomp/
```

测试重点：

- 正常执行、编译错误、超时、内存、输出大小、进程数；
- C/C++ 标准 IO 与 File IO；
- Python/Node binding；
- Seccomp 禁止 `execve`、fork、写文件等样例；
- 非 root 调用和 UID/GID 传递；
- `_judger` JSON 字段与 backend dispatcher 消费字段一致。

## 步骤 04.6：验证语言与 SPJ 端到端

以 `backend/judge/languages.py` 为唯一语言配置来源，至少运行：

| 语言 | 编译/运行 | 预期 |
|---|---|---|
| C | gcc 编译 + 标准 IO | AC、WA、编译错误各一例 |
| C++ | g++ 编译 + 标准 IO | AC、资源限制 |
| Python3 | py_compile + 运行 | AC、运行时错误 |
| Java | javac + Main | AC、内存检查模式 |
| Go | go build | AC、缓存目录可写 |
| JavaScript | node --check + node | AC、Seccomp 规则 |
| SPJ | compile_spj + judge | 正确、错误、SPJ 错误 |

先直接用 `server/judge-server/client/Python/client.py` 或 Go client 调 `/ping`/`/judge`，再用 backend 提交链路。不要只测 server 独立接口。

## 步骤 04.7：修正 CI 和客户端路径

迁移后搜索并处理：

```bash
rg -n --hidden -g '!*.lock' \
  '(COPY Judger|JudgeServer|Judger|client/Python|tests/test_case|qduoj/judge-server)' \
  server .github deploy README*.md
```

- JudgeServer 原有 Go/PHP/Python client 保留在 `server/judge-server/client/`；
- 客户端 README 中的上游 import/module 路径标注为 SDK 使用说明，不要误改成仓库内部 import；
- `.travis.yml` 若保留，改为指向新 context；更推荐在阶段 05 统一到 root workflow；
- server release workflow 的 Docker build context 必须是 `server/`，不能默认根目录；
- Judger 的 C 测试 workflow 必须在 `server/judger/` context 下运行。

## 许可证与归属

- 保留 `server/judge-server/LICENSE` 和 `server/judger/LICENSE`；
- `server/LICENSES.md` 说明两个 SATA 组件的版权、项目 URL 和原始条件；
- 不把 SATA 代码包装成 MIT；
- 新增 glue code 的版权归属单独标明；
- 不删除上游 README、版本常量和致谢信息。

## 建议提交点

```text
refactor(server): merge judge-server and judger under one module
build(server): fix sandbox build context and image layout
 test(server): preserve protocol language and sandbox coverage
```

## 验收门槛

- [ ] `docker build -f server/Dockerfile server` 成功，且不依赖空的 `JudgeServer/Judger`。
- [ ] `_judger`、`libjudger.so`、三类运行用户、编译器和语言运行时存在。
- [ ] `/ping`、错误 Token、`/judge`、`/compile_spj` 的响应形态未变。
- [ ] heartbeat 能在内部网络调用 backend，backend 能发现并调度 server。
- [ ] C/Python/Node/Seccomp 测试和语言/SPJ 端到端矩阵通过。
- [ ] `read_only`、只读 test_case、工作目录清理和权限边界通过审查。
- [ ] SATA/MIT 许可证边界和客户端文档完整。

## 停止条件与回滚

任何 Seccomp 测试回归、资源限制放宽、容器 root 执行用户代码、测试数据可写、Token 不匹配、JudgeServer 结果字段变化都必须停止。回滚为恢复旧 `judge:1.6.1` 镜像和旧 Compose；保留新的 server 构建产物和日志供诊断，不直接替换生产判题服务。
