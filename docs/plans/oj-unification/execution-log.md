# OJ 统一化阶段 00 执行记录

- 阶段：`00-baseline-and-contracts`
- 仓库：`/home/winbeau/Projects/xju-OJ`
- 采集基线：`2026-08-20T12:17:28Z`，UTC 标识 `20260820T121728Z`
- 原则：不移动目录、不改业务代码、不执行生产迁移、不输出或保存凭据明文。
- 外部快照：`/home/winbeau/.cache/xju-oj/baseline-20260820T121728Z`

## 00.1 Git 与工作树

| 时间/命令 | 结果 |
|---|---|
| `git rev-parse HEAD` | `0283f8a48d09a67a8943c6deed5933ed0e60492f` |
| `git status --short --branch` | `main...origin/main`；`JudgeServer/`、`Judger/`、`OnlineJudge/`、`OnlineJudgeFE/`、`docs/` 未跟踪 |
| `git remote -v` | `origin` 指向 `https://github.com/xjuIcthub/xju-OJ.git` |
| `git ls-files --stage` | 只有根四个文件：`.gitignore`、两个 README、`docker-compose.yml` |
| `git submodule status` / `.git` 搜索 | 无有效 gitlink；只有根 `.git` |
| `find JudgeServer/Judger -mindepth 1 -print` | 无输出，目录为空 |

该未跟踪状态与计划的源码调研一致；没有覆盖或重置已有提交。`docs/` 是随任务提供的阶段计划，源码四目录是待纳管的原始快照。

## 00.2 源码与运行时资产

| 命令/动作 | 结果 |
|---|---|
| `mkdir -p /secure-backup/xju-oj/...` | 失败：当前用户无权创建 `/secure-backup`；未使用 sudo、未请求凭据 |
| 外部备份降级 | 使用权限 0700 的 `/home/winbeau/.cache/xju-oj/baseline-20260820T121728Z` |
| `find ... > all-files.txt`、SHA-256 清单 | 成功 |
| `tar ... source-tree.tgz` | 成功；排除依赖缓存、Python 缓存、密钥、证书；发现源码中已有硬编码 DSN 后，在外部副本中将该字段替换为 `<redacted>`，仓库源文件未改动 |
| `source-snapshot-safety.txt` 核验 | 成功；外部快照不含 `secret.key`、`.key`、`.crt`、`.pem` 文件名，已知 DSN 仅保留脱敏标记 |
| 根 `.gitattributes` | 新增仅用于基线导入的 whitespace 属性，保留四模块历史 CRLF/行尾空白字节；不改变运行逻辑 |
| `git diff --cached --check` / `git diff --check` | 均通过；不对上游源码做无关的空白重写 |
| `tar ... backend-data.tgz` | 成功且可读取；当时只有仓库占位文件和公开静态资源 |
| PostgreSQL/Redis 备份 | 未执行：本地 PostgreSQL/Redis 不可达，且未提供受控生产连接参数；状态写入 `runtime-data-inventory.md` |

## 00.3 版本与 Compose

| 命令/检查 | 结果 |
|---|---|
| `node --version` / `npm --version` | `v24.16.0` / `11.13.0` |
| `yarn --version` | 失败：Yarn 不在 PATH；没有安装或改写 lockfile |
| `python3 --version` | `Python 3.10.12` |
| `cmake --version` / `gcc --version` | `3.30.2` / `11.4.0` |
| `docker compose version` | `v2.39.2` |
| `docker compose config` | 退出码 0；未绑定真实环境变量时产生变量未设置警告，并提示顶层 `version` 字段过时；未将其视作镜像或源码构建证据 |
| 版本/hash 采集 | 已写入 `docs/contracts/version-matrix.md`，不含敏感值 |

## 00.4 API 清单

通过静态阅读以下固定来源生成 `docs/contracts/api-compatibility.md`：后端 URL/View/Serializer/Form、两份前端 `api.js`、Simditor 上传、问题测试数据上传、问题导入导出、头像上传。记录了方法、完整路径、调用端/权限、Content-Type、CSRF、字段、响应和测试索引；同时保留了 `export_problem` 方法/路径不匹配等已知事实。没有通过手工猜测补充端点。

