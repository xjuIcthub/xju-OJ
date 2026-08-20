# 阶段 00：冻结基线、接口契约与数据资产

## 目标

在移动任何目录、修改任何启动脚本前，把当前工作树变成可审计、可恢复的基线。该阶段不做架构重写；只收集事实、生成契约样本、备份运行时资产并提交基线。

## 进入条件

- 在仓库根目录 `/home/winbeau/Projects/xju-OJ` 执行。
- 确认没有其他开发者未提交的改动；若有，先记录并停止，不要覆盖。
- 准备一个**仓库外**的备份目录，例如 `/secure-backup/xju-oj/<timestamp>`；不要把数据库、密钥、Cookie、Token 或生产代码输出到 Git、聊天记录或日志。
- 具备 Python、Node/Yarn、Docker Compose 和 PostgreSQL/Redis 访问权限。缺失工具时先按仓库运行环境补齐，不在本阶段升级依赖。

## 禁止事项

1. 不执行 `mv`、`git mv`、删除旧目录或修改业务代码。
2. 不在生产数据库上执行 `makemigrations`、`migrate`、数据修复脚本或清空 Redis。
3. 不把 `JUDGE_SERVER_TOKEN`、数据库密码、Sentry DSN、`secret.key` 写入新增文档或终端输出。
4. 不把远程预构建镜像当作本地源码已经构建成功的证据。

## 步骤 00.1：记录 Git 与工作树事实

```bash
cd /home/winbeau/Projects/xju-OJ
BASELINE_ID=$(date -u +%Y%m%dT%H%M%SZ)
export BASELINE_DIR=/secure-backup/xju-oj/baseline-$BASELINE_ID
mkdir -p "$BASELINE_DIR"

git rev-parse HEAD > "$BASELINE_DIR/root-commit.txt"
git status --short --branch > "$BASELINE_DIR/git-status.txt"
git remote -v > "$BASELINE_DIR/git-remotes.txt"
git ls-files --stage > "$BASELINE_DIR/tracked-index.txt"
git submodule status > "$BASELINE_DIR/submodules.txt" 2>&1 || true
find . -path './.git' -prune -o -type f -print | sort > "$BASELINE_DIR/all-files.txt"
find . -path './.git' -prune -o -type f -print0 | sort -z | xargs -0 sha256sum > "$BASELINE_DIR/all-files.sha256"
```

当前事实应与调研一致：根 `HEAD` 为 `0283f8a`，四个源码目录均未跟踪，只有根 `.git`，`git submodule status` 不应列出有效 gitlink。若任一事实不同，将实际结果写入计划执行记录并暂停后续假设。

检查空的历史子模块目录：

```bash
find JudgeServer/Judger -mindepth 1 -print
find . -type d -name .git -print
```

预期 `JudgeServer/Judger` 为空、实际 Judger 源码在顶层 `Judger/`；这决定阶段 01 必须显式处理 `.gitmodules` 与 Docker build context。

## 步骤 00.2：保存源码与运行时资产快照

源码快照不包含 `.git` 和运行时秘密：

```bash
tar --exclude='./.git' \
    --exclude='*/node_modules' \
    --exclude='*/__pycache__' \
    --exclude='*/data/config/secret.key' \
    --exclude='*/data/ssl/*.key' \
    --exclude='*/data/ssl/*.crt' \
    -czf "$BASELINE_DIR/source-tree.tgz" .
```

若存在实际部署数据，分别备份，不要假定 Git 中的空目录代表数据完整：

```bash
tar -czf "$BASELINE_DIR/backend-data.tgz" \
    OnlineJudge/data/config \
    OnlineJudge/data/public \
    OnlineJudge/data/test_case \
    OnlineJudge/data/ssl \
    OnlineJudge/data/log
```

生产 PostgreSQL 使用管理员提供的安全连接参数执行（示例中的变量只存在于受控 TTY，不写入脚本）：

```bash
pg_dump -Fc -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -f "$BASELINE_DIR/onlinejudge-before-unification.dump"
```

