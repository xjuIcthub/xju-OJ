# xju-OJ `server` 模块 2026 技术升级与容器化专项调研报告

> **研究基线**：`main` / `2d84d089bcd8ea90d5836c00d7c46e6de47697fc`
> **调研时间截点**：2026-08-20
> **范围**：仅 `server/judge-server` + `server/judger`，不修改代码、不创建 PR。
> **结论标识**：**[已核实事实]**、**[架构建议]**、**[仍需实测]**

---

## 1. 执行摘要

### 1.1 最终推荐

**[架构建议]** 推荐将 2026 年 `server` 生产基线确定为：

| 层                    | 推荐                                                             |
| -------------------- | -------------------------------------------------------------- |
| OS                   | **Debian 13 / trixie-slim**，构建时固定 point release/base digest    |
| Python / JudgeServer | **Python 3.13.x（Debian 原生）**                                   |
| C/C++                | **GCC/G++ 14（Debian 原生）**                                      |
| Java                 | **OpenJDK 21**，第一阶段不升级 Java 25                                 |
| JavaScript           | **Node.js 24.x LTS（Krypton）**，从 Node 官方固定 stage 引入             |
| Go                   | **Go 1.26.x，截点可核实最新稳定补丁为 1.26.5**，从 Go 官方固定 stage 引入           |
| libseccomp           | Debian 13 原生 **2.6.x**                                         |
| Flask                | **3.1.x**                                                      |
| Gunicorn             | **26.x**，必须经过现有 WSGI/请求回归再启用                                   |
| requests             | **2.34.x**                                                     |
| psutil               | **7.2.x**                                                      |
| idna                 | 作为 requests 间接依赖由 `uv.lock` 锁定，不建议代码未直接使用时手工一级声明               |
| Python 依赖管理          | 独立 `server/judge-server/pyproject.toml + uv.lock`              |
| 容器                   | 一个最终 `server` image/container，同时包含 JudgeServer、Judger 和所有判题工具链 |
| 镜像结构                 | `judge-runtime-base` 重型低频基础镜像 → `judge-server` 轻量业务层           |
| 构建 context           | **仓库根目录 `.`**，Dockerfile 可放 `server/Dockerfile`                |
| 网络暴露                 | JudgeServer **只在 Compose 内网暴露，不发布 8080 到公网**                   |
| `/test_case`         | 始终 `read_only` / `:ro`                                         |
| 容器用户                 | JudgeServer/Judger master 保持 root；判题/编译子进程继续降权                 |
| capabilities         | 从 `cap_drop: ALL` 开始，只回加实测必需的 `CHOWN/SETUID/SETGID/KILL`       |
| Root FS              | `read_only: true`                                              |
| 临时工作区                | 显式 tmpfs/volume，仅 `/judger`、`/tmp`、日志目录可写                      |
| Docker socket        | 禁止                                                             |
| `privileged`         | 禁止                                                             |
| `SYS_ADMIN`          | 禁止                                                             |
| 健康检查                 | **本机 `/ping` liveness 与 backend heartbeat 完全拆开**               |

Debian 官方目前把 Debian 13.6 定义为 stable；13 的常规 Debian 支持到 2028-08-09，随后 LTS 到 2030-06-30。Debian 12 已在 2026 年转入 LTS，官方对于新安装明确建议使用 Debian 13。因此在 2026-08-20 建新的长期 Judge runtime，没有充分理由继续以 Debian 12 为主基线。 ([Debian 镜像][1])

**核心原则不是“一次把所有东西升级到最新”，而是：**

1. 先修复 build context、锁依赖、拆镜像层和健康检查；
2. 再切 Debian 13 / Python 3.13 / GCC 14；
3. Node 20 → 24 单独迁移并重新验证 `node` seccomp；
4. Go 1.22 → 1.26 单独迁移并重新验证 `golang` seccomp；
5. Java 第一轮维持 **21 major**；
6. Java 25 作为后续独立迁移；
7. arm64 必须作为独立 sandbox 安全目标验证，不能因为镜像能 `buildx` 成功就宣布支持。

---

# 2. 当前仓库事实

## 2.1 目录与 Docker build context

**[已核实事实]**

目标提交中确实存在：

```text
server/
├── judge-server/
│   ├── Dockerfile
│   └── server/
└── judger/
    ├── CMakeLists.txt
    ├── bindings/Python/
    └── src/
```

并不存在 `server/.dockerignore`。

当前 Dockerfile：

```dockerfile
WORKDIR /app
COPY Judger/ /app/
...
COPY server/ /app/
```

而实际 Judger 是兄弟目录 `server/judger/`。当前 Dockerfile 还同时尝试安装 Python 3.12、Go 1.22、Temurin 21、GCC 13、Node 20，并直接无版本约束安装 Flask/Gunicorn/idna/psutil/requests。

因此问题并不是简单把：

```dockerfile
COPY Judger/
```

改成：

```dockerfile
COPY ../judger/
```

Docker 本身禁止 `COPY` 越出 build context。

### 推荐 build 方式

**[架构建议]**

统一使用仓库根作为 context：

```text
docker build \
  -f server/Dockerfile \
  .
```

Dockerfile 内：

```text
COPY server/judger/ ...
COPY server/judge-server/ ...
```

Compose 同理：

```yaml
build:
  context: .
  dockerfile: server/Dockerfile
```

这是最清晰的长期方案。

---

## 2.2 Judger 的 root 要求不是历史包袱，可以直接移除

**[已核实事实]**

`runner.c` 首先执行：

```c
uid_t uid = getuid();
if (uid != 0) {
    ERROR_EXIT(ROOT_REQUIRED);
}
```

随后 fork 子进程。

子进程在设置资源限制、打开 stdin/stdout/stderr 后：

1. `setgid`
2. `setgroups`
3. `setuid`
4. 加载对应语言 seccomp
5. `execve`

也就是说其设计就是：

> **root supervisor → resource setup → drop UID/GID → seccomp → exec user code**

因此：

**不能为了符合普通 Web 容器的“非 root 最佳实践”，直接给整个 JudgeServer 配 `user: 1000`。**

正确做法是保留 root master，同时砍掉 root 不需要的 Linux capabilities。

---

## 2.3 当前固定 UID/GID

当前 Dockerfile创建：

* `compiler`: UID **901**
* `code`: UID **902**
* `spj`: UID **903**
* `spj` 加入 `code` group

