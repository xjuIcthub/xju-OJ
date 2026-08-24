# Step 03：Ubuntu >=22.04 运行前置

## 目标

在仍受官方支持的 Ubuntu `>=22.04` 宿主上建立可验证的 Docker、Compose、BuildKit、目录、权限和 Secret 文件前置条件；生产优先使用 LTS，不启动新生产业务，不生成秘密。

## 进入条件

- Step 00 已锁定 Python3.10 和容器候选。
- Step 02 已记录当前卷、容量和构建基线。
- 目标机器由运维授权，执行命令不包含密码、Token 或私钥。

## 宿主门禁

必须记录但不写入应用日志：

- Ubuntu 精确版本（必须 `>=22.04` 且仍受支持）、内核、架构、cgroup v2。
- Docker Engine、containerd、Compose plugin、buildx、BuildKit 版本。
- systemd、时间同步、UTC、locale、磁盘空间/inode、挂载选项。
- 防火墙规则：只允许 frontend 配置的 HTTP/HTTPS；不开放 8000、8080、5432、6379。
- amd64 为 Judge 第一生产架构；arm64 另做 native 验收。

## 目录布局

默认根目录由部署变量指定，示例：

```text
/srv/xju-oj/
  runtime/backend/
  runtime/public/
  runtime/test_case/
  runtime/judger/
  runtime/log/
  volumes/postgres/10/
  volumes/postgres/18/
  volumes/redis/4/
  volumes/redis/6.2/
  volumes/redis/7.4/
  volumes/redis/8.2/
  deployments/
  secrets/
/var/backups/xju-oj/
```

PG/Redis 每代使用独立目录；不覆盖旧卷。`RUNTIME_ROOT` 必须是绝对路径，不能为 `/`，不能指向 Git 工作树中的未忽略敏感目录。

## 权限原则

- backup 和 secrets 目录 `0700`；文件 `0600`。
- 根据 pinned image 实际 UID/GID 设置数据库卷，不预设未经验证的宿主 UID。
- Judge 运行 UID/GID 901/902/903 的权限在实际 Ubuntu 内核/Docker 配置上验证。
- `/test_case` 和 frontend 的 `/public` 只读挂载。
- `/judger` 是可清理 scratch，不存 Secret、数据库 dump 或不可恢复数据。

## Secret 前置

本节只约束 Phase 5 生产发布。Phase 1–4 的 WSL/huawei1 隔离演练可使用专用、Git ignored、可销毁的测试 Secret 文件；测试 helper 可以创建这些文件，但 `deploy.sh` 不生成 Secret，且测试 Secret 不得复用为生产 Secret。

生产必须预先提供文件：

- PostgreSQL password
- Django `SECRET_KEY`
- Judge token
- 初始管理员密码
- 可选 TLS 证书/私钥

`deploy.sh` 只检查路径、权限和非空，不创建、打印、覆盖或回显内容。backend 缺少 Django Secret 必须 fail closed；不能沿用当前自动从 `/dev/urandom` 生成生产 Secret 的行为。

## 计划命令

```bash
set -eu
. /etc/os-release
[ "$ID" = ubuntu ]
dpkg --compare-versions "$VERSION_ID" ge 22.04

uname -m
stat -fc '%T' /sys/fs/cgroup

docker version
docker compose version
docker buildx version

docker info --format '{{json .DriverStatus}}'

df -h /srv /var/backups 2>/dev/null || df -h /

# 仅创建空目录；不创建 Secret 内容
install -d -m 0700 "$RUNTIME_ROOT/secrets" "$BACKUP_ROOT"
```

后续实际命令必须通过受控部署脚本传入变量；不得把真实 `RUNTIME_ROOT`、密码或 Token 粘贴到公共日志。

## 验收

- 宿主和 Docker 工具版本可重复记录。
- 持久化 BuildKit builder 可用，amd64 cache 与 arm64 cache 隔离。
- 所需空间能并存旧卷、新卷、dump、restore 临时空间和备份。
- 目录权限经过一次容器用户写入/只读测试。
- 所有 Secret 文件已经由外部系统提供，缺失时预期失败。

## 停止条件

- 宿主不是 Ubuntu、版本低于 22.04、已结束官方支持，或 cgroup/容器权限行为无法解释。
- 磁盘不足以并存 old/new/backup。
- Docker/Compose 不支持计划中的 health、`--wait`、BuildKit cache 或 secrets。
- 生产 Secret 只能通过命令行参数或 `.env` 明文提供。
- Judge 只能靠 rootless/privileged 才能运行。

## 回滚

只删除本 Step 创建的空目录或停用 builder；不删除旧数据卷、不执行 prune、不触碰 Secret 文件。

## 完成标志

提交格式建议：

```text
ops: establish Ubuntu 22+ deployment preflight
```

Ubuntu/Docker/BuildKit 和隔离目录预检通过后即可进入 Phase 1–4，生产 Secret 缺失只阻塞 Phase 5。创建生产数据库/Redis 卷和发布仍需完整 Secret、备份与切换门。
