# Judger

这是 `server/judger/` 内的 C/Seccomp 沙箱核心及 bindings。它与 `server/judge-server/` 保持独立边界；当前 native/binding 版本为 `2.1.4`。

- 判题服务通过 Python `_judger` binding 调用 `/usr/lib/judger/libjudger.so`。
- Runner 使用显式 `cwd`、close-on-exec error pipe、单调时钟、进程组与 subreaper 完成 setup 错误、超时和后代回收闭环。
- 固定 UID/GID 在 exec 前完成完整降权；File IO 通过 Landlock ABI 3+ 将写入限制在 testcase cwd。
- C/C++、Python、Go、Node、Java 使用独立 Seccomp profile；Node 同时启用 permission model，子进程与二次 exec 保持禁止。
- `ERROR_CHDIR_FAILED=-14` 是 2.1.4 新增的 setup 错误；既有结果码与 JudgeServer 响应字段保持不变。
- CMake、Python/Node/Lua binding 和安全测试继续从本目录单独构建/执行。

## 原始模块说明

[![Build Status](https://travis-ci.org/QingdaoU/Judger.svg?branch=newnew)](https://travis-ci.org/QingdaoU/Judger)

Judger for OnlineJudge 

[Document](https://opensource.qduoj.com#/judger/api)

[JudgeServer](https://github.com/QingdaoU/JudgeServer)

[OnlineJudge](https://github.com/QingdaoU/OnlineJudge)