JudgeServer 在运行时通过用户名取得 UID/GID；路径固定为：

* `/judger/run`
* `/judger/spj`
* `/test_case`
* `/log`

### 建议

**[架构建议]**

第一阶段继续固定：

```text
compiler = 901:901
code     = 902:902
spj      = 903:903
```

不要在框架迁移时顺手修改 UID。

如果以后确实需要可配置 UID/GID，也应在另一个提交中完成，并对历史 `/judger`、`/log` volume 做 ownership migration。

---

# 3. JudgeServer 协议兼容基线

仓库已经有一份协议契约，应将其直接转成迁移测试。

**[已核实事实]**

JudgeServer 与 Backend：

* 均使用 HTTP POST；
* Token 在请求头中传递的是配置 Token 的 **SHA-256 hex digest**；
* JudgeServer 包装是 `{"err": ..., "data": ...}`；
* Django API/heartbeat 包装是 `{"error": ..., "data": ...}`；
* 两者不可混淆。

### `/judge`

结果项必须继续保留：

```text
cpu_time
memory
real_time
result
signal
exit_code
error
output_md5
output
test_case
```

结果码不能重编号：

| result | 语义                       |
| -----: | ------------------------ |
|     -2 | Compile Error            |
|     -1 | Wrong Answer             |
|      0 | Accepted                 |
|      1 | CPU Time Limit Exceeded  |
|      2 | Real Time Limit Exceeded |
|      3 | Memory Limit Exceeded    |
|      4 | Runtime Error            |
|      5 | System Error             |

### `/compile_spj`

成功仍必须：

```json
{"err": null, "data": "success"}
```

### `/ping`

成功必须包含：

```json
{
  "err": null,
  "data": {
    "hostname": "...",
    "judger_version": "...",
    "cpu_core": 4,
    "cpu": 0.0,
    "memory": 0.0,
    "action": "pong"
  }
}
```

### heartbeat

继续：

```text
POST /api/judge_server_heartbeat/
```

请求至少保留：

```text
hostname
judger_version
cpu_core
memory
cpu
action = heartbeat
service_url
```

成功响应：

```json
{"error": null, "data": null}
```

现有 JudgeServer tests 实际只覆盖了 `/ping` 成功、错误 Token 和缺 Token，并没有覆盖完整判题协议。

---

# 4. 官方支持与版本矩阵

以下“访问日期”统一为 **2026-08-20**。

## 4.1 Debian 12 vs Debian 13