## 00.5 JudgeServer 协议

通过静态阅读 Dispatcher、心跳 View/Serializer、Flask server/service/utils、JudgeClient 和客户端实现生成 `docs/contracts/judge-server-protocol.md`。样本只使用合成字段值；Token 仅以 `<token_sha256>` 占位，未写入摘要、明文或运行时配置。

## 00.6 基线验证

### 开发密钥准备

首次检查发现 `OnlineJudge/data/config/secret.key` 不存在。按计划在被忽略目录生成 32 字节随机临时值，权限 0600；值未打印。该文件不进入 Git、不进入合同文档，也不代表生产密钥。

### Backend

执行了：

```text
python3 manage.py check --settings=oj.settings
python3 manage.py showmigrations --settings=oj.settings
python3 manage.py migrate --plan --settings=oj.settings
python3 manage.py makemigrations --check --dry-run --settings=oj.settings
flake8 --config=./.flake8 .
coverage run --include="$PWD/*" manage.py test
coverage report
```

结果：

- 四个 Django 管理命令均在导入阶段失败，根因是当前 Python 环境没有安装 `django`；没有接触数据库，也没有执行迁移。
- `flake8` 和 `coverage` 命令不在 PATH。
- 失败是环境依赖缺失，不是目录迁移造成；完整原始输出在外部快照 `backend-checks.txt`。

### Frontend

- `yarn install --frozen-lockfile` 未执行：Yarn 缺失，避免用 npm 改写 `yarn.lock`。
- `npm run build:dll` 失败：`webpack` 不存在。
- `npm run build` 失败：依赖 `chalk` 不存在。
- 失败是未安装前端依赖/工具链，不是目录迁移造成；完整原始输出在 `frontend-checks.txt`。

### Judger / JudgeServer

- `cmake -S . -B build` 成功。
- `cmake --build build --parallel "$(nproc)"` 失败，根因是环境缺少 `seccomp.h`；未修改 C/Seccomp 源码。随后删除了本次命令新生成的 `Judger/build/` 构建目录。
- `python3 -m unittest tests/tests.py` 启动了 3 个测试，但因没有可响应的本地 JudgeServer，3 个测试均在 JSON 解析处失败；未把它们误记为协议通过。
- 完整原始输出在 `judger-server-checks.txt`。

### 数据服务探针

- `pg_isready -h 127.0.0.1 -p 5435`：no response。
- Redis DB 1/4 在 `127.0.0.1:6380` 均 connection refused。
- 因此 PostgreSQL dump、Redis queue/dbsize 和生产数据状态标为“未验证”；没有执行写操作或 `FLUSHALL`。

## 阶段 00 产物与验收映射

- [x] 外部源码/运行时快照存在且可读取；数据库/Redis 状态明确标为未验证。
- [x] 四模块文件清单、SHA-256、许可证和初始 Git 纳管状态已保存；外部源码快照已做敏感配置二次脱敏。
- [x] API、Session/CSRF、文件、心跳、判题协议有脱敏契约样本。
- [x] 已记录前端 `2.7.6` vs Docker 下载 `2.7.5`、Node 6.11/当前 Node、Python 3.6.2/3.10/3.12、Compose 远程镜像等漂移。
- [x] 可执行的基线结果已保存；失败均定位为环境缺失或服务未启动，未归因于迁移。
- [ ] 基线提交：待人工检查完成后执行。

## 阶段边界

本阶段没有执行 `mv`、`git mv`、旧目录删除、业务代码修改、生产 `makemigrations`/`migrate`、数据修复或 Redis 清空。下一阶段必须在本文件及三份合同验收、提交后才允许开始。

## 阶段 01：目录收敛执行记录

