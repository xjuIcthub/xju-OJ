# OJ 统一化基线版本与构建矩阵

- 基线采集时间：2026-08-20T12:17:28Z（目录名 `baseline-20260820T121728Z`）
- 仓库外快照目录：`/home/winbeau/.cache/xju-oj/baseline-20260820T121728Z`（目录权限 0700）
- 采集原则：只记录版本、哈希、路径和失败原因；不记录密码、Token、Cookie、私钥、证书内容或 Sentry DSN。

## Git 根基线

| 项目 | 结果 |
|---|---|
| `git rev-parse HEAD` | `0283f8a48d09a67a8943c6deed5933ed0e60492f` |
| 分支 | `main`，跟踪 `origin/main` |
| 远端 | `https://github.com/xjuIcthub/xju-OJ.git` |
| 初始索引 | 只有 `.gitignore`、`README.md`、`README.en.md`、`docker-compose.yml` |
| 初始工作树 | `JudgeServer/`、`Judger/`、`OnlineJudge/`、`OnlineJudgeFE/`、`docs/` 均未跟踪；只有根 `.git`；无有效 gitlink |
| 初始源码快照 | `source-tree.tgz`，可读取；排除了 `.git`、依赖缓存、Python 缓存和密钥/证书文件；外部副本中的已知硬编码 DSN 已替换为 `<redacted>` |
| 初始运行时快照 | `backend-data.tgz`，可读取；数据库/Redis 不在当前工作树中 |
| 快照安全核验 | `source-snapshot-safety.txt`；快照内未发现 `secret.key`、`.key`、`.crt`、`.pem` 文件名，`OnlineJudge/oj/settings.py` 仅保留 `<redacted>` 标记 |

四个源码目录在采集时均通过根仓库解析到同一根提交，并不是嵌套 Git 仓库。`JudgeServer/Judger/` 为空；当前未跟踪的 `JudgeServer/.gitmodules` 声明了 `Judger` 子模块，但当前没有 gitlink。

## Frontend

| 项目 | 基线事实 |
|---|---|
| 来源 | `OnlineJudgeFE/package.json`、`yarn.lock` |
| package 版本 | `onlinejudge@2.7.6` |
| `package.json` SHA-256 | `9b4684dc44df0c3d8c1c705c1ede6b5ed78186cd9961662327c480ce8a19db37` |
| `yarn.lock` SHA-256 | `1e344a057d83de5c5aa6f41186d0f623db99e1d8e3800f700e89fd7ef354fccb` |
| 当前检查环境 | Node `v24.16.0`、npm `11.13.0`；Yarn 不在 PATH |
| 历史容器 | `OnlineJudgeFE/deploy/Dockerfile` 使用 `node:6.11-alpine` |
| 代码形态 | Vue 2、Vue Router、Vuex、Axios、Webpack 3；用户端和管理端双入口 |
| 基线构建 | `yarn install --frozen-lockfile` 未执行（Yarn 缺失）；`npm run build:dll` 因 `webpack` 不在 PATH 失败；`npm run build` 因依赖 `chalk` 不存在失败 |

本阶段不安装 Yarn、不改 `package.json`/`yarn.lock`、不升级 Node 或 Webpack。后续阶段必须保留 Axios 同源 `/api`、CSRF Cookie/Header 和双 history 路由。

## Backend

| 项目 | 基线事实 |
|---|---|
| 依赖来源 | `OnlineJudge/deploy/requirements.txt` |
| requirements SHA-256 | `0dc46378e3fd62d4533294237024d5fa9e073e9a40767169e6edaff5bbb443bc` |
| 关键版本 | Django `3.2.25`、Django REST framework `3.14.0`、Dramatiq `1.16.0`、django-dramatiq `0.11.6`、psycopg2 `2.9.9`、django-redis `5.4.0` |
| Docker 运行时 | `python:3.12-alpine`；Dockerfile 同时安装 Nginx、Supervisor、Gunicorn 等运行组件 |
| 当前检查环境 | Python `3.10.12` |
| Dockerfile SHA-256 | `9b9b588317f0b9d266f22e004bd0eff430092796456c88ad98592206b812bdd6` |
| 当前入口 | `oj.settings`、`oj.wsgi`、`manage.py`；`INSTALLED_APPS` 的本地 app label 不变 |
| 基线检查 | 因当前 Python 环境没有 Django，`check`、`showmigrations`、`migrate --plan`、`makemigrations --check` 均在导入阶段失败；`flake8`、`coverage` 命令也不在 PATH |

后续不得改 Django app label、迁移历史、`db_table`、Session/CSRF 中间件顺序、Redis DB 约定或 `/api` 响应包装。

## JudgeServer