| 候选                      | 发布状态       | 支持状态                   | 支持结束                                   | 结论            | 官方来源                                                        |
| ----------------------- | ---------- | ---------------------- | -------------------------------------- | ------------- | ----------------------------------------------------------- |
| Debian 12 Bookworm      | oldstable  | **LTS**                | LTS 至 **2028-06-30**                   | 不作为新 Judge 基线 | [Debian Bookworm LTS](https://wiki.debian.org/LTS/Bookworm) |
| Debian 13 Trixie / 13.6 | **Stable** | Debian regular support | **2028-08-09**；之后 LTS 至 **2030-06-30** | **推荐**        |                                                             |

Debian 官方新安装指南明确推荐 current stable，即 Debian 13。([Debian Wiki][2])

### 为什么不是 Debian 12

不是因为 Debian 12 “不能用”，而是：

* 已经转入 LTS；
* 生命周期少约两年；
* 新工具链要额外维护；
* 之后仍然要做一次 12→13；
* 判断器又是安全敏感、需要长期维护的组件。

所以 **2026 新基础镜像选 13，维护既有生产实例时才考虑继续留 12。**

---

# 5. 推荐 server 目标版本矩阵

## 5.1 最终推荐

| 组件          | 2026-08-20 状态           | 推荐目标                        | 支持结束/周期                                   | 兼容要求                               | 选择    |
| ----------- | ----------------------- | --------------------------- | ----------------------------------------- | ---------------------------------- | ----- |
| Debian      | Stable                  | **13 / trixie**             | regular 2028-08-09；LTS 2030-06-30         | amd64/arm64                        | ✅     |
| Python      | bugfix                  | **3.13.x / Debian package** | 2029-10                                   | Flask/Gunicorn + `_judger` wrapper | ✅     |
| Python 3.14 | bugfix                  | 3.14.x                      | 2030-10                                   | 需独立 Python/runtime/seccomp 回归      | 暂不    |
| GCC/G++     | Debian stable toolchain | **14.2.x Debian package**   | 跟随 Debian 安全维护；**无 GCC LTS 概念**           | C17/C++20                          | ✅     |
| Go          | Stable                  | **1.26.x**                  | 直到两个后续 major 发布；**无 Go LTS 概念**           | `golang` seccomp                   | ✅     |
| Go 1.27     | **RC / 未 GA**           | 不使用                         | —                                         | release notes 仍为 DRAFT             | ❌     |
| Java 21     | LTS release line        | **OpenJDK 21**              | Oracle Premier 2028-09 / Extended 2031-09 | 现有 Java21 兼容                       | ✅     |
| Java 25     | LTS release line        | 后续候选                        | Oracle Premier 2030-09 / Extended 2033-09 | syscall/JIT/资源重新标定                 | Later |
| Node 20     | EOL                     | 20                          | **已 EOL**                                 | 不再作为新 runtime                      | ❌     |
| Node 24     | **LTS / Krypton**       | **24.x**                    | 2028-04                                   | `node` seccomp 重新验证                | ✅     |
| Node 26     | Current                 | 26.x                        | 截点尚非 LTS                                  | Node 官方建议生产使用 LTS                  | ❌     |
| libseccomp  | Debian stable           | **2.6.x**                   | Debian 生命周期                               | amd64/arm64 native                 | ✅     |

Python 官方显示 3.13 与 3.14 当前均处于 bugfix 支持，分别到 2029-10 和 2030-10。([Python Developer's Guide][3])

Python 3.14 已是 stable，不是 beta；3.14.0 于 2025-10-07 正式发布。([Python.org][4])

但 Debian 13 原生 Python 是 3.13 系列，因此本项目选择 3.13 是“减少外部工具链和 ABI 组合”，不是因为 3.14 不稳定。Debian 13 官方发布资料同时列出了 Python 3.13 和 GCC 14.2。([Debian Project][5])

---

## 5.2 Go：必须修正一个容易误判的时间点

截至本报告截点，Go 官方 **Go 1.27 release notes 明确写着：**

> Go 1.27 is not yet released.

仍是 DRAFT，并预计 2026 年 8 月发布。([Go 语言][6])

当前可核实 stable 分支为 **1.26**，官方 release history 可确认：

* 1.26.0：2026-02-10
* 1.26.5：2026-07-07

Go 官方规则是：

> 一个 major release 支持到两个更新的 major release 出现。

它没有 “LTS” 品牌或 LTS 分支。([Go 语言][7])

因此：

**推荐 Go 1.26.x，构建时固定实际补丁版本和 image digest；不要把 Go 1.26 称为 LTS。**

---

# 6. Node.js 选择

截至截点：

* Node 20：**EOL**
* Node 22：LTS
* Node 24 `Krypton`：**LTS**
* Node 26：**Current**

Node 官方明确表示生产应用应使用 Active/Maintenance LTS，而不是 Current。([Node.js][8])

Node 24 于 2025-10-28 正式进入 LTS，并将持续更新到 **2028-04**。([Node.js][9])

因此：

> **Node 24 是明确推荐。Node 26 即使数字更大，也不应在本次生产迁移中采用。**

---

# 7. Java 21 与 Java 25

Oracle 2026-04 的生命周期表：

| Java | GA      | Premier | Extended |
| ---- | ------- | ------- | -------- |
| 21   | 2023-09 | 2028-09 | 2031-09  |
| 25   | 2025-09 | 2030-09 | 2033-09  |

([甲骨文][10])

两者都是 Java LTS release line。

### 推荐 Java 21，而不是马上上 25

**[架构建议]**

原因不是 Java 25 不成熟，而是：

1. 仓库当前明确对外描述的是 **Temurin 21**；
2. Java 当前是唯一 `seccomp_rule=None` 的主要语言；
3. JVM 本身线程/JIT/内存行为比普通 native binary 复杂；
4. 同时把 OS、JDK major、vendor 和资源策略全部改变，会大幅增加回归定位成本。

所以第一轮：

```text
Temurin 21 → Debian OpenJDK 21
```

先只改变 vendor/package source，不改变 Java major。

待 server 基础镜像稳定后，再以独立 migration：

```text
OpenJDK 21 → OpenJDK 25
```

进行完整 Java corpus + memory/time/syscall 重标定。

---

# 8. Debian 包还是外部仓库/上游 stage

## 推荐策略

| 工具链                     | 获取方式                | 理由                             |
| ----------------------- | ------------------- | ------------------------------ |
| Python 3.13             | Debian apt          | Trixie 原生主版本                   |
| GCC/G++ 14              | Debian apt          | Trixie 默认编译器                   |
| libseccomp              | Debian apt          | 必须与 OS/kernel 用户态紧密配合          |
| OpenJDK 21              | Debian apt          | 避免再混 Adoptium repo             |
| Node 24                 | **Node 官方固定 stage** | Trixie 的 Node20 已 upstream EOL |
| Go 1.26                 | **Go 官方固定 stage**   | Trixie 自带 Go 版本落后于当前支持线        |
| JudgeServer Python deps | uv lock + PyPI      | 项目级依赖                          |

### 不推荐当前模式

当前 Dockerfile：

* base 是 Trixie；
* 却添加 Adoptium **bookworm** repository；
* 再添加 NodeSource 20；
* apt 安装一组指定旧 major。

这会造成：

```text
Debian stable
 + Debian old-release-targeted third-party repo
 + NodeSource
 + Debian apt
```

四套生命周期混在一个 runtime。

### 推荐的 Node/Go stage 思路

使用官方镜像作为 **artifact provider**：

```text
node:24.x@sha256:...
golang:1.26.x@sha256:...
```

只把运行/编译所需固定工具链复制到 `judge-runtime-base`。

这比运行时调用 NodeSource/自建 curl 安装器可复现得多。

---

# 9. Flask / Gunicorn / Python 依赖

## 9.1 推荐组合

截至截点可采用的稳定版本族：

| 包        | 推荐                | 状态     | Python |
| -------- | ----------------- | ------ | ------ |
| Flask    | **3.1.3**         | Stable | ≥3.9   |
| Gunicorn | **26.1.0**        | Stable | ≥3.10  |
| requests | **2.34.2**        | Stable | ≥3.10  |
| psutil   | **7.2.2**         | Stable | ≥3.6   |
| idna     | **3.19 resolved** | Stable | ≥3.9   |

访问日：2026-08-20。

这些包均没有类似 Django LTS 那样的长期版本线，应称为当前 Stable release，而不是 LTS。

### 生产上的额外保守措施

Gunicorn 26.1.0 和 idna 3.19 在截点附近非常新，因此**不应因为是最新版就直接替换生产环境**。

建议：

1. 在迁移分支上由 `uv lock` 得到完整依赖集合；
2. 运行 HTTP/API/protocol corpus；
3. 固定 `uv.lock`；
4. 只有测试通过的 lock 才进入 server image；
5. 后续升级包必须显式更新 lock，而不是每次 Docker build 自动追最新。

---

# 10. JudgeServer 应使用独立 `pyproject.toml + uv.lock`

## 结论：应当使用

**[架构建议]**

JudgeServer 是独立 deployable application，应拥有自己的：

```text
server/judge-server/
├── pyproject.toml
└── uv.lock
```

而不是和 backend 共用 lock。

原因：

* backend 与 JudgeServer 生命周期完全不同；
* JudgeServer 还绑定 native Judger；
* JudgeServer 对 Python ABI/syscall 更敏感；
* Flask/Gunicorn 更新不应触发 backend lock；
* server image 可独立构建和回滚。

uv 官方设计就是：

* `pyproject.toml` 描述直接依赖；
* `uv.lock` 保存精确解析；
* lock 建议入库；
* Docker 构建可先只同步依赖，再复制业务源码，从而最大化缓存。([Astral Docs][11])

[uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/)

---

# 11. `judge-runtime-base` 与 app image 分层

## 11.1 推荐结构

```text
debian:13-slim
      │
      ▼
judge-runtime-base
      ├── Python 3.13
      ├── GCC/G++ 14
      ├── OpenJDK 21
      ├── Node 24
      ├── Go 1.26
      ├── libseccomp
      ├── locale / ca-certificates
      └── fixed users/groups 901/902/903
      │
      ▼
judger-builder
      ├── cmake
      ├── libseccomp-dev
      ├── Python build backend
      └── build native judger + Python wheel
      │
      ▼
xju-oj-server
      ├── judge-runtime-base
      ├── /usr/lib/judger/libjudger.so
      ├── _judger wheel
      ├── JudgeServer venv from uv.lock
      └── JudgeServer source
```

### 11.2 为什么要独立 runtime-base

工具链中：

* GCC
* JDK
* Go
* Node

占据绝大多数下载/镜像体积，但业务层 `server.py/judge_client.py/compiler.py` 修改频率更高。

如果所有东西都写在一个普通 Dockerfile layer 链里：

```text
业务文件变化
→ cache invalidation
→ apt/toolchain reinstall
```

非常浪费。

推荐发布内部 image：

```text
xju-oj/judge-runtime-base:2026.08-r1
```

其输入仅包含：

```text
Debian version
toolchain versions
UID/GID
system packages
```

只有工具链或系统安全更新才 rebuild。

业务代码变更只重新构建：

```text
xju-oj/server:<git-sha>
```

---

# 12. BuildKit 缓存设计

至少独立：

```text
apt cache
uv cache
CMake object/cache
```

缓存键必须包含：

```text
TARGETARCH
toolchain version
lock hash
```

例如概念上：

```text
apt-${TARGETARCH}
uv-${TARGETARCH}
cmake-judger-${TARGETARCH}
```

对于 CI，推荐 `cache-to/cache-from` registry cache，而不只依赖单机 Docker cache。

### `.dockerignore`

应在 build context 根适用的位置排除至少：

```text
.git
.git/**
frontend/node_modules
**/__pycache__
**/*.pyc
**/.venv
**/dist
**/build
server/judger/.git
server/judge-server/.git
logs
data
test runtime outputs
```

但**不能错误排除 Judger tests 和 protocol fixtures**，因为 CI sandbox image 可能需要它们。

---

# 13. Python binding wheel

一个重要事实是：

**当前 `_judger` 并不是直接链接 C extension。**

Python wrapper 实际使用：

```python
proc_args = ["/usr/lib/judger/libjudger.so"]
subprocess.Popen(...)
```

来执行 native Judger，并读取 JSON。

其 `pyproject.toml` 当前仅声明 setuptools build backend。

因此推荐：

### builder

```text
CMake → native /usr/lib/judger/libjudger.so
setuptools/build → _judger wheel
```

### final

分别复制：

```text
native judger → /usr/lib/judger/libjudger.so
wheel → JudgeServer venv
```

这样边界清晰。

**[仍需实测]** 应确认 wheel 最终是否为 `py3-none-any`。即使 wheel 本身是 pure Python：

> `libjudger.so` 依然必须在 amd64/arm64 上分别原生编译。

不能把 amd64 native Judger 和 architecture-independent Python wheel 的概念混淆。

---

# 14. Seccomp 现状与升级风险

## 14.1 C/C++：严格 allowlist

当前 C/C++：

```c
seccomp_init(SCMP_ACT_KILL)
```

也就是默认 kill，再逐个开放 syscall。

当前已有例如：

```text
arch_prctl
brk
clock_gettime
futex
getrandom
mmap
mprotect
munmap
newfstatat
prlimit64
rseq
...
```

这是正确的高安全方向，但也是升级 glibc/GCC 后最容易出现：

```text
正常程序 → 新 libc 调新 syscall → SIGSYS/RE
```

的部分。

---

## 14.2 Python `general`：default allow + blacklist

当前：

```c
seccomp_init(SCMP_ACT_ALLOW)
```

并明确禁：

```text
clone
fork
vfork
kill
execveat
socket
write-open
write-openat
```

以及限制 `execve`。

问题在于现代 Linux syscall 集已经大于这些旧规则覆盖范围。

例如必须专门验证：

```text
clone3
openat2
socketpair
pidfd_*
io_uring_*
memfd_create
process_vm_*
bpf
perf_event_open
userfaultfd
```

是否构成新逃逸路径。

---

## 14.3 Go

Go rule 同样是 default allow blacklist，并阻止 `socket/fork/vfork/kill/execveat` 和可写 open。

但它**没有禁止 clone**，因为 Go runtime 本来需要创建线程。

因此不能简单：

```text
“发现 Go 使用 clone/clone3”
→ 加 blacklist
```

否则 Go 本身就无法工作。

应采用参数级规则或以攻击结果为目标测试，而不是按 syscall 名称粗暴禁用。

---

## 14.4 Node

Node 的规则甚至更宽：

```text
default allow
deny socket
deny fork/vfork
deny kill
deny execveat
```

而 Node/V8/libuv 正常运行本身依赖线程、epoll/futex/eventfd 等。

Node 20→24 后，**必须重新建立 Node syscall baseline。**

---

# 15. glibc / runtime 新 syscall 风险

升级 Debian 13、glibc、Python、Node、Go、JDK 后应重点观察：

```text
clone3
rseq
getrandom
faccessat2
openat2
close_range
statx
membarrier
madvise
sched_getaffinity
prlimit64
pidfd_open
```

特别重要的是 `clone3`。

Docker 官方曾明确调整默认 seccomp，让 `clone3` 返回 **ENOSYS** 而不是一般权限错误，目的就是让 glibc 能正确 fallback 到旧 `clone`。([Docker Documentation][12])

这说明：

> seccomp 不只是“允许/不允许”。

对部分 runtime：

```text
KILL
EPERM
ENOSYS
```

三种 action 可能导致完全不同的行为。

因此本项目不能通过“遇到 SIGSYS 就把 syscall 加 allowlist”完成迁移。

---

# 16. Seccomp 兼容测试方法

## 正向 corpus

每个 runtime 建立 syscall trace：

```text
strace -ff
```

覆盖：

* hello world
* stdin/stdout
* 大量内存
* sleep
* thread
* random
* Unicode
* file IO 模式
* subprocess 尝试
* network 尝试

得到：

```text
runtime
architecture
toolchain version
kernel
syscall
arguments
expected allow/deny
```

然后才决定 seccomp 修改。

---

## 负向 corpus

任何 seccomp 修改都必须证明以下攻击仍然失败：

### Process

```text
fork bomb
exec /bin/sh
execveat
clone process
clone3 process
```

### File

```text
写 /etc
写 /usr
写 /test_case
覆盖其他 submission workspace
读取无权限 submission
```

### Network

```text
TCP connect backend
TCP connect Redis
TCP connect Internet
UDP
raw socket
Unix socket abuse
```

### Kernel surfaces

```text
mount
ptrace
bpf
perf_event_open
keyctl
userfaultfd
io_uring
setns/unshare
```

**验收标准不是“程序能跑”，而是：**

> 正常 corpus 全部通过 + 攻击 corpus 仍全部被拒绝。

---

# 17. x86_64 与 arm64

## 17.1 Debian/toolchain

Debian 13 正式支持：

* amd64
* arm64

等架构。([Debian 镜像][13])

Node 官方、Go、OpenJDK、Python 和 libseccomp 也都有 arm64 路径。

但这**不等于 Judger 已经 arm64-ready**。

---

## 17.2 当前规则包含架构假设

例如 C/C++ whitelist 中有：

```text
arch_prctl
```

这是典型的 architecture-sensitive syscall。

不同架构：

```text
amd64 glibc
arm64 glibc
```

初始化 runtime 所需的 syscall 并不保证相同。

### 结论

arm64 发布条件必须是：

```text
native arm64 host
+ arm64 Debian
+ arm64 libseccomp
+ native arm64 Judger
+ 全语言测试 corpus
+ 全安全负向 corpus
```

**QEMU buildx 成功只能证明“能构建”，不能证明 sandbox 安全兼容。**

建议第一阶段 production 标：

```text
linux/amd64: supported
linux/arm64: experimental until security suite passes
```

---

# 18. 编译阶段没有 language Seccomp

当前 `Compiler.compile()` 实际仍然通过 `_judger.run()` 执行编译器，因此 CPU、real time、memory、output、UID/GID 等 Judger 资源隔离仍在。

但是它明确：

```python
seccomp_rule_name=None
```

所以：

> **“编译阶段没有 Seccomp”准确地说是：使用 Judger resource/UID sandbox，但没有 syscall sandbox。**

---

## 18.1 在不使用 privileged/SYS_ADMIN 的条件下怎么补

第一层先做容器边界：

* `read_only: true`
* `/test_case:ro`
* compiler UID 901
* rootfs 不可写
* workspace 单独 tmpfs
* CPU/memory/pids cgroup limit
* Judger rlimit
* `no-new-privileges`
* cap drop
* Docker 默认/custom seccomp
* 不挂 Docker socket
* 不挂 host sensitive paths
* Compose internal network

Docker 官方默认 seccomp 已经阻止包括 namespace、kernel management 等大量敏感 syscall，并明确建议不要禁用默认 seccomp。([Docker Documentation][14])

但必须明确：

**这仍不等于“compiler 无网络”。**

因为 JudgeServer 自己必须：

```text
listen HTTP
+
connect backend heartbeat
```

所以不能在整个 container 上禁止 `socket/connect`。

### 长期正确方向

**[架构建议]**

给 compiler 增加独立的 seccomp profile：

```text
gcc_compile
gpp_compile
javac_compile
python_compile
go_compile
node_check
```

但这是下一阶段安全增强，不要和 Debian/toolchain migration 混在同一个提交。

---

# 19. capability 设计

Linux capabilities 官方语义中：

* `CAP_CHOWN`：改变文件 UID/GID
* `CAP_KILL`：跨 UID signal
* `CAP_SETGID`：切换 GID / supplementary groups
* `CAP_SETUID`：切换 UID

([man7.org][15])

而这恰好对应当前 Judger：

```text
chown/workspace ownership
setgid
setgroups
setuid
kill timeout child
```

### 推荐起点

```yaml
cap_drop:
  - ALL
cap_add:
  - CHOWN
  - SETUID
  - SETGID
  - KILL
```

### 明确不加

```text
SYS_ADMIN
SYS_PTRACE
NET_ADMIN
NET_RAW
SYS_MODULE
DAC_READ_SEARCH
BPF
PERFMON
```

`DAC_OVERRIDE/FOWNER` 也不要预先添加。

若 regression suite 证明缺少某项 capability，再逐项调查。

---

# 20. `read_only` / tmpfs / pids

Docker Compose 原生支持：

* `cap_drop`
* `read_only`
* `security_opt`
* `tmpfs`
* `pids_limit`

并支持 `no-new-privileges`。([Docker Documentation][16])

## 推荐初始结构

```text
root filesystem      ro
/test_case           ro bind/volume
/tmp                 tmpfs
/judger/run          tmpfs
/judger/spj          volume 或 tmpfs（需验证缓存语义）
/log                 writable volume
```

### `pids_limit`

不建议拍脑袋设置成 32/64，因为：

* JVM 有多个 runtime thread；
* Node/V8/libuv 有线程池；
* Gunicorn/JudgeServer 也有进程。

建议初始：

```text
pids_limit = 512
```

但它属于**性能/并发配置项，不是固定协议值**。

最终应按照：

```text
最大并发 submission 数
× 最大合法 runtime thread 数
+ JudgeServer/Gunicorn overhead
```

实测。

---

# 21. `/test_case` 权限

现有 example compose 已明确：

```yaml
$PWD/tests/test_case:/test_case:ro
```

这条应该升级成**不可破坏的部署契约**：

> JudgeServer/Judger 无权修改 testcase source。

验收脚本必须主动尝试：

```text
create
truncate
rename
unlink
chmod
```

`/test_case/*`

并要求全部失败。

如果某个新 runtime 需要：

```text
/test_case:rw
```

才能正常工作：

# **STOP**

不得上线。

---

# 22. JudgeServer 不应公开 8080

当前 example compose：

```yaml
ports:
  - "0.0.0.0:12358:8080"
```

这不适合新的统一 production compose。

### 推荐

正常 production：

```text
frontend/reverse proxy
backend
server
redis/db
```

server 只存在于内部 Compose network：

```text
backend → http://server:${SERVER_PORT}
```

不需要 host `ports:`。

可以使用：

```yaml
expose:
  - "${SERVER_PORT}"
```

甚至 `expose` 只是文档化，Compose 网络中的服务本来就可互访。

### Debug profile

若确实需要本机调试：

```text
127.0.0.1:${JUDGE_DEBUG_PORT}:${SERVER_PORT}
```

而不是：

```text
0.0.0.0
```

如果 production 必须公开 JudgeServer 8080 才能运行：

# **STOP**

---

# 23. 健康检查必须拆开

这是当前 Dockerfile 的明确问题。

Dockerfile 使用：

```dockerfile
HEALTHCHECK ... python3 /app/service.py
```

而 `service.py` 实际发：

```text
POST BACKEND_URL
timeout=5
```

backend 不可达就 exit 1。

因此：

```text
Backend temporary outage
→ heartbeat failed
→ Docker healthcheck failed
→ JudgeServer marked unhealthy
```

这把 dependency health 错误地等同于 process health。

---

## 推荐双状态

### Liveness

只测：

```text
Gunicorn process
→ localhost JudgeServer
→ POST /ping
→ action=pong
```

必须完全不依赖 backend。

状态：

```text
server_liveness = healthy / unhealthy
```

### Backend heartbeat

另记录：

```text
heartbeat_last_success
heartbeat_fail_count
backend_connectivity
```

状态：

```text
backend_heartbeat = connected / degraded
```

backend 暂时断开时：

```text
container = healthy
heartbeat = degraded
```

而不是 restart JudgeServer。

---

# 24. `/ping`、`/judge`、`/compile_spj`、heartbeat 回归矩阵

| 接口             | Case                   | 期望                              |
| -------------- | ---------------------- | ------------------------------- |
| `/ping`        | 正确 token               | `err=null`, `action=pong`       |
| `/ping`        | 错 token                | `TokenVerificationFailed`       |
| `/ping`        | 无 token                | `TokenVerificationFailed`       |
| `/ping`        | backend down           | **仍然成功**                        |
| `/judge`       | 正确 C AC                | result=0                        |
| `/judge`       | C CE                   | compile result/error 保持         |
| `/judge`       | WA                     | result=-1                       |
| `/judge`       | CPU TLE                | result=1                        |
| `/judge`       | real TLE               | result=2                        |
| `/judge`       | MLE                    | result=3                        |
| `/judge`       | RE                     | result=4                        |
| `/judge`       | sandbox/system failure | result=5                        |
| `/judge`       | bad token              | 原错误包装                           |
| `/judge`       | test_case_id           | 只读 mounted testcase 正常          |
| `/judge`       | dynamic test_case      | 行为与旧版一致                         |
| `/judge`       | Standard IO            | 一致                              |
| `/judge`       | File IO                | 一致                              |
| `/judge`       | SPJ                    | 一致                              |
| `/compile_spj` | valid                  | `{"err":null,"data":"success"}` |
| `/compile_spj` | invalid code           | `SPJCompileError`               |
| heartbeat      | 正常 backend             | `{"error":null,"data":null}`    |
| heartbeat      | bad token              | `Invalid token` 语义不变            |
| heartbeat      | backend down           | JudgeServer liveness 不受影响       |
| heartbeat      | restore backend        | 自动恢复 heartbeat，无需重启             |

协议字段基线来自当前 repository contract。

---

# 25. 每种语言验收矩阵

所有语言至少执行以下维度：

| 维度                    |  C | C++ | Java | Python | Go | Node |
| --------------------- | -: | --: | ---: | -----: | -: | ---: |
| compile/check success |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| compile syntax error  |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| normal run            |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| stdin/stdout          |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| Unicode               |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| CPU TLE               |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| real-time TLE         |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| memory limit          |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| output limit          |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| runtime error         |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| child process escape  |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| write rootfs          |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| write `/test_case`    |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| read other workspace  |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| outbound TCP          |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| UDP/socket            |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| exec shell/binary     |  ✓ |   ✓ |    ✓ |      ✓ |  ✓ |    ✓ |
| SPJ where applicable  |  ✓ |   ✓ |    — |      — |  — |    — |

对“攻击测试”而言，表中 ✓ 的含义是：

> **攻击被正确阻止。**

---

# 26. 当前语言配置迁移影响

当前 backend language definitions 是：

* C：GCC 13 / C17
* C++：GCC 13 / C++20
* Java：Temurin 21
* Python：3.12
* Go：1.22
* Node：20

推荐迁移到：

```text
C        GCC 14 / C17
C++      GCC 14 / C++20
Java     OpenJDK 21
Python   CPython 3.13
Go       Go 1.26
JS       Node 24 LTS
```

注意：

> language description 也属于用户可见行为。

不要镜像升级完成后仍显示：

```text
GCC 13
Python 3.12
Go 1.22
Node 20
```

但更新这些 description 应和对应 runtime upgrade 在同一阶段完成。

---

# 27. 分阶段迁移路径

## Phase S0 — 冻结安全与协议基线

不升级任何 runtime。

新增/固化：

* `/ping`
* `/judge`
* `/compile_spj`
* heartbeat
* result code
* token digest
* UID/GID
* `/test_case:ro`
* syscall negative corpus
* language corpus

**完成后才允许后续工作。**

---

## Phase S1 — 修复构建系统，不改变语言版本

目标：

```text
正确 root build context
server/.dockerignore
pyproject + uv.lock
BuildKit cache
runtime-base / app layer
```

这一阶段原则上不改变 C/Python/Go/Node/Java 判题行为。

这是最容易回滚的一层。

---

## Phase S2 — Debian 13 原生 runtime

迁移：

```text
Debian 13
Python 3.13
GCC 14
libseccomp 2.6
```

Java 暂时保持 major 21。

必须全量重跑：

```text
C/C++ strict whitelist
Python general blacklist
protocol tests
resource accounting
```

---

## Phase S3 — Node 20 → Node 24 LTS

单独提交/发布。

重点：

```text
V8/libuv threads
clone/clone3
epoll/eventfd
mmap/mprotect
network block
filesystem block
memory accounting
```

通过后才升级语言描述。

---

## Phase S4 — Go 1.22 → Go 1.26

单独提交/发布。

重点：

```text
runtime threads
clone semantics
futex
epoll
signals
network
filesystem
CGO behavior
memory_limit_check_only
```

不要同时跟 Node 升级。

---

## Phase S5 — 容器 hardening

在已验证 runtime 基础上逐步启用：

```text
cap_drop ALL
minimal cap_add
read_only
tmpfs
no-new-privileges
pids_limit
internal networking
remove public port
```

每加一项运行一次完整判题 corpus。

---

## Phase S6 — arm64

单独 pipeline：

```text
linux/arm64
```

全套原生测试。

不得和 amd64 共用一份未经验证的 syscall 假设。

---

## Phase S7 — Java 25（可选）

只有 Java21 方案长期稳定之后，再评估。

不属于第一轮 server modernization 的 blocker。

---

# 28. 破坏性变更与高风险项

## P0：Seccomp 误杀

Debian/glibc/runtime 升级后：

```text
valid submission
→ new syscall
→ SIGSYS
→ Runtime Error
```

这是最大风险。

---

## P0：Seccomp 逃逸

更危险的是为了消除 SIGSYS 直接：

```text
SCMP_ACT_ALLOW everything
```

或者删除规则。

这是不可接受的。

---

## P0：Java 当前没有 language seccomp

现有配置 Java：

```python
"seccomp_rule": None
```

必须明确记录为现状风险，不能在升级报告中把 Java 误描述成已经获得和 C/C++ 同等 syscall sandbox。

---

## P0：compiler 没有 seccomp

虽然 compiler UID/resource 已下降，但 syscall 面仍大。

不能因为外层 Docker 默认 seccomp 存在就宣称 compiler 与 runtime sandbox 等价。

---

## P1：健康检查依赖 backend

当前设计会造成错误重启/错误 unhealthy。

应优先修。

---

## P1：Node 20 EOL

Debian Trixie 自身提供 Node20 并不改变 Node upstream 已 EOL 的事实。

这正是“不能只看 Debian 包是否存在”的典型案例。Node 官方明确标记 v20 EOL。([Node.js][8])

---

# 29. 测试和验收标准

上线新 server image 前必须全部满足：

### Build

```text
amd64 clean build succeeds
build is reproducible from lock/digests
second build hits dependency/toolchain caches
business-only change does not rebuild heavy toolchain
```

### Runtime

```text
all expected compilers/interpreters print target versions
Judger version unchanged unless explicitly migrating
UID/GID are correct
```

### Protocol

```text
100% protocol regression pass
result fields unchanged
token hash behavior unchanged
heartbeat payload unchanged
```

### Sandbox

```text
all positive language corpus pass
all negative escape corpus blocked
/test_case stays ro
no privileged
no SYS_ADMIN
no Docker socket
```

### Container

```text
rootfs read-only
only documented writable mounts/tmpfs
minimal capability set
no public JudgeServer port
pids limit under load does not kill legitimate Node/JVM workload
```

### Availability

```text
backend offline:
  /ping = healthy
  container = healthy
  heartbeat = degraded

backend restored:
  heartbeat resumes
  no JudgeServer restart required
```

---

# 30. 停止条件

出现以下任一情况必须 **STOP，不得上线**：

1. 新 server 必须使用 `privileged: true` 才能判题；
2. 必须添加 `SYS_ADMIN`；
3. 必须挂 `/var/run/docker.sock`；
4. 必须把 `/test_case` 从 `ro` 改为 `rw`；
5. 必须公开 JudgeServer `8080`/内部 Judge API 到 `0.0.0.0` 才能工作；
6. 为适配某 runtime 必须取消 Judger UID/GID 降权；
7. 必须取消 C/C++ seccomp 才能运行；
8. Node/Go 的“修复”是把 sandbox 变成无条件 syscall allow；
9. arm64 仅在 QEMU/buildx 测试过、没有 native security tests；
10. backend 暂时不可达会触发 server container restart；
11. 新 runtime 的资源结果明显偏移，却没有重新标定；
12. `/judge` 返回字段或 result code 与现有协议不同；
13. Token 从 SHA-256 digest 退化成传明文；
14. 无法证明 testcase、其他 submission workspace、容器 rootfs 不可写。

---

# 31. 回滚原则

server 必须支持**镜像级原子回滚**。

推荐 tag：

```text
xju-oj/server:<git-sha>
xju-oj/judge-runtime-base:<toolchain-manifest-id>
```

而不是生产依赖：

```text
latest
```

### 每一个阶段都必须满足

```text
旧 server image
      ↓
docker compose config change
      ↓
重新 up
      ↓
无需 schema migration
      ↓
恢复判题
```

server migration 不应需要数据库 migration，因此理论上是整个 OJ 中最适合 blue/green 或 image rollback 的部分。

禁止一个提交同时做：

```text
Debian
+ Python
+ GCC
+ Go
+ Node
+ Java
+ seccomp rewrite
+ capability hardening
```

否则任何判题差异都无法快速定位。

---

# 32. 待本仓库实测的问题

## 必须回答后才能宣布 server modernization 完成

### Sandbox

1. Debian13/GCC14 下 C/C++真实 syscall 集是否仍匹配 whitelist？
2. glibc 是否尝试 `clone3`？
3. arm64 C/C++ 初始化 syscall 与 amd64 差多少？
4. Python3.13 是否可以绕过当前 general blacklist 使用 `clone3`？
5. `openat2` 是否形成新的写文件路径？
6. Node24 是否通过 `clone3` 创建线程？
7. Node24 是否可利用允许的 syscall 建立非 `socket()` 路径的 IPC/network？
8. Go1.26 runtime 是否引入新进程/syscall 行为？
9. `io_uring` 是否必须主动阻止？

### Resource accounting

10. JVM `-XX:MaxRAM` 与 Judger `ru_maxrss` 在 OpenJDK21 下是否仍保持历史语义？
11. Go/Node `memory_limit_check_only=1` 是否仍准确？
12. Python3.13 RSS 是否会让旧题目出现系统性 MLE？

### Container

13. `cap_drop: ALL + CHOWN/SETUID/SETGID/KILL` 是否足够？
14. 是否确实不需要 `DAC_OVERRIDE`？
15. `no-new-privileges` 是否影响 libseccomp filter load？
16. `/judger/spj` 是否必须跨容器重启持久化？
17. `/log` 是否以后可以逐步转 stdout/stderr？

### Multiarch

18. `_judger` wheel 是否最终生成 pure Python wheel？
19. native `libjudger.so` 在 arm64 是否完整通过现有 integration suite？
20. Node24/Go1.26/OpenJDK21 的官方 stage 在两个架构是否得到一致版本？

---

# 33. 推荐最终形态

```text
repo root
│
├── deploy.sh
├── compose.yaml
│
└── server/
    ├── Dockerfile
    ├── .dockerignore
    │
    ├── judge-server/
    │   ├── pyproject.toml
    │   ├── uv.lock
    │   ├── server/
    │   └── tests/
    │
    └── judger/
        ├── CMakeLists.txt
        ├── bindings/Python/
        ├── src/
        └── tests/
```

构建依赖关系：

```text
toolchain manifest
       │
       ▼
judge-runtime-base
       │
       ├────────────┐
       ▼            ▼
judger builder   app dependency layer
       │            │
       └──────┬─────┘
              ▼
       final server image
```

最终生产运行关系：

```text
                        internal compose network
               ┌───────────────────────────────┐
               │                               │
backend ───────┼──── HTTP ──────► server       │
               │                  :8080        │
               │                    │          │
               │              root supervisor │
               │                    │          │
               │        ┌───────────┼────────┐ │
               │        ▼           ▼        ▼ │
               │ compiler:901   code:902  spj:903
               │        │           │        │ │
               │        └──── Judger/Seccomp ┘ │
               └───────────────────────────────┘

Host/Public Internet
        │
        └── X  no direct JudgeServer mapping
```

---

# 34. 推荐目标结论

## 建议正式冻结为下面的 server 2026 baseline

```text
OS:
  Debian 13 stable

JudgeServer:
  CPython 3.13
  Flask 3.1.x
  Gunicorn 26.x
  requests 2.34.x
  psutil 7.2.x
  uv + pyproject.toml + uv.lock

Judger:
  native C/CMake
  Debian libseccomp 2.6.x

Languages:
  C       GCC 14 / C17
  C++     GCC 14 / C++20
  Java    OpenJDK 21
  Python  CPython 3.13
  Go      Go 1.26.x
  JS      Node 24.x LTS

Container:
  root master
  compiler=901
  code=902
  spj=903

  cap_drop: ALL
  candidate cap_add:
    CHOWN
    SETUID
    SETGID
    KILL

  read_only: true
  no-new-privileges: true
  /test_case: ro
  /tmp: tmpfs
  /judger/run: tmpfs
  /judger/spj: explicit writable storage
  pids_limit: initial 512, load-test before freeze

Networking:
  JudgeServer internal only
  no 0.0.0.0 host publish

Health:
  Docker health = localhost /ping
  Backend heartbeat = separate dependency status
```

其中：

* **Debian 13 优于 Debian 12**；
* **Python 3.13 优于本次直接使用 3.14**，主要因为 Debian 原生集成；
* **GCC 14 推荐，但不得称为 LTS**；
* **Go 1.26 推荐，但不得称为 LTS**；
* **Go 1.27 截点尚未正式发布，不能进入生产矩阵**；
* **Node 24 LTS 推荐，Node20 已 EOL，Node26 尚为 Current**；
* **Java 21 第一轮优于直接跳 Java25**；
* Node/Go 最适合从**官方固定 Docker stage**导入；
* Python/GCC/OpenJDK/libseccomp 最适合使用 **Debian 13 原生包**；
* 不建议继续保持当前 Trixie + Adoptium Bookworm repo + NodeSource + Debian 混合安装模型。

---

# 35. 官方来源清单

所有来源访问日期：**2026-08-20**。

### Debian

*
*
*
*
*
*
*

### Python

*
*

### Node.js

*
*
*

### Go

*
*

### Java

*

### Docker / container isolation

*
*
*

### Python dependency/build tooling

* [uv Docker integration and caching guidance](https://docs.astral.sh/uv/guides/integration/docker/)

---

## 最终判定

**该 server 模块适合直接以 Debian 13 为新的 2026 长期基线，但不适合“一次性升级所有语言 runtime”。**

最稳妥的生产迁移主线是：

```text
协议与安全 corpus 固化
        ↓
Docker context / uv / 分层镜像
        ↓
Debian13 + Python3.13 + GCC14 + libseccomp
        ↓
Node24 单独迁移
        ↓
Go1.26 单独迁移
        ↓
容器 capability/read-only hardening
        ↓
arm64 原生安全验收
        ↓
可选 Java21 → Java25
```

其中 **Seccomp regression 是整个 server modernization 的发布闸门**。任何方案如果只能通过 `privileged`、`SYS_ADMIN`、Docker socket、公开 JudgeServer 8080、把 `/test_case` 改为可写、或取消既有 UID/GID/Seccomp 安全边界才能工作，都应直接停止迁移，不进入生产。

[1]: https://mirror-anu4.debian.org/releases/trixie/ "https://mirror-anu4.debian.org/releases/trixie/"
[2]: https://wiki.debian.org/LTS/Installing "https://wiki.debian.org/LTS/Installing"
[3]: https://devguide.python.org/versions/?source=post_page-----4134150b6b0d-------------------------------- "https://devguide.python.org/versions/?source=post_page-----4134150b6b0d--------------------------------"
[4]: https://www.python.org/downloads/release/python-3140/ "https://www.python.org/downloads/release/python-3140/"
[5]: https://bits.debian.org/2025/08/trixie-released.html "https://bits.debian.org/2025/08/trixie-released.html"
[6]: https://go.dev/doc/go1.27 "https://go.dev/doc/go1.27"
[7]: https://go.dev/doc/devel/release "https://go.dev/doc/devel/release"
[8]: https://nodejs.org/en/about/previous-releases "https://nodejs.org/en/about/previous-releases"
[9]: https://nodejs.org/en/blog/release/v24.11.0 "https://nodejs.org/en/blog/release/v24.11.0"
[10]: https://www.oracle.com/partners/campaign/lifetime-support-middleware-069163.pdf "https://www.oracle.com/partners/campaign/lifetime-support-middleware-069163.pdf"
[11]: https://docs.astral.sh/uv/concepts/projects/layout/ "https://docs.astral.sh/uv/concepts/projects/layout/"
[12]: https://docs.docker.com/engine/release-notes/23.0/ "https://docs.docker.com/engine/release-notes/23.0/"
[13]: https://mirror-anu4.debian.org/releases/trixie/release-notes/whats-new.en.html "https://mirror-anu4.debian.org/releases/trixie/release-notes/whats-new.en.html"
[14]: https://docs.docker.com/engine/security/seccomp/ "https://docs.docker.com/engine/security/seccomp/"
[15]: https://man7.org/linux/man-pages/man7/capabilities.7.html "https://man7.org/linux/man-pages/man7/capabilities.7.html"
[16]: https://docs.docker.com/reference/compose-file/services/ "https://docs.docker.com/reference/compose-file/services/"
