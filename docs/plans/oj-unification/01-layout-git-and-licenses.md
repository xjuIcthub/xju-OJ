# 阶段 01：源码纳管、目录收敛与许可证边界

## 目标

在**不改变可观察业务行为**的前提下，把四个未跟踪源码目录收敛为目标三大主模块的目录布局，并让所有可版本化源文件受 Git 管理。此阶段不是前后端容器切换阶段；旧 Compose 可以暂时保留为兼容基线。

## 进入条件

- 阶段 00 的备份、契约和构建结果已经完成并提交。
- 当前分支从干净工作树开始。
- 团队已确认“顶层 `Judger/` 是唯一真实源码，`JudgeServer/Judger/` 是空历史目录”。
- 已人工检查 `OnlineJudge/data/` 中没有应该进入源码的运行时秘密；默认资源将移入显式源码目录。

## 目标布局

```text
frontend/                  <- OnlineJudgeFE/
backend/                   <- OnlineJudge/
server/
├── judge-server/          <- JudgeServer/（排除空 JudgeServer/Judger）
├── judger/                <- Judger/
├── Dockerfile             # 先在阶段 04 赋予新构建语义
├── LICENSES.md
└── README.md
deploy/                    # 阶段 05 填充运行配置
docs/
```

保留 Django 内部包与 app 名称：

```text
oj
account
announcement
conf
contest
fps
judge
options
problem
submission
utils
```

不要在这里把它们改成 `accounts`、`problems` 等复数名称。Django `INSTALLED_APPS`、`AUTH_USER_MODEL`、迁移依赖和已有 `django_migrations` 记录都依赖当前 app label。

## 步骤 01.1：创建受控分支和原始源码导入提交

由于四个模块目前未跟踪，先把**可审计的原样源码**纳入 Git；不要直接混合“导入”和“重构”在同一提交。

```bash
cd /home/winbeau/Projects/xju-OJ
git switch -c chore/unified-oj-layout
git status --short
```

1. 暂存代码、文档、测试、锁文件和许可证。
2. `data/` 受根 `.gitignore` 忽略，不能批量 `git add -f OnlineJudge/data`；逐个审查后仅强制暂存默认头像、favicon、`.gitkeep` 等无秘密的种子资源。
3. 不暂存 PostgreSQL、Redis、日志、测试数据、上传文件、`secret.key`、证书、node_modules、build 输出。
4. 审查暂存差异，确认无密钥、数据库 dump、环境文件或生成二进制。

建议拆成以下可审计提交：

```text
chore: import current OJ source baseline
chore: record OJ compatibility contracts
```

如果需要先修改 `.gitignore` 才能清楚表达安全边界，将它作为独立的第三提交并逐项审查例外规则。

## 步骤 01.2：重构 `.gitignore` 与源码种子资源

### 当前问题

根 `.gitignore` 含有 `data/`，它匹配嵌套的 `OnlineJudge/data/`。当前默认头像和 favicon 存在于该目录，而真正运行数据也在同一路径，造成“必要模板资源”和“绝不能提交的运行时数据”混在一起。

### 目标

1. 在根 `.gitignore` 新增明确的 `runtime/` 规则，保持运行时状态在忽略目录或由 `RUNTIME_ROOT` 指定的仓库外路径；
2. 保留现有通配 `data/` 规则作为过渡保护，直到阶段 03 删除临时 `backend/data/`；
3. 把需要随源码发布的文件迁移到：

```text
backend/resources/bootstrap/public/avatar/default.png
backend/resources/bootstrap/public/website/favicon.ico
```

4. 本阶段先**复制**安全种子资源到 `resources/bootstrap/`；保留旧 `data/` 内容直到阶段 03 的运行目录切换成功，避免目录整理破坏当前启动脚本。
5. 在后端 bootstrap 脚本中从 `resources/bootstrap/` 初始化空运行目录；该脚本改造放到阶段 03。
6. 仅在阶段 03 验证新运行目录后，才删除或清空临时 `backend/data/`；届时确保没有反向忽略规则意外纳入秘密。

执行安全种子迁移（仅当文件存在且经过人工确认，不要复制整个 `data/`）：

```bash
install -D -m 0644 OnlineJudge/data/public/avatar/default.png \
  OnlineJudge/resources/bootstrap/public/avatar/default.png
install -D -m 0644 OnlineJudge/data/public/website/favicon.ico \
  OnlineJudge/resources/bootstrap/public/website/favicon.ico
```

完成后逐项验证：

```bash
git check-ignore -v runtime/backend/config/secret.key
git check-ignore -v runtime/backend/test_case/example
! git check-ignore -q OnlineJudge/resources/bootstrap/public/avatar/default.png
git status --short
```

预期：前两项被忽略，种子资源不被忽略。

## 步骤 01.3：执行目录移动

在原始导入提交完成后，使用 Git 感知的移动；如果基线提交尚未完成，停止并回到步骤 01.1。

```bash
mkdir -p server
git mv OnlineJudgeFE frontend
git mv OnlineJudge backend
git mv JudgeServer server/judge-server
git mv Judger server/judger
```

本次 `git mv OnlineJudge backend` 可能同时在工作树中移动**被忽略的** `OnlineJudge/data/` 到 `backend/data/`。这是过渡期本地运行时目录，不应加入 Git，也不应在本阶段删除；阶段 03 会将其内容迁出到 `RUNTIME_ROOT` 后再清理。迁移空目录时还应避免把空的历史 `JudgeServer/Judger` 复制为第二份 Judger。Git 不跟踪空目录；在 `server/judge-server/` 中删除失效 `.gitmodules` 和空目录的动作必须单独记录为历史子模块清理，而非静默省略。

