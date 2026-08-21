# Step 00：决策门与版本锁

## 目标

建立本轮唯一的版本、平台、兼容和回滚事实源。此 Step 不升级业务代码，不切换数据库，不删除旧锁文件；只建立证据和停止门。

## 进入条件

- `main` 是当前工作分支，工作树干净或所有未提交变更已明确登记。
- `docs/research/01-*.md` 至 `07-*.md` 可读。
- `docs/plans/oj-unification/` 的目录迁移基线已完成。
- 不存在生产 Secret、数据库 dump、Redis RDB/AOF 或用户数据待提交。

## 计划文件

新增：

- `docs/contracts/modernization-version-lock.md`
- `docs/contracts/modernization-compatibility.md`
- `docs/plans/oj-modernization-2026/execution-log.md`

只读核对：

- `frontend/package.json`、`.nvmrc`、`yarn.lock`
- `backend/deploy/requirements.txt`、`backend/Dockerfile`
- `server/judge-server/Dockerfile`
- `docker-compose.yml`
- 七份 `docs/research/*.md`

## 版本锁初稿

在版本锁中登记候选、依据、精确 patch、digest、发布日期和复核日期：

| 组件 | 候选 | 本轮规则 |
|---|---|---|
| 宿主 | Ubuntu 24.04 LTS | 固定，不可替换 |
| Python | 3.12.x `<3.13` | backend/JudgeServer 同一维护线；锁 micro |
| Node | 24.x LTS，优先 24.19.0 | 不选 Node26 Current |
| pnpm | 11.x，优先 11.22.0 | 报告有 11.21.0/11.22.0 冲突，以 Step 00 重核结果定案 |
| Vite bridge/final | 7.3.6 / 8.2.1 | 分两个发布 |
| Vue bridge/final | 2.7.16 / 3.5.41 | Vue2 bridge 只保留两个生产发布周期 |
| Django | 4.2.30 / 5.2.17 | 4.2 仅 checkpoint |
| uv | 0.12.5 | lock 与镜像同时固定 |
| PostgreSQL | 18.6；备用17.11 | 以 PG18 restore rehearsal 结果做 GO/NO-GO |
| Redis | 6.2.23 → 7.4.10 → 8.2.8 | 不直接跨代、不切 Valkey |
| Judge | Python3.12、GCC14.2、JDK21、Go1.26.x、Node24、libseccomp2.6.x | 每种语言独立验证 |

精确版本若在实施日已变化，不能静默改计划；必须更新版本锁、影响的 Step 和回滚标签。

## 必须记录的决策

1. Python 3.12 的具体 micro、基础镜像 digest、`python --version` 和 ABI。
2. Node、pnpm、Vite、uv、Django、数据库镜像和 Judge toolchain 的官方来源。
3. PG18 与 PG17 的 staging 选择结果；若选择 PG17，记录 blocker 和复审日期。
4. Redis 许可证审查结果；本计划默认不切 Valkey。
5. amd64 为 Judge 生产架构；arm64 的支持状态必须写成 experimental 或 supported，不能模糊描述。
6. Ubuntu 24.04 宿主的 Docker Engine、Compose plugin、Buildx/BuildKit 版本及 cgroup v2 状态。

## 计划命令

以下命令只收集版本，不打印 Secret：

```bash
set -eu
printf '%s\n' '--- git ---'
git rev-parse HEAD
git status --short --branch
printf '%s\n' '--- host ---'
. /etc/os-release && printf '%s %s\n' "$ID" "$VERSION_ID"
uname -m
printf '%s\n' '--- container tooling ---'
docker version --format '{{.Server.Version}}'
docker compose version
docker buildx version
printf '%s\n' '--- source declarations ---'
awk '/"packageManager"|"engines"/{print}' frontend/package.json || true
sed -n '1,80p' backend/deploy/requirements.txt
```

实施时用受控查询确认包元数据；不要用浮动 `latest` 直接生成 lock。所有 digest 保存到版本锁和部署元数据，不保存凭据。

## 验收

- 版本锁中没有未解释的候选冲突。
- 明确标注哪些组件有 LTS，哪些只有 stable/current/maintenance；不得给 Vite、pnpm、GCC、Go 等错误贴 LTS 标签。
- Python 3.13/3.14 不出现在生产实施命令、Dockerfile 或 `requires-python` 中。
- PG、Redis、Django、frontend、Judge 各自有独立回滚标签。
- 兼容文档列出 API、Session/CSRF、数据库、Redis DB1/DB4、Judge、安全边界。

## 停止条件

- 不能确认 Ubuntu 24.04 宿主或 Python3.12 运行基线。
- 版本来源只有博客/搜索摘要，没有官方或包元数据证据。
- 只能通过浮动 tag 构建，无法保存 digest。
- PG/Redis 主版本方案没有独立回滚卷和 restore 证据。
- 任何候选要求改变 app label、表名、migration 历史或判题协议。

## 回滚

本 Step 只产生文档和版本锁；错误时恢复该文档提交即可，不触碰运行数据、旧锁文件和服务。

## 完成标志

提交格式建议：

```text
docs: lock modernization platform decisions
```

完成后依次进入 Step 01、02、03；未通过本 Step 不允许开始框架升级。