Redis 备份策略必须先和运维确认：Redis DB 1 同时承载 Session、缓存和 `waiting_queue`，DB 4 承载 Dramatiq broker/result。优先保存原数据卷或 RDB/AOF，并额外记录队列长度；不要在运行中用 `FLUSHALL`：

```bash
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -n 1 llen waiting_queue
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -n 4 dbsize
```

若当前环境没有可访问数据库/Redis，记录为“未验证”，不要伪造备份成功。

## 步骤 00.3：建立版本与构建矩阵

把实际版本写入 `docs/contracts/version-matrix.md`，至少包含：

| 组件 | 当前来源 | 必须记录 |
|---|---|---|
| Root | `git rev-parse HEAD` | commit、工作树状态 |
| Frontend | `OnlineJudgeFE/package.json`、`yarn.lock` | package 版本、Node、Yarn、锁文件 hash |
| Backend | `OnlineJudge/deploy/requirements.txt`、`OnlineJudge/Dockerfile` | Python、Django、DRF、依赖文件 hash |
| JudgeServer | `JudgeServer/Dockerfile`、`server/.python-version` | Python、Flask/Gunicorn、镜像基础层 |
| Judger | `Judger/CMakeLists.txt`、`bindings/Python` | CMake、gcc、libseccomp、binding 版本常量 |
| Runtime | `docker-compose.yml` | PostgreSQL、Redis、镜像 tag/digest、卷和端口 |

执行只读检查：

```bash
cd OnlineJudgeFE
node --version
npm --version
yarn --version
git rev-parse HEAD
sha256sum package.json yarn.lock
cd ../OnlineJudge
python3 --version
sha256sum deploy/requirements.txt Dockerfile
cd ..
docker compose config > "$BASELINE_DIR/compose-config.txt"
```

如果 `docker compose config` 因未设置环境变量失败，保存失败原因并使用不含秘密值的变量名清单补充 `docs/contracts/version-matrix.md`；不要把真实值写进去。

## 步骤 00.4：生成前端—后端 API 清单

将来源固定为以下文件，不手工凭印象补 endpoint：

```text
OnlineJudge/oj/urls.py
OnlineJudge/*/urls/*.py
OnlineJudge/utils/urls.py
OnlineJudgeFE/src/pages/oj/api.js
OnlineJudgeFE/src/pages/admin/api.js
OnlineJudgeFE/src/pages/admin/components/Simditor.vue
OnlineJudgeFE/src/pages/admin/components/simditor-file-upload.js
OnlineJudgeFE/src/pages/admin/views/problem/Problem.vue
OnlineJudgeFE/src/pages/admin/views/problem/ImportAndExport.vue
OnlineJudgeFE/src/pages/oj/views/setting/children/ProfileSetting.vue
```

把每个端点登记到 `docs/contracts/api-compatibility.md`，字段至少包括：

- 方法、完整路径、调用端（用户端/管理端/判题服务）；
- 是否需要 Session、管理员角色、超级管理员、比赛权限或 `APPKEY`；
- Content-Type（JSON、URL encoded、multipart、二进制）；
- 请求字段、分页参数、成功 `data` 形状；
- 错误码和登录失效表现；
- CSRF 是否豁免；
- 对应后端 View、Serializer 和测试文件。

第一轮必须明确记录以下兼容点：

```text
/api/*
/api/admin/*
/api/judge_server_heartbeat/
/api/upload_image/
/api/upload_file/
/api/admin/test_case
/api/admin/import_problem
/api/admin/import_fps
```

## 步骤 00.5：生成 JudgeServer 协议样本

在 `docs/contracts/judge-server-protocol.md` 固化脱敏后的样本和字段表：

### Backend -> Server

