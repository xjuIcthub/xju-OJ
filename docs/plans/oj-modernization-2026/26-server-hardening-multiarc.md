# Step 26：Server 安全加固与多架构门禁

## 目标

在协议稳定后启用最小容器权限、只读 rootfs、tmpfs、pids 限制和显式 internal network；amd64 先支持，arm64 只有 native 安全验收后才升级状态。

## 进入条件

- Step 24 工具链 corpus 通过。
- Step 25 协议/liveness/heartbeat 回归通过。
- Ubuntu24.04 实际 Docker/cgroup/Seccomp 行为已经能复现。

## 初始安全配置

从最小集合开始，逐项启用：

```yaml
read_only: true
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - CHOWN
  - SETUID
  - SETGID
  - KILL
pids_limit: 512
```

可写位置仅为经测试的：

- `/tmp` tmpfs
- `/judger/run` tmpfs
- `/judger/spj` 明确 scratch volume/tmpfs
- `/log` writable volume

`/test_case` 永远 `:ro`。不预先加入 `SYS_ADMIN`、`SYS_PTRACE`、`NET_ADMIN`、`NET_RAW`、`BPF`、`PERFMON`、`SYS_MODULE`、`DAC_READ_SEARCH`。

## root 与降权

- JudgeServer/Judger master 保持 root。
- 子进程由 Judger 降权到 `compiler=901:901`、`code=902:902`、`spj=903:903`。
- 不把 Compose `user:` 设为非 root，不移除 supervisor 检查。

## Seccomp 规则

- C/C++ 严格 allowlist：升级 glibc/GCC 后重新采集 syscall baseline。
- Python general、Go、Node blacklist：测试 `clone3`、`openat2`、`io_uring`、`bpf`、`userfaultfd`、`pidfd_*` 等新路径。
- 编译阶段目前没有 language Seccomp；不能宣称编译/运行等价，长期加强另立项目。
- Docker 默认 Seccomp 保留，禁止全量 allow。

## 多架构

- amd64：第一生产支持目标。
- arm64：先 experimental。
- 两架构分别构建 native `libjudger.so`、wheel、工具链和 Seccomp 规则。
- QEMU/buildx 成功只说明可构建，不能替代 native 安全测试。
- arm64 必须完成正向语言、资源限制、攻击 corpus、workspace 权限和结果标定后才能 supported。

## 验收

- rootfs、`/test_case`、其他 workspace、网络、进程数、文件权限负向测试均阻止攻击。
- capability、UID/GID、tmpfs、pids、日志和清理行为符合基线。
- amd64 全语言/协议/安全回归通过；arm64 状态标签和限制在文档中明确。
- JudgeServer 无 host `ports:`；只可由 backend 内网访问。

## 停止条件

- 需要 privileged、Docker socket、SYS_ADMIN 或放宽 C/C++ Seccomp。
- `/test_case` 可写、其他 workspace 可读、网络可绕过。
- arm64 只有 QEMU 验证。
- 资源结果漂移而没有重新标定。

## 回滚

每一项 hardening 使用独立 commit；失败时切回上一 server image/security profile。保留旧日志、test_case 和 Judger scratch 的现场证据。

## 完成标志

提交格式建议：

```text
security(server): harden judge container and gate arm64 support
```

通过后才把 server 接入最终 BuildKit/Compose。
