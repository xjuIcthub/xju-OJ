# 阶段 01 路径引用清单

- 采集阶段：01，目录移动后
- 目标：把目录路径变化与后续行为改造分离；本阶段只记录引用，不把 Docker、Nginx、API 或 Django import 进行猜测性重写。
- 当前布局：`frontend/` ← 原 `OnlineJudgeFE/`；`backend/` ← 原 `OnlineJudge/`；`server/judge-server/` ← 原 `JudgeServer/`；`server/judger/` ← 原 `Judger/`。

## A. 必须由后续阶段处理的路径

| 当前路径 | 当前引用/事实 | 负责阶段 | 阶段 01 动作 |
|---|---|---|---|
| `backend/Dockerfile` | downloader 下载上游 `oj_2.7.5/dist.zip`，并把 dist/Nginx/Supervisor 与后端镜像混在一起 | 02–03 | 保留原样；记录为后续构建边界问题 |
| `backend/deploy/entrypoint.sh` | 依赖 `/app`、`data/`、运行时 secret/证书和旧 Supervisor 启动方式 | 03 | 保留原样；不在目录提交中改变启动行为 |
| `backend/deploy/supervisord.conf` | 同时托管 API、worker 和 Nginx，含 `/app` 路径 | 03 | 保留原样 |
| `backend/deploy/nginx/*` | 后端容器内提供 SPA、`/public` 和 `/api`；即将移到 frontend 网关 | 02–03 | 保留原样 |
| `frontend/deploy/Dockerfile` | 使用 Node 6.11、`/OJ_FE` volume 和旧启动脚本 | 02 | 保留原样 |
| `frontend/deploy/run.sh` | `base=/OJ_FE` 并从旧路径构建/启动 | 02 | 保留原样 |
| `frontend/deploy/nginx.conf` | 仍引用 `/app/dist`、`/data/avatar`、`oj-backend:8080` | 02 | 保留原样；旧部署路径不得被误认为新网关 |
| `server/judge-server/Dockerfile` | `COPY Judger/ /app/` 假设 Judger 是 JudgeServer 子目录 | 04 | 保留原样；删除空 `.gitmodules`，修复 build context 留到阶段 04 |
| 根 `docker-compose.yml` | 只拉远程 `backend:1.6.1`/`judge:1.6.1`，使用旧 `data/*` 卷和端口 | 05 | 保留为回滚/兼容基线 |
| 模块 CI/release workflow | 仍按原仓库 context、路径或镜像发布 | 05 | 仅记录，未重写 |

## B. 物理移动后应保持不变的引用

这些引用随目录一起移动，但包名和语义不能改：

- `backend/manage.py` 的 `oj.settings`；`backend/oj/wsgi.py` 的 `oj.settings`。
- `backend/oj/settings.py` 的 `ROOT_URLCONF = 'oj.urls'`、`WSGI_APPLICATION = 'oj.wsgi.application'`。
- backend 内部 import 的 `account`、`announcement`、`conf`、`contest`、`fps`、`judge`、`options`、`problem`、`submission`、`utils`。
- 所有 `backend/*/migrations/` 文件名、依赖、app label 和数据库表名。
- `frontend/src/pages/{oj,admin}/api.js` 的 Axios base URL `/api`、CSRF Cookie/Header。
- `server/judge-server/server/` 的 Flask endpoint、`server/service.py` 心跳 URL/头和 `server/judger` binding 版本常量。

## C. 已确认仅为历史文档/上游归属的引用

以下匹配不属于本阶段运行路径，不改写：

- 模块 README、许可证中的上游 GitHub URL 和项目名称。
- `docs/plans/oj-unification/` 中描述迁移前后路径的计划文本。
- 前端界面中的产品名、`Judger` 翻译和用户可见帮助文本。
- JudgeServer 客户端示例中的上游仓库链接、旧公开包导入路径和测试说明。
- 根 README/README.en.md 旧部署说明；已在底部补充“旧 Compose 为兼容基线”的新布局说明，未删除回滚线索。

## D. 阶段 01 已完成的路径动作

- `git mv OnlineJudgeFE frontend`
- `git mv OnlineJudge backend`
- `git mv JudgeServer server/judge-server`
- `git mv Judger server/judger`
- 删除 `server/judge-server/.gitmodules`：它只声明失效的历史 `Judger` 子模块；未初始化 gitlink 不再误导构建。
- 删除移动后空的 `server/judge-server/Judger/` 目录；真实源码只有 `server/judger/` 一份。
- 复制无秘密默认资源到 `backend/resources/bootstrap/public/avatar/default.png` 和 `backend/resources/bootstrap/public/website/favicon.ico`；旧过渡数据目录保留在工作树但不纳管。
- 根 `.gitignore` 增加 `runtime/`；原有 `data/` 规则继续保留作为过渡保护。

## E. 后续搜索基线

阶段 01 移动后的搜索命令：

```bash
rg -n --hidden -g '!node_modules/**' -g '!*.lock' \
  '(OnlineJudgeFE|OnlineJudge|JudgeServer|Judger|/app/dist|/OJ_FE|COPY Judger|oj-backend)' \
  .
```

该命令仍会命中上述历史文档、上游归属和后续阶段负责的真实配置。后续阶段修改路径时必须更新本清单，并以契约测试证明 `/api`、`/public`、Django import 和 JudgeServer 协议没有行为漂移。
