# Step 13：Backend Python 3.10 基础镜像

## 目标

在 uv 安装器稳定后，评估并切换 backend 的容器基础镜像，仍固定 Python 3.10；本 Step 不升级 Django、Redis、数据库驱动或 Worker。

## 进入条件

- Step 12 的 locked uv 镜像通过。
- Step 02 已有 Alpine cold/warm 构建、镜像大小和 native wheel 指标。
- Python3.10 micro、OpenSSL、libpq、Pillow 等 native 依赖可在候选镜像中验证。

## 选择门

优先候选：

- `python:3.10-slim-bookworm`，具体 patch + digest。
- 若组织要求容器也使用 Ubuntu，则另做 Ubuntu `>=22.04` 的等价镜像；不能把宿主约束误当成容器约束。

不以“换 Debian”自动获批；必须比较：

- psycopg/Pillow/C 扩展 wheel 命中率。
- SSL、时区、locale、字体、图像处理行为。
- 镜像大小、CVE、启动时间、构建速度。
- amd64/arm64 可重建性。

## 文件范围

- `backend/Dockerfile`
- `.dockerignore`
- 必要的系统包清单/版本锁
- `docs/contracts/backend-runtime.md`
- CI 构建矩阵

## 实施顺序

1. 使用相同 pyproject/uv.lock 构建候选 image。
2. 在候选 image 运行 Django check、全量测试、图片 golden、邮件/OTP、Redis smoke。
3. 对比现有 Alpine image 的 API、Worker、migrate 和运行时行为。
4. 仅切换基础 image；保留旧 image 作为回滚候选。
5. 把基础 image digest 写入版本锁和镜像 metadata。

## 计划命令

```bash
docker buildx build --file backend/Dockerfile \
  --build-arg BASE_IMAGE=python:3.10-slim-bookworm@sha256:<verified> \
  --tag xju-oj/backend-py310-slim:<git-sha> .
docker run --rm xju-oj/backend-py310-slim:<git-sha> \
  uv run --locked --no-sync python manage.py check
```

不要把真实 registry 凭据或 digest 以外的秘密放入命令记录。

## 验收

- Python 精确版本仍为 3.10.x。
- 所有已有测试、migration dry-run、API/Session/CSRF、Pillow、邮件和 Worker smoke 通过。
- 依赖安装无未锁定下载；CVE、SBOM 和来源可追溯。
- 镜像回滚不需要 schema 或数据操作。

## 停止条件

- 候选镜像必须放宽权限、改变文件所有权或修改业务代码才能运行。
- native wheel/locale/时区/图片行为出现无法解释差异。
- 只能依赖 `latest` 或未验证的 tag。
- 无法取得受维护且可锁 digest 的 Python3.10 基础镜像。

## 回滚

Compose/CI 恢复上一 Python3.10 基础镜像 digest；不回退 pyproject/lock 的业务升级。

## 完成标志

提交格式建议：

```text
build(backend): pin Python 3.10 runtime base image
```

之后进入 Django 兼容债务清理。
