# Step 12：Backend uv 安装器与运行规范

## 目标

将 backend Docker/CI/管理命令从 pip requirements 切换为 `uv sync --locked`，保持 Python3.12、旧框架和数据库连接不变。

## 进入条件

- Step 11 的 pyproject/uv.lock 可重建当前环境。
- Step 03 BuildKit 可用。
- 旧 backend 镜像仍可部署和回滚。

## 文件范围

- `backend/Dockerfile`
- `backend/deploy/entrypoint.sh`
- `backend/deploy/runtime_smoke.py`
- CI workflow
- `backend/README.md`

## Docker 分层

```text
base: Python3.12 + 系统运行库 + 精确 uv
deps: 只复制 pyproject.toml/uv.lock，uv sync --locked --no-install-project
app: 复制 backend 源码，必要时 uv sync --locked --no-dev
runtime: API/Worker 共用已安装环境
```

建议：

- `UV_LINK_MODE=copy`。
- BuildKit cache mount 使用 `/root/.cache/uv`，按 OS/ARCH/Python/uv 分离。
- 普通源码改动不能触发第三方依赖重新下载。
- 生产 runtime 不 resolve；可不携带 uv，但必须携带 lock 对应的 `.venv`/site packages。
- 不把宿主 `.venv`、`.env`、data、证书或日志放入 context。

## 运行角色

同一 backend 镜像分角色运行：

- `api`：Gunicorn/Django。
- `worker`：Dramatiq。
- `migrate`：一次性迁移。
- `bootstrap-runtime`、`configure-judge-token`、`create-initial-admin`：一次性命令。

不恢复 Supervisor 同时托管 API/Worker。

## 计划命令

```bash
docker buildx build --file backend/Dockerfile --target runtime \
  --tag xju-oj/backend:<git-sha> .
docker run --rm xju-oj/backend:<git-sha> \
  uv run --locked --no-sync python manage.py check

docker compose run --rm backend-migrate \
  uv run --locked --no-sync python manage.py showmigrations --plan
```

生产命令必须通过最终 `deploy.sh` 编排；本 Step 不执行真实数据迁移。

## 验收

- cold/warm build 指标与 Step 02 可比较；源码-only 改动命中依赖层。
- `api`、`worker`、migrate 角色均能启动并读取同一锁定环境。
- entrypoint 对未知角色非零退出；不会静默 fallback 到 API。
- `runtime_smoke.py --worker` 不要求 API 请求，但检查 DB1/DB4 连接语义。
- 旧 backend 镜像仍可回滚。

## 停止条件

- uv 在运行时联网 resolve 或修改 lock。
- API/Worker 需要不同未锁定依赖集合。
- 镜像层包含 Secret、runtime data 或前端 dist 下载。
- `requirements.txt` 和 pyproject 同时被人工修改，无法确定真源。

## 回滚

恢复旧 Dockerfile/entrypoint 和旧 backend digest；不触碰数据库/Redis。

## 完成标志

提交格式建议：

```text
build(backend): install locked environment with uv
```

完成后再单独评估 Alpine→Debian slim。
