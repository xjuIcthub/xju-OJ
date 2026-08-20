# Backend 运行时与进程契约

## 阶段 03 目标布局

`backend/` 是独立 Django 业务模块；frontend 提供浏览器静态入口和同源 Nginx，backend 不再下载、复制或服务 frontend `dist`。

| 角色 | 启动入口 | 监听/职责 | 数据依赖 |
|---|---|---|---|
| `backend-migrate` | `./deploy/entrypoint.sh migrate` | 一次性 `check` + `migrate --no-input` | PostgreSQL、runtime secret |
| `backend-api` | `./deploy/entrypoint.sh api` | Gunicorn `oj.wsgi:application`，默认 `0.0.0.0:8000` | PostgreSQL、Redis DB 1/4、已完成迁移 |
| `backend-worker` | `./deploy/entrypoint.sh worker` | `rundramatiq`，只消费 actor | PostgreSQL、Redis DB 1/4、已完成迁移 |
| `bootstrap-runtime` | `./deploy/entrypoint.sh bootstrap-runtime [--dry-run]` | 幂等创建目录、secret 和无秘密种子 | `RUNTIME_ROOT`/`OJ_DATA_DIR` 文件卷 |
| `configure-judge-token` | `./deploy/entrypoint.sh configure-judge-token` | 仅在数据库没有 token 时从外部 secret 配置 | PostgreSQL |
| `create-initial-admin` | `./deploy/entrypoint.sh create-initial-admin` | 仅新安装、无超级管理员时从密码文件创建 | PostgreSQL |
| `manage` | `./deploy/entrypoint.sh manage <django-command>` | 受控透传管理命令，供检查/测试；不自动迁移 | PostgreSQL/Redis 按命令需要 |

旧 `deploy/nginx/` 和 `deploy/supervisord.conf` 保留在源码中作迁移/回滚参考，但被 `backend/.dockerignore` 排除，不进入新 backend 镜像运行路径。

## 镜像边界

- `backend/Dockerfile` 使用固定的 Python 3.12 Alpine 依赖层，仅安装 Django/Gunicorn/Dramatiq/Pillow/PostgreSQL 运行依赖。
- 已删除 downloader stage、上游 frontend `dist.zip`、Nginx、Supervisor 和 `COPY --from=downloader`。
- build context 必须为 `backend/`；`.dockerignore` 排除 `data/`、`runtime/`、密钥/证书、日志、缓存、前端和构建产物。
- API/Worker 通过 `su-exec` 以镜像内 `backend` 用户运行；bootstrap/migrate 允许一次性 root Job 处理挂载目录，再将 runtime 归属交给 backend 用户。
- 镜像和日志不写入 `SECRET_KEY`、JudgeServer token、数据库密码、Sentry DSN 或一次性管理员密码。

## 运行时目录

生产默认兼容旧 `/data`；设置 `RUNTIME_ROOT=/srv/xju-oj/runtime` 后，默认 `DATA_DIR` 为 `$RUNTIME_ROOT/backend`；显式 `OJ_DATA_DIR` 优先级最高。Django 内部变量仍叫 `DATA_DIR`，以保持 `TEST_CASE_DIR`、`UPLOAD_DIR`、`STATICFILES_DIRS` 和 `LOG_PATH` 语义。

```text
$RUNTIME_ROOT/
├── backend/
│   ├── config/secret.key
│   ├── public/avatar/default.png
│   ├── public/website/favicon.ico
│   ├── public/upload/
│   ├── test_case/<test_case_id>/
│   ├── log/
│   └── ssl/
├── postgres/
├── redis/
└── judge-server/
    ├── log/
    └── run/
```

- bootstrap 只在目标缺失时复制头像/favicon，不覆盖上传和已有数据。
- `Problem.test_case_id` 继续解析到 `DATA_DIR/test_case/<id>`；backend 可写/维护，JudgeServer 只读，frontend 不挂载。
- frontend 只读挂载 `backend/public`；不挂载 config、test_case、log、ssl、数据库、Redis 或 `/judger`。bootstrap 为 runtime 根和 public 路径设置可穿越/只读权限，同时将 config 设为 0700、secret 设为 0600；test_case/log/ssl 保持 backend 私有。
- Redis DB 1 继续承载 Session、cache、`waiting_queue`；DB 4 继续承载 Dramatiq broker/result。

## Secret 与初始化规则

### Django secret

`backend/oj/settings.py` 仍从 `DATA_DIR/config/secret.key` 读取。`bootstrap-runtime` 在文件缺失时以 0600 原子创建；它不打印内容、不覆盖现有文件、不执行迁移。

### JudgeServer token

`configure_judge_token` 仅接受 `JUDGE_SERVER_TOKEN_FILE` 或外部环境注入的 `JUDGE_SERVER_TOKEN`。如果 `SysOptions` 已有 `judge_server_token`，命令拒绝覆盖；Token 值不写 stdout。已有 token 的生产数据库必须先备份并保持不变。

### 初始管理员

`create_initial_admin` 只在不存在超级管理员时运行，要求 `INITIAL_ADMIN_USERNAME` 和 `INITIAL_ADMIN_PASSWORD_FILE`；密码至少 12 个字符，从文件读取，不作为命令行参数，不回显，不重置已有账户。升级数据库默认跳过。

旧 `inituser --username=root --password=rootroot` 启动路径已移除；`init_db.sh` 仅保留开发辅助能力，并要求外部 `POSTGRES_*`/管理员密码文件输入。

## API/Worker 不变量

- `oj.settings`、`oj.wsgi`、Django app label、migration 文件和数据库表名不变。
- `utils.models.JSONField` 使用与历史 migration graph 一致的 PostgreSQL JSONField 序列化；Django 3.2 会给出弃用 warning，但不产生 schema migration。阶段 03 不升级 JSONField 或重写 migration。
- `redis==4.6.0` 显式固定以保持与现有 Redis 4.0 服务兼容；未固定时新 resolver 会选择发送 RESP3 `HELLO` 的 Redis 8 客户端，破坏 Session/cache。
- `/api/*`、`/api/admin/*`、`{"error": ..., "data": ...}`、分页、Session/CSRF、上传和 `HTTP_APPKEY` 行为不变。
- API 不运行 migration；Worker 不运行 migration；migration Job 失败必须阻断后续角色启动。
- `judge.tasks.judge_task` actor、Redis DB 4 broker/result、Redis DB 1 `waiting_queue`、`JudgeDispatcher` 选择/计数/重试语义不变。
- 无可用 JudgeServer 时提交和 waiting queue 仍保持现有 Pending/重新投递可观察行为；本阶段不改 JudgeServer endpoint、Token hash、结果码或字段。

## 健康检查

旧 Supervisor XML-RPC 检查不再适用。API 可在 Compose/部署层调用：

```text
python3 deploy/runtime_smoke.py
python3 deploy/runtime_smoke.py --worker
```

```text
GET /api/website/
```

`backend/deploy/health_check.py` 只检查 API JSON 响应的 2xx 和 `error == null`；`runtime_smoke.py` 额外检查 Redis DB 1/4 和一次短 TTL cache 往返，Worker 用 `--worker` 跳过 HTTP 检查。Worker 仍应由进程存活和 actor 集成检查负责，不把 HTTP 健康误当作队列消费健康。
