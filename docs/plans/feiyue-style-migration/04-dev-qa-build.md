# 04 · 开发态回归与构建验收

## 目标

在现有 `./deploy.sh --dev frontend` 开发桥接上完成视觉回归，确认双入口构建、路由合同和前端静态产物没有被样式改造破坏。

## 开发流程

优先使用已经运行的：

```text
http://127.0.0.1:5173/
```

如果需要隔离端口，只启动前端 Vite，不重建/重启 PostgreSQL、Redis、backend-worker 或 judge-server。所有 API 继续使用相对 `/api`，不把测试地址写入源码。

## 页面矩阵

### 用户端

- `/`：Upcoming Contests、Problems Set 热门题目、窄栏 Notice Board、footer。
- `/problem` 与 `/problem/:problemID`：筛选、题目阅读、代码编辑、验证码、提交按钮全状态。
- `/contest` 与详情：卡片/表格、状态标签、子导航、排行榜。
- `/status` 与详情：表格 hover、结果色、分页、分享/弹窗。
- `/acm-rank`、`/oi-rank`：表格、空状态、下载按钮。
- `/login`、注册/找回密码、`/user-home`、`/setting/*`：表单、提示和 modal。
- `/about`、`/faq`、公告列表/详情：Markdown/prose、链接和返回操作。

### 管理端

- `/admin/`、`/admin/login`、Dashboard。
- Problem/Contest 列表、创建/编辑、导入导出。
- User、Announcement、Conf、JudgeServer、PruneTestCase。

## 自动检查

每个阶段至少执行：

```bash
cd frontend
pnpm run lint:modern
pnpm run test:routes
pnpm run build
```

涉及部署脚本或入口时额外执行：

```bash
sh -n deploy.sh
git diff --check
```

构建验收确认：

- `frontend/dist/index.html` 存在。
- `frontend/dist/admin/index.html` 存在。
- `/runtime-config.js`、`/static/`、`/public/` 路径合同不变。
- 不提交 `frontend/dist`、`frontend/node_modules`、截图临时文件或运行时 Secret。

## 视觉检查清单

- 白底检查：html/body/#app、用户端主内容、admin 工作区都不是 `#eee`/深蓝大底。
- 低浮动检查：Panel/Card/Dialog/Dropdown 只有细边框和轻阴影，没有旧式大阴影或大幅 translate。
- 圆角检查：小控件 6px、普通卡片 8px、弹层 12px；比赛状态标签使用更克制的 6px 小圆角，避免所有元素一刀切同一圆角。
- 动效检查：hover 约 150ms，弹层约 200–220ms，提交 loading/success 不闪烁；reduced-motion 生效。
- 字体检查：衬线标题、UI 文本、代码区域层级稳定；网络字体失败仍可读。
- 图标检查：Lucide 描边粗细和尺寸统一，无新旧图标混用造成的明显跳变。
- 响应式检查：1360px 参考宽度、1200px、900px、760px 和窄屏下导航、卡片、验证码、表格行为合理。

## 基线差异记录

测试失败分为三类记录：

1. 迁移前就存在的失败：保留命令和错误摘要，不标记为样式回归。
2. 由选择器/主题引入的失败：回退局部规则，补更具体的作用域。
3. 由依赖/环境/API 引入的失败：不通过改视觉代码掩盖，记录环境和复现路由。

本轮结果：

