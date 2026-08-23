# Step 23：Server 构建边界

## 目标

修复 server 的 Docker build context 和层边界，建立 `judge-toolchain`、Judger builder、JudgeServer dependency/app stages；本 Step 不升级语言工具链和 Seccomp 行为。

## 进入条件

- Step 02 已记录当前远程镜像与本地源码差异。
- Step 03 Ubuntu `>=22.04`/buildx 可用。
- Step 01 已有 Judge protocol、结果字段、权限和 corpus 基线。

## 当前 blocker

`server/judge-server/Dockerfile` 当前使用 `COPY Judger/`，实际源码在 `server/judger/`。Dockerfile 不能通过 `COPY ../judger` 越过 context；根 Compose 也仍使用远程 `judge:1.6.1`。

## 目标文件

新增/修改：

- `server/Dockerfile`
- `server/.dockerignore`
- `server/judge-server/pyproject.toml`
- `server/judge-server/uv.lock`
- `server/judge-server/server/entrypoint.sh`
- 根 Compose 的 server build 声明（后续 Step 28 完成）

## 推荐 context

```yaml
build:
  context: .
  dockerfile: server/Dockerfile
```

Dockerfile 只能按真实路径复制：

```text
COPY server/judger/ /src/server/judger/
COPY server/judge-server/ /src/server/judge-server/
```

`.dockerignore` 排除 `.git`、node_modules、`.venv`、缓存、日志、构建输出和运行数据，但保留 Judger tests、协议 fixtures、安全 corpus。

## 镜像阶段

```text
judge-toolchain     OS + toolchains + libseccomp + Python3.10 support
judger-build        CMake + libjudger.so + Python binding wheel
judge-server-deps   pyproject/uv.lock + Flask/Gunicorn dependencies
judge-server        native artifacts + app + root entrypoint
```

`judge-toolchain` 是低频更新的可发布基础镜像；其他 stages 作为业务构建缓存，不单独发布。

## 计划命令

```bash
docker buildx build --file server/Dockerfile \
  --target judge-server --tag xju-oj/server:<git-sha> .
docker image inspect xju-oj/server:<git-sha>
```

构建日志只保存层、digest 和错误，不打印环境变量或 Secret。

## 验收

- clean context 能找到 `server/judger` 和 `server/judge-server`，不复制第二份源码。
- Judger C library、Python binding、JudgeServer app 均进入最终镜像。
- JudgeServer 源码变化不会重新安装/编译 toolchain（有 build graph 证据）。
- 旧远程镜像仍可在回滚窗口使用；新镜像不发布宿主 8080。

## 停止条件

- 仍依赖错误大小写路径、父目录 COPY 或远程未锁定源码。
- 为构建需要把生产 `/test_case`、Secret、runtime/log 放入 context。
- 只能通过 privileged、Docker socket 或 SYS_ADMIN 编译/运行。

## 回滚

只切回旧 server image/build definition；不改协议、数据卷和 backend。

## 完成标志

提交格式建议：

```text
build(server): establish repository-root build context and stages
```

后续工具链变更必须单独提交。