移动后立即检查：

```bash
find frontend backend server -maxdepth 2 -type d | sort
git diff --summary
git diff --check
git status --short
```

预期路径包括：

```text
frontend/package.json
backend/manage.py
backend/oj/settings.py
server/judge-server/server/server.py
server/judger/CMakeLists.txt
```

## 步骤 01.4：添加最小模块 README 与所有权说明

每个主模块先创建简洁 README，避免在目录移动阶段重新写完整开发文档：

| 文件 | 本阶段必须包含 |
|---|---|
| `frontend/README.md` | 职责、当前 Vue/Webpack 基线、构建入口、依赖的 `/api` 与 `/public` |
| `backend/README.md` | 职责、Django app 不改名原则、PostgreSQL/Redis/测试数据依赖、API/worker 边界 |
| `server/README.md` | `judge-server` 与 `judger` 的关系、运行权限风险、测试数据只读约束 |
| `server/LICENSES.md` | 指向 SATA 文本、保留版权和上游项目 URL 的说明 |
| 根 `README.md` | 三模块概览；旧部署说明标为过渡，不删除可回滚线索 |

不要为了“统一风格”删除：

```text
frontend/LICENSE
backend/LICENSE
server/judge-server/LICENSE
server/judger/LICENSE
```

`frontend`/`backend` 是 MIT，JudgeServer/Judger 是 SATA；许可证文本和归属必须继续随各自代码移动。

## 步骤 01.5：进行路径引用清单，而非一次性全改

目录移动会产生路径级改动，但不应该在本阶段全部猜测性修复。建立 `docs/contracts/path-reference-inventory.md`，将引用分为三类：

### A. 必须在阶段 02–05 修改

```text
backend/Dockerfile                          # 当前下载前端 dist
backend/deploy/entrypoint.sh                # /app、data/ 种子资源、Supervisor
backend/deploy/supervisord.conf             # oj.wsgi、/app
backend/deploy/nginx/*                      # 即将移出 backend
frontend/deploy/Dockerfile                  # 旧 /OJ_FE 路径和 Node 6
frontend/deploy/nginx.conf                  # 旧 oj-backend:8080 上游
server/judge-server/Dockerfile              # COPY Judger/ 的旧子模块假设
server/judge-server/.gitmodules             # 失效历史声明
根 docker-compose.yml                       # 旧模块/远程镜像拓扑
模块 CI 与 release workflow                  # 旧 build context
```

### B. 物理目录移动后仍可保持不变

```text
backend/manage.py -> DJANGO_SETTINGS_MODULE=oj.settings
backend/oj/wsgi.py -> oj.settings
backend/oj/settings.py -> ROOT_URLCONF=oj.urls
backend 内所有 Django app import
所有 migration 文件与 app label
```

### C. 需要通过搜索确认的外部引用

```bash
rg -n --hidden -g '!node_modules/**' -g '!*.lock' \
  '(OnlineJudgeFE|OnlineJudge|JudgeServer|Judger|/app/dist|/OJ_FE|COPY Judger|oj-backend)' \
  .
```

把每一处标注为“本阶段已修正 / 后续阶段负责 / 已确认仅文档历史”，不要让 `rg` 输出变成未跟踪的待办。

## 步骤 01.6：最小无行为验证

此阶段验证的是“源码仍能被工具定位”，不要求新容器已可运行：

```bash
cd backend
python3 manage.py check --settings=oj.settings
python3 manage.py showmigrations --settings=oj.settings
python3 manage.py makemigrations --check --dry-run --settings=oj.settings

cd ../frontend
node -e "const p=require('./package.json'); console.log(p.name, p.version)"

cd ../server/judger
cmake -S . -B build-layout-check
cmake --build build-layout-check --parallel "$(nproc)"
```

如果最后一个命令把 `output/libjudger.so` 写回源码目录，立刻清理生成物、添加合适忽略规则，然后重新执行；不要把二进制加入 Git。

## 建议提交点

```text
chore: import current OJ source baseline
chore: organize source into frontend backend server
chore: document module ownership and license boundaries
```

每个提交都应满足 `git diff --check`。目录移动提交不要混入 Docker 拓扑重写、依赖升级或 API 行为改动，确保 `git diff --find-renames` 可清楚审查文件历史。

## 验收门槛

- [ ] 三个一级业务目录存在，旧四个一级源码目录不再存在。
- [ ] 所有可版本化代码、测试、构建文件、许可证和安全种子资源由 Git 纳管。
- [ ] 运行时数据、密钥、证书、数据库、Redis、上传和编译产物仍被忽略。
- [ ] `server/judge-server/.gitmodules` 与空 `Judger` 历史目录不再误导构建。
- [ ] Django app label/迁移、API 路径、源码逻辑均未改动。
- [ ] backend Python 检查、frontend manifest 读取、Judger CMake 路径检查成功或失败已有基线记录。

## 停止条件与回滚

若暂存区出现未知二进制、秘密、测试数据或大批不合理删除，停止。由于每一步有独立提交，回滚优先使用 `git revert <commit>`；不要删除备份后再重新 clone。若目录移动尚未提交，可在确认没有同事改动后使用 `git restore --staged` 和受控反向 `git mv` 恢复。