- `pnpm run lint:modern`：通过。
- `pnpm run test:routes`：通过。
- `pnpm run build`：通过，双入口产物生成；仅保留既有 runtime-config 非 module 提示与大 chunk 警告。
- `sh -n deploy.sh`：通过；`git diff --check`：通过。
- 5173 路由 curl 均返回 200；Chrome headless 截图覆盖关键用户端页面与 `/admin/login` 直接加载的 admin login。无后端数据时显示预期空状态/鉴权页。
- 主页二次视觉复核：Header 菜单与搜索框无竖线、无横向滚动，Home/Problems 图标与文字对齐；主体为左栏上下排列 Upcoming Contests/Problems Set，右侧窄 Notice Board（截图记录：`/tmp/xju-home-final.png`、`/tmp/xju-home-final-760-current.png`）。
- 导航细节复核：Rank/About 下拉标题与 Status 同一 36px 高度，激活灰框不撑满 Header，Status→Rank 与 Rank→About 内容间距一致（截图记录：`/tmp/xju-nav-spacing-final.png`）。
- ACM Rank 回归修复：为 `vue-echarts@8` 注册 ECharts renderer，并通过兼容包装层保留旧版 `showLoading`/`hideLoading`/`resize` ref 调用；从 `/acm-rank` 点击 Home、Problems、Contests、Status 均可无刷新跳转。
- Rank 页面复核：`/acm-rank`、`/oi-rank` 改为左上角 `ACM Ranklist`/`OI Ranklist` 标题加直接表格，不再包裹圆角大卡片；后端返回空列表时展示 6 个本地虚拟用户排名。
- 开发 fixtures：后端无种子数据时 `/`、`/problem`、`/contest` 和首页显示两道正式题目（1001 Integer Addition、1002 Decimal Addition）与 2 场各含两题的 Recent Contests；真实 API 有旧演示行时，开发归一化层仅替换 1001/1002 展示字段并隐藏 1003，生产构建仍使用空 fixtures。截图记录：`/tmp/xju-rank-table-mock.png`、`/tmp/xju-home-mock.png`、`/tmp/xju-problem-mock.png`、`/tmp/xju-contest-mock.png`。
- 当前开发环境的题目页均提供完整描述、输入/输出说明、样例和 starter code；比赛 `101`、`102` 均索引 `1001/1002`，比赛详情的 Problems 区可跳转到对应 contest problem 路由。公共 API 路由、鉴权和提交接口未改动；旧数据库演示行不会被前端带入正式构建。
- 首页最终复核：左栏为 Recent Contests 与 Problems Set，右栏为较窄的 Notice Board 及 User Ranking；`Aug 29` 在 1360px 与 760px 视口计算样式中均为 `white-space: nowrap`。当前截图记录：`/tmp/xju-home-final.png`、`/tmp/xju-home-final-760-current.png`、`/tmp/xju-contest-101-final.png`。
- Problems/Problem 增量复核：筛选工具栏在桌面保持同高对齐，Reset 使用 token 暖灰表面；难度胶囊为统一 58×24px 的 Low 绿、Mid 蓝、High 红；侧栏 tags 为双列胶囊，Pick one 图标/文字间距正常。连续开关 Tags 表格列的列头数量始终为 0/1，不会重复追加；单题 Information 字段可读且尽量单行，编辑器 Reset/Upload 无边框图标 hover 才显示边框，Solarized/Monokai/Material 的代码面板均透明并使用 Nerd Font 回退栈，语法色仍可区分。
- Contests/Status 增量复核：Rule、Status、Keyword 与 Status 页过滤器在桌面同高同列；比赛行使用 Lucide Trophy、粗体左对齐标题，移除星标/题号，OI/ACM 仅保留紫/黄彩色文字；Not Started/Ended/Underway 分别映射绿/蓝/灰，并统一为 6px 小圆角（截图记录：`/tmp/xju-shots/contest-after2.png`、`/tmp/xju-shots/status-after.png`、窄屏 `/tmp/xju-shots/contest-760.png`）。
- Problem 最近提交复核：右上角 Submission 标题、左侧图标和箭头同一行，短分隔线下自动显示最多 5 条倒序提交；匿名/空 API 时显示开发态示例记录，导航标题 hover 使用同一 `bg-hover` token。Sample Input 复制图标保持蓝色 hover，无黑框；CodeMirror 聚焦 outline 为 none，行号背景与编辑区一致，仅保留右侧分隔线。
- 上述题目、比赛及测试点仅存在于当前开发数据库和 judge-server `/data/test_case` 运行时，不进入仓库提交；匿名请求访问 contest problem API 仍遵循原有登录权限，开发态 store 仅为 101/102 的展示详情提供 fixture bridge。
