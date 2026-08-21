# Step 08：Frontend UI 组件迁移

## 目标

在 Vue 3 核心已稳定后，按组件类别迁移 Element UI 2 和 iView 2，保持页面行为、表单校验、分页、上传和权限交互；不处理编辑器持久化格式。

## 进入条件

- Step 07 通过两个 SPA 的核心回归。
- 已有组件使用清单和截图/行为基线。
- 选定单一最终 UI 方案，不同时长期维护 Element Plus 与 View UI Plus 的相同功能。

## 方案门

- 管理端优先 Element Plus 2.14.4 候选。
- 用户端先做 View UI Plus 1.3.24 POC；若维护、主题或行为不达标，统一采用 Element Plus，不保留双 UI 体系。
- POC 只覆盖真实高频组件：Form、Table、Pagination、Dialog/Modal、Upload、Message、Loading、DatePicker。

## 文件范围

- `frontend/src/pages/admin/**/*.vue`
- `frontend/src/pages/oj/**/*.vue`
- UI 注册、主题、变量、图标和样式文件
- 组件测试、Playwright fixture、截图基线

## 批次顺序

1. 基础布局、按钮、消息、Loading。
2. 表单、校验、Select、DatePicker。
3. Table、Pagination、筛选和排序。
4. Dialog/Modal、Upload、图片裁剪。
5. 比赛、题目、用户管理等业务页面。
6. 主题、响应式、无障碍和浏览器差异。

每一批都只替换一个 UI 族，提交后执行完整用户端和管理端 E2E。

## 兼容重点

- `.sync` → `v-model:*` 或显式事件。
- `slot-scope` → `#default`/具名 slot。
- 表单错误展示、分页边界、上传 multipart、进度/失败回调。
- Modal/Dialog 关闭时机、Message/Notification 文案和全局实例。
- 管理端 `/admin/` 下资源路径和权限跳转。

## 计划命令

```bash
cd frontend
pnpm add element-plus@~2.14.4
# View UI Plus 仅在 POC 通过且版本锁确认后加入
pnpm install --frozen-lockfile
pnpm run test:unit
pnpm run test:e2e -- --project=chromium
```

不要用全局搜索替换模板；每个组件类别保留迁移前后行为证据。

## 验收

- 用户端/管理端主要 CRUD、分页、筛选、上传、比赛操作通过。
- 表单校验、错误提示、权限拒绝和 API 失败行为不变。
- 关键页面截图/可访问性没有未解释的回归。
- bundle 大小和首次交互时间在 Step 02 基线阈值内，超阈值需单独记录。
- 最终只有一个主 UI 组件体系，旧 UI 包不再被业务代码引用。

## 停止条件

- UI 组件无法保持上传、表单或分页契约。
- 通过全局 CSS 覆盖破坏另一 SPA 或 `/public`。
- 需要修改后端 API 或数据库数据格式才能迁移。
- POC 结果不稳定却直接扩展到全站。

## 回滚

按 UI 批次回滚 frontend commit/image；不回滚 Vue3 核心或后端。旧 UI 依赖在兼容窗口内保留到所有引用清零。

## 完成标志

提交格式建议：

```text
feat(frontend): migrate UI component surfaces to Vue 3 stack
```

编辑器继续由 Step 09 单独处理。