- 基线提交：`038b02d84728bc7aaf9b83ab613972ad0f729ffd`，提交后切换到受控分支 `chore/unified-oj-layout`。
- 受控移动已完成：`OnlineJudgeFE/ -> frontend/`、`OnlineJudge/ -> backend/`、`JudgeServer/ -> server/judge-server/`、`Judger/ -> server/judger/`。
- 迁移保留 backend 的过渡 `data/` 运行目录（未纳管）；未复制第二份 Judger 源码。
- 已删除移动后的 `server/judge-server/.gitmodules` 和空 `server/judge-server/Judger/`；这是失效历史子模块清理，不是业务代码变更。
- 已逐项复制无秘密默认资源到 `backend/resources/bootstrap/public/avatar/default.png` 与 `backend/resources/bootstrap/public/website/favicon.ico`，并以 SHA-256 比对源文件一致。
- 根 `.gitignore` 新增 `runtime/`；`data/` 过渡保护保留。`runtime/backend/config/secret.key`、`runtime/backend/test_case/example` 均被忽略，bootstrap 资源不被忽略。
- 新增/补充 `frontend/README.md`、`backend/README.md`、`server/README.md`、`server/LICENSES.md`、根 README 中英说明以及 `docs/contracts/path-reference-inventory.md`。
- 阶段 01 的 `rg` 路径引用清单已生成并按后续阶段、保持不变、历史文档三类归档；`backend/Dockerfile`、frontend 旧 Nginx、JudgeServer build context 和旧 Compose 未在本阶段改写。
- 最小验证：frontend manifest 读取成功；backend Django check 仍因环境缺少 Django 而在导入阶段失败；Judger CMake 路径检查仍因环境缺少 `seccomp.h` 失败。两类失败均与阶段 00 相同，未归因于目录移动；生成的 `build-layout-check/` 已清理。
- 阶段 01 未改 Django app label、migration 内容、API 路径、响应包装、数据库表名、JudgeServer 协议、依赖版本或容器拓扑。

## 阶段 02：frontend 独立化执行记录

- 构建候选 Node `14.21.3` + Yarn `1.22.x` 已在官方 Node 14 临时副本中通过 frozen install、DLL、production build 和重复构建；生成 `dist/index.html`、`dist/admin/index.html`，两次 79 个产物的文件清单与 SHA-256 一致。
- 宿主 Node `24.16.0` + Corepack Yarn `1.22.22` 的 frozen install、lint 和带 OpenSSL legacy provider 的 build 通过；未加 provider 的旧 UglifyJS/OpenSSL 错误已记录，但 Node 24 未选为默认运行时。
- 新增 `frontend/.nvmrc`、`frontend/.dockerignore`、多阶段 `frontend/Dockerfile`、`frontend/nginx/nginx.conf`、`build:ci`，并让 `dev.env.js` 优先使用 `GIT_COMMIT`、无 Git 时回退 `unknown`；未升级业务依赖或改 `yarn.lock`。
- `frontend` Docker build 在构建环境显式传入可达的 HTTP(S) proxy 后成功；未传 proxy 的首次尝试因 Docker builder 使用不可达的 `127.0.0.1:9098` 失败，根因是环境网络而非 Dockerfile。镜像内入口、Nginx 配置和 `index.html`/`admin/index.html` 检查通过。
- 使用 Nginx 容器 + backend-api stub 完成静态路由冒烟：`/`、`/admin/`、history 路由、`/public/website/favicon.ico` 和 `/api/website/` 均成功；`/admin` 301 到 `/admin/`，JSON `error/data` 包装未被改写。Nginx 语法检查在为 `backend-api` 提供隔离 hosts 映射后通过。
- 生成 JS 未发现 Token 值、数据库连接、`backend-api:8000` 或 secret 文件内容；`/api/admin/test_case` 等公开 API 路径属于既有前端调用，不视为内部服务泄露。
- 阶段 02 未改 Vue 双入口、`/admin/` history base、Axios `/api`、CSRF Cookie/Header、`/public` 语义、Django API、数据库表名或 JudgeServer 协议。