- `POST /judge`
- `POST /compile_spj`
- 可选 `POST /ping`
- 请求头 `X-Judge-Server-Token: sha256(JUDGE_SERVER_TOKEN)`
- `judge` 请求中的 `language_config`、`src`、`max_cpu_time`、`max_memory`、`test_case_id`、`output`、SPJ 和 `io_mode` 字段；
- 返回包装 `{"err": null|..., "data": ...}`；测试点结果中的 `cpu_time`、`memory`、`result`、`test_case`、`signal`、`exit_code`、`error`、`output_md5`、`output`。

### Server -> Backend

- `POST /api/judge_server_heartbeat/`；
- `X-Judge-Server-Token` 为同一明文 Token 的 SHA-256；
- `hostname`、`judger_version`、`cpu_core`、`cpu`、`memory`、`action=heartbeat`、`service_url`；
- Backend 返回 `{"error": null, "data": null}`。

样本必须来自 `OnlineJudge/judge/dispatcher.py`、`OnlineJudge/conf/{serializers,views}.py`、`JudgeServer/server/{server,service,utils}.py` 及客户端实现，不要把明文 Token 放入 fixture。

## 步骤 00.6：做当前基线验证

只在隔离开发环境执行；不把失败归因于目录迁移。`oj.settings` 会读取 `data/config/secret.key`；若该**开发环境**文件尚不存在，先在被忽略目录生成临时值，绝不提交或显示其内容：

```bash
cd OnlineJudge
if [ ! -f data/config/secret.key ]; then
  mkdir -p data/config
  umask 077
  head -c 32 /dev/urandom | base64 > data/config/secret.key
fi
python3 manage.py check --settings=oj.settings
python3 manage.py showmigrations --settings=oj.settings
python3 manage.py migrate --plan --settings=oj.settings
python3 manage.py makemigrations --check --dry-run --settings=oj.settings
flake8 --config=./.flake8 .
coverage run --include="$PWD/*" manage.py test
coverage report
```

前端基线：

```bash
cd ../OnlineJudgeFE
yarn install --frozen-lockfile
npm run build:dll
npm run build
```

如果只能用 `npm install`，记录实际 Node/npm 版本和依赖解析差异，不覆盖 `yarn.lock`。前端构建失败时保存首个根因（Node、DLL manifest、依赖或源码），不要先升级依赖。

Judger/Server 基线：

```bash
cd ../Judger
cmake -S . -B build
cmake --build build --parallel "$(nproc)"
cd ../JudgeServer
python3 -m unittest tests/tests.py
```

JudgeServer 的端到端测试需要容器和真实服务；若当前 Dockerfile 因 `COPY Judger/` 找不到路径失败，这是已确认的基线缺陷，记录后交给阶段 04，不要用临时复制目录掩盖。

## 产物

阶段 00 结束时应新增（建议只提交脱敏文本和 hash）：

```text
docs/contracts/version-matrix.md
docs/contracts/api-compatibility.md
docs/contracts/judge-server-protocol.md
docs/contracts/runtime-data-inventory.md
docs/plans/oj-unification/execution-log.md
```

`execution-log.md` 记录命令、时间、环境、结果和失败根因，不记录秘密值。

## 验收门槛

- [ ] 备份目录存在且可读取；PostgreSQL/运行时数据/Redis 的实际状态明确标注。
- [ ] 四模块文件清单、hash、许可证和 Git 纳管状态已保存。
- [ ] API、Session/CSRF、文件、心跳、判题协议均有脱敏样本。
- [ ] 已知版本漂移（前端 `2.7.6` vs 后端 Dockerfile 下载 `oj_2.7.5`、Node 6/8、Python 3.8/3.12、Compose 远程镜像）已记录。
- [ ] 基线测试结果可重复，或失败已定位且未被误记为迁移问题。
- [ ] 完成一次基线提交；提交前 `git diff --check` 通过。

## 停止条件与回滚

任何备份缺失、工作树有未解释改动、生产凭据可能泄露、数据库迁移状态不明时停止。此阶段尚未移动源码，回滚就是删除未提交的脱敏调研文件并从仓库外快照恢复；不要通过 `git reset --hard` 擅自抹掉他人改动。
