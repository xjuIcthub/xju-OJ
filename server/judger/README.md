# Judger

这是 `server/judger/` 内的 C/Seccomp 沙箱核心及 bindings。它与 `server/judge-server/` 保持独立边界：本阶段仅移动源码，不改 `VERSION 0x020101`、资源限制、Seccomp 规则、结果码或 binding API。

- 判题服务通过 Python `_judger` binding 调用 `/usr/lib/judger/libjudger.so`。
- 运行用户、UID/GID、工作目录和测试数据只读约束由 JudgeServer/镜像层负责，不在此处复制或放宽。
- CMake、Python/Node/Lua binding 和安全测试继续从本目录单独构建/执行。

## 原始模块说明

[![Build Status](https://travis-ci.org/QingdaoU/Judger.svg?branch=newnew)](https://travis-ci.org/QingdaoU/Judger)

Judger for OnlineJudge 

[Document](https://opensource.qduoj.com#/judger/api)

[JudgeServer](https://github.com/QingdaoU/JudgeServer)

[OnlineJudge](https://github.com/QingdaoU/OnlineJudge)
