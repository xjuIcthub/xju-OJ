# Step 24：Server 判题工具链

## 目标

在构建边界稳定后，逐项固定 JudgeServer/Judger 的 Python3.12、GCC14.2、JDK21、Go1.26.x、Node24 和 libseccomp2.6.x；每种语言独立回归。

## 进入条件

- Step 23 新 context/build stages clean build 通过。
- Step 01 已有旧镜像协议和语言 corpus。
- amd64 builder 可用；arm64 不因本 Step 自动宣称生产支持。

## 工具链策略

- Python：JudgeServer 与 backend 固定 3.12.x；Judge builder/runtime 的 patch、ABI、digest 都记录。
- C/C++：GCC/G++14.2.x、C17/C++20，验证历史题结果和时限。
- Java：OpenJDK/Temurin21；Java25 后置，不在本轮追新。
- Go：1.26.x（候选1.26.5），不称 LTS。
- Node：24.x LTS；Node20 已过时，Node26不进入生产。
- libseccomp：2.6.x，重采集新 glibc/runtime syscall baseline。

系统包优先使用可验证的发行版包或固定上游 stage；不继续混用未锁定 Trixie/Adoptium/NodeSource 源。每个来源、版本、digest、许可证和 CVE 记录在 toolchain manifest。

## 单项顺序

1. 先固定 OS/Python，不改变语言描述。
2. GCC/CMake/libseccomp。
3. JDK21。
4. Node24。
5. Go1.26.x。
6. 每项完成后运行完整协议、资源和安全 corpus，再进入下一项。

## 计划命令

```bash
docker run --rm xju-oj/server:<git-sha> python --version
docker run --rm xju-oj/server:<git-sha> gcc --version
docker run --rm xju-oj/server:<git-sha> java -version
docker run --rm xju-oj/server:<git-sha> go version
docker run --rm xju-oj/server:<git-sha> node --version
```

输出只记录版本和构建 digest；不要输出环境变量/Token。

## 验收

每种语言至少覆盖：编译成功/语法错误、正常运行、stdin/stdout、Unicode、CPU/real/memory/output 限制、runtime error、子进程、rootfs、test_case 写入、其他 workspace 读取、TCP/UDP/Unix socket、线程/文件 IO、适用的 SPJ。

攻击用例的通过标准是行为被阻止，不是“进程退出”。资源结果需与旧镜像建立可解释的容差和重新标定记录。

## 停止条件

- 任何语言升级造成结果码/字段、时限、内存、文件或网络语义漂移且无法解释。
- 只能放宽 Seccomp、加 privileged 或写开放网络才能通过。
- 版本来自 mutable tag，无法重建同一 toolchain。
- Java/Go/Node/GCC 的升级与 Django/PG/Redis/前端框架混在一个发布。

## 回滚

每个工具链版本使用独立 `judge-toolchain:tc-vX.Y.Z` 和 server image digest；失败时只切回上一 toolchain/app image，保留 `/test_case`、`/log` 和业务数据。

## 完成标志

提交格式建议按工具链：

```text
build(server): pin judge Python and native toolchain
build(server): update judge language runtimes
```

协议/健康和 hardening 另由 Step 25/26 处理。
