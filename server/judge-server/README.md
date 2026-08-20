# JudgeServer

这是 `server/judge-server/` 内的 Flask/Gunicorn 判题 HTTP 服务。当前阶段只改变物理目录，不改变协议：`POST /judge`、`POST /compile_spj`、`POST /ping`、心跳字段、Token 摘要头和 `{"err": ..., "data": ...}` 包装均保持不变。

- 运行时通过 `/usr/lib/judger/libjudger.so` 使用同级主模块 `../judger` 构建的 Python binding。
- 测试数据目录只读；服务工作目录、编译用户、运行用户和 SPJ 用户的权限边界由现有配置/镜像保持。
- 构建 context、`COPY` 路径和容器职责在阶段 04 处理，本阶段不在这里改 Dockerfile。

[Document](http://opensource.qduoj.com/)
