# 2026 现代化迁移执行记录

> 此文件只记录已经实际执行并验证的事实；计划文本、预估结果和“应当通过”不能写成完成事实。

## 全局信息

- 生产宿主：Ubuntu >=22.04；Step 00 实测目标为 Ubuntu 22.04，支持状态仍由 Step 03 preflight 再验收
- Python：3.10.x，Step 00 锁定官方 amd64 基础镜像解释器 `3.10.21` 与 manifest digest
- 当前分支：`main`
- 计划入口：[README.md](README.md)
- 当前 Step：Step 00 已完成，准备 Step 01
- 最近完成 Step：Step 00

## 记录格式

每完成一个 Step，追加一条：

```text
### YYYY-MM-DD — Step NN

- Commit:
- 变更摘要:
- 实际命令:
- 测试/验收结果:
- 镜像与 digest:
- 数据/Redis/queue 证据:
- 已知风险:
- 回滚点:
- 下一步:
```

## 禁止记录

- Secret、密码、Token、私钥、Cookie、Authorization header。
- 完整生产数据库 dump、Redis RDB/AOF、用户上传文件或判题运行数据。
- 未执行的命令结果、未验证的版本或推测性的“已完成”。

### 2026-08-23 — Step 00

- Commit: 本条记录随 `step 00: lock modernization decisions` 独立提交
- 变更摘要: 新增 `docs/contracts/modernization-version-lock.md` 与 `docs/contracts/modernization-compatibility.md`；锁定平台、版本、镜像 digest、兼容合同和停止门。
- 实际命令: 本地核验 `git rev-parse HEAD`、`git status --short --branch`、源依赖声明和当前工具版本；在配置目标 `huawei1` 执行计划中的宿主/容器工具查询；通过 Docker Official Image 元数据和 `docker run` 核验 `python:3.10-slim-bookworm@sha256:7ed92b32353e8d8bd865b5ba811e0315d3999c3b57b1c2df2b504a359d4a1707` 的 amd64 Python `3.10.21`；通过 npm/PyPI 包元数据核验 pnpm 11.22.0、Vite bridge/final、Vue bridge/final、uv 0.12.5 和 Django 5.2.17 候选。
- 测试/验收结果: `huawei1` 为 Ubuntu 22.04、x86_64、cgroup v2、Docker 29.7.1、Compose v5.4.0、Buildx v0.36.0；版本锁已解释 pnpm 11.21/11.22、PG17/18、Redis/Valkey 和 Python 3.10/3.13 冲突；未修改应用代码、旧锁文件或运行数据。
- 镜像与 digest: Python amd64 manifest `sha256:7ed92b32353e8d8bd865b5ba811e0315d3999c3b57b1c2df2b504a359d4a1707`; Node 24.19.0、PostgreSQL 18.6/17.11、Redis 6.2.23/7.4.10/8.2.8、Debian Trixie 的 manifest digest 记录在版本锁中。
- 数据/Redis/queue 证据: 本 Step 未触碰 PostgreSQL、Redis、queue、Secret 或用户数据。
- 已知风险: 当前宿主 Node/pnpm/uv 仍为旧工具版本；Step 03 必须重新执行 Ubuntu/runtime-root/权限/工具链门，后续镜像构建必须使用锁定 digest。
- 回滚点: `d59d274ce3237bb10165fc9afadc4260aa79c359`；本 Step 仅新增文档，错误时回到该提交即可。
- 下一步: Step 01 — 行为合同与特征测试。
