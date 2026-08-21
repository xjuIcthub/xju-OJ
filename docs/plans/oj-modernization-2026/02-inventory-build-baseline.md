# Step 02：现状盘点与构建基线

## 目标

记录依赖、源码、数据、容器、构建耗时和缓存流量，后续才能判断迁移是否减少重复下载、是否改变了运行行为。

## 进入条件

- Step 00 版本锁已确定候选。
- Step 01 合同测试资产已存在。
- 只在本地或隔离 staging 执行；不读取或打印生产 Secret。

## 盘点范围

### Frontend

- `package.json`、`yarn.lock`、`.nvmrc`、Webpack/Babel/DLL 配置。
- 两个真实入口、Router history、Axios API/CSRF、隐式 `jquery`/`codemirror`。
- `.native`、`.sync`、`slot-scope`、filters、`new Vue`、`Vue.prototype`、`Vue.util`。
- Element UI、iView、ECharts、CodeMirror、Simditor、Sentry、analytics、moment。
- 当前 `frontend/nginx/nginx.conf` 与旧 `frontend/deploy/nginx.conf` 的差异。

### Backend

- `backend/deploy/requirements.txt`、Dockerfile、entrypoint、settings、CI。
- 所有 URLConf 中的 `django.conf.urls.url`。
- 当前/历史 JSONField import、migration graph、第三方 legacy imports。
- API、Session/CSRF、Redis DB1/DB4、Dramatiq actor 和 task 状态。

### Server

- `server/judge-server/Dockerfile` 的 build context、COPY 路径、Python 依赖。
- `server/judger` CMake、binding、UID/GID、Seccomp 规则、测试 corpus。
- 当前语言版本、编译/运行/资源限制和健康检查语义。

### 部署和数据

- 根 Compose 远程镜像、端口、网络、卷、healthcheck。
- PostgreSQL/Redis 镜像和数据目录布局。
- runtime/public/test_case/judger/log 的路径、所有权、容量和备份位置。

## 构建指标

至少记录：

- cold build、warm build、源码-only 修改、lockfile 修改、基础镜像修改的时间。
- npm/PyPI/apt 下载字节和次数。
- 镜像大小、层数、昂贵 build vertex 命中率。
- Judger C 编译时间和工具链安装时间。
- 多架构构建是否使用 QEMU/native builder。
- 当前部署镜像 tag/digest（只记录标识，不记录 Secret）。

## 计划命令

```bash
set -eu
find frontend backend server -type f -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' | sort > /tmp/xju-oj-source-files.txt

git ls-files > /tmp/xju-oj-tracked-files.txt
find docs/research -maxdepth 1 -type f -print | sort

du -sh frontend backend server 2>/dev/null || true

git diff --check
```

构建指标通过 BuildKit/buildx metadata 或 CI 日志采集；日志中禁止显示环境变量值和 Secret 文件内容。

## 产出

建议新增（内容脱敏）：

- `docs/contracts/source-inventory.md`
- `docs/contracts/dependency-inventory.md`
- `docs/contracts/build-baseline.md`
- `docs/contracts/runtime-volume-inventory.md`
- `docs/plans/oj-modernization-2026/execution-log.md`

## 验收

- 目录、依赖、入口、数据卷和镜像来源有清单。
- 每个现有构建命令都能追溯到文件和版本。
- 至少有一次 cold/warm 基线；后续 Step 可以比较。
- 生产数据和凭据没有进入临时文件、Git 或日志。

## 停止条件

- 构建依赖下载到不可审计的远程压缩包或浮动 URL。
- 无法区分源码层和依赖层，无法测量缓存收益。
- 发现当前 Compose 使用的镜像与本地源码不一致但没有记录 digest。
- 数据卷、test_case、public 或 Judger 的实际路径/权限不明。

## 回滚

本 Step 只写脱敏清单和指标；删除错误清单即可，不触碰运行数据。

## 完成标志

提交格式建议：

```text
docs: record modernization inventory and build baseline
```

Step 03 可并行开始；Frontend/Backend/Server 的改造必须以本 Step 清单为输入。