| 项目 | 基线事实 |
|---|---|
| Python 版本声明 | `JudgeServer/server/.python-version`：`3.6.2` |
| Docker 运行时 | `debian:trixie-slim`；最终层安装 Python 3.12、Flask/Gunicorn/requests 等（Flask/Gunicorn 未锁定小版本） |
| Dockerfile SHA-256 | `ec185601f691f7c4e4599094aa5c1fcbaf98febf1b61467f9a918c3252a610a9` |
| 服务端边界 | Flask `server.py` 暴露 `/judge`、`/compile_spj`、`/ping`，统一使用 `err/data` 包装 |
| 认证 | `X-Judge-Server-Token` 携带配置 Token 的 SHA-256 十六进制摘要；本阶段未输出摘要值 |
| 基线测试 | `python3 -m unittest tests/tests.py` 执行 3 个测试但因本地未启动可响应的 JudgeServer，3 个测试均在 JSON 解析处失败 |

## Judger

| 项目 | 基线事实 |
|---|---|
| CMake 来源 | `Judger/CMakeLists.txt`；SHA-256 `fc211b86b6d1eb6e2412a35ba5121f2e865876aea2c101be9352ab71a4c5bf34` |
| C 核心版本 | `Judger/src/runner.h` 的 `VERSION 0x020101`，按源码规则为 `2.1.1` |
| Python binding | `Judger/bindings/Python/setup.cfg`：`judger==2.2.0`；`_judger.VERSION` 为 `0x020101`（核心版本 `2.1.1`） |
| Node binding | `Judger/bindings/NodeJS/package.json`：`judger@1.0.0` |
| libseccomp | 主机运行库 `libseccomp2` 为 `2.5.3-2ubuntu3~22.04.1`；`libseccomp-dev` 未安装，故头文件缺失 |
| 当前构建工具 | CMake `3.30.2`、GCC `11.4.0` |
| 配置检查 | `cmake -S . -B build` 成功 |
| 编译检查 | `cmake --build build` 因环境缺少 `seccomp.h` 失败；本阶段未修改 C/Seccomp 代码 |
| 许可证 | `JudgeServer/LICENSE` 与 `Judger/LICENSE` 均为 SATA；不得在目录收敛时合并覆盖 |

## Runtime / Compose

| 项目 | 基线事实 |
|---|---|
| Compose 来源 | 根 `docker-compose.yml`，SHA-256 `344a769ea6c0ad78a3bab1290f83f8215a297e4ca5ffb3a2351d302ad549060b` |
| 数据库 | `postgres:10-alpine` |
| Redis | `redis:4.0-alpine` |
| 后端镜像 | `registry.cn-hongkong.aliyuncs.com/oj-image/backend:1.6.1` |
| 判题镜像 | `registry.cn-hongkong.aliyuncs.com/oj-image/judge:1.6.1` |
| 本地源码构建 | 当前 Compose 没有 `build`，不能证明本地源码可构建或可发布 |
| `docker compose config` | 在未绑定真实环境变量时退出码为 0，但产生未设置变量警告及 `version` 字段过时警告；没有把该结果当作运行成功证据 |
| Redis 逻辑 | Redis DB 1 承载 Django cache/Session/waiting queue；DB 4 承载 Dramatiq broker/result |
| Compose 卷 | Redis `./data/redis:/data`；PostgreSQL `./data/postgres:/var/lib/postgresql/data`；JudgeServer `./data/backend/test_case:/test_case:ro`、`./data/judge_server/log:/log`、`./data/judge_server/run:/judger`；Backend `./data/backend:/data` |
| Compose 端口 | Backend 发布 `0.0.0.0:80->8000` 与 `0.0.0.0:443->1443`；JudgeServer 容器端口为 `8080`，当前根 Compose 不直接发布到宿主机 |

## 许可证哈希与边界

| 目录/文件 | 类型 | SHA-256 |
|---|---|---|
| `OnlineJudge/LICENSE` | MIT | `e9a5f908dcaa26ae628b75ca131a69b9f39d9cae999c5081bea33b759c1248aa` |
| `OnlineJudgeFE/LICENSE` | MIT（含上游依赖许可证文本） | `8edf510bf1ba03d88eb07ef5038a211e8fbca5b5b5003718a5aed5c51db961e0` |
| `JudgeServer/LICENSE` | SATA | `10328b2fe2628791510c6c806c7c8121132dd777a8f5acf5aa8684001709017e` |
| `Judger/LICENSE` | SATA | `10328b2fe2628791510c6c806c7c8121132dd777a8f5acf5aa8684001709017e` |

阶段 0 只冻结上述事实。Node/Yarn、Python 3.8/3.10/3.12、前端 `2.7.6` 与旧 Docker 下载 `2.7.5`、libseccomp 开发头缺失、以及 Compose 远程镜像漂移均登记为后续阶段的兼容风险，不在本阶段升级或修复。
