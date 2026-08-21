# Step 04：Frontend pnpm 锁定

## 目标

只替换前端包管理和运行时声明，先得到可重建的 pnpm lock；Vue、Webpack、UI 和业务代码暂不迁移。

## 进入条件

- Step 01 的浏览器/API/CSRF 基线通过。
- Step 02 已记录 Yarn resolution 和隐式依赖。
- Step 03 的 Node 24 候选可在本地/CI 使用。

## 文件范围

修改：

- `frontend/package.json`
- `frontend/.nvmrc`
- `frontend/yarn.lock`（过渡期保留）

新增：

- `frontend/pnpm-lock.yaml`
- 可选 `frontend/.npmrc`
- `docs/contracts/frontend-package-manager.md`

不改：

- `frontend/src/**`
- `frontend/build/**`
- Webpack 配置和 Nginx

## 依赖决策

- Node 24.x LTS，使用 Step 00 锁定的具体 patch。
- pnpm 11.x，优先报告候选 `11.22.0`；若实施日官方稳定线仍为 `11.21.0`，以版本锁为准。
- Vue 维持 lock 中已核实的 2.7.16。
- 明确把源码直接 import 但 manifest 未声明的 `jquery`、`codemirror` 加入顶层依赖。
- 不使用永久 `shamefully-hoist`；如临时启用，必须有到期 Step 和删除验收。

`package.json` 目标形态：

```json
{
  "packageManager": "pnpm@<locked-version>",
  "engines": {
    "node": ">=24.0.0 <25",
    "pnpm": ">=11 <12"
  }
}
```

## 实施顺序

1. 复制并保存现有 `package.json`/`yarn.lock` 的校验和。
2. 按锁定 Node/pnpm 版本导入 Yarn resolution。
3. 显式补齐隐式依赖，确认 import 来源。
4. 运行 lint、旧 Webpack build 和最小浏览器 smoke。
5. 只在全绿后把 pnpm lock 作为新真源；`yarn.lock` 仍保留到 Step 06。

## 计划命令

```bash
cd frontend
node --version
pnpm --version
pnpm import
pnpm add jquery@<verified-version> codemirror@<verified-version>
pnpm install --frozen-lockfile
pnpm run lint
npm run build
```

如果 `pnpm import` 无法保持旧 resolution，停止并改为逐项审计，不要强制接受大规模传递依赖漂移。脚本名以当前 `package.json` 为准，不能假定存在 `lint`/`build`。

## 验收

- `pnpm-lock.yaml` 可在干净目录使用 `pnpm install --frozen-lockfile`。
- Node/pnpm 版本与 Step 00 一致。
- `pnpm why jquery codemirror` 显示顶层声明，无需 hoist 才能编译的隐式依赖已登记。
- 旧 Webpack 产物、API/CSRF、两个入口和原有 E2E 与迁移前一致。
- `yarn.lock` 尚未删除，能够回到旧包管理器。

## 停止条件

- lock 导致 Vue、Router、Vuex、UI 或 Axios 未经批准改变。
- 必须永久使用 `shamefully-hoist`、修改 API 或改写构建输出路径。
- Node 24 无法构建现有 Webpack 链且没有明确隔离修复。
- 生成的 lock 含未审查的远程 git/tarball 或平台特定恶意脚本。

## 回滚

删除 `pnpm-lock.yaml` 和 packageManager/显式依赖变更，恢复保存的 `package.json`/`yarn.lock`；不删除本地缓存，不改业务源码。

## 完成标志

提交格式建议：

```text
build(frontend): lock dependencies with pnpm 11
```

兼容窗口：继续使用旧 Webpack，最多两个生产发布周期；随后进入 Step 05。
