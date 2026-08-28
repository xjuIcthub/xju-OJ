# XJU-OJ · xju-feiyue 风格迁移主计划

## 1. 目标

把 `../xju-feiyue/frontend` 的视觉语言迁移到本仓库的 Vue 3 + Element Plus 前端。迁移对象是设计系统和交互表现，不是 React 组件、React Router、业务页面或 Tailwind 运行时。

最终用户端和管理端都应呈现同一套低浮动、暖白、细边框风格：

- 页面主背景为白色，不再使用 OJ 当前的灰色大底和重浮动面板。
- 品牌显示为 `XJU-OJ`，不再显示 `Online Judge`。
- 页脚固定显示 `Powered by XJU-ICTHub · Version 0.2.0`。
- 导航、卡片、标签、提示、弹窗和提交按钮使用统一的颜色、圆角、hover 与动效节奏。
- 图标优先使用 Lucide 风格（1.75px 左右描边、16–18px 常规尺寸），业务行为保持不变。

## 2. 已完成的设计分析

### 2.1 参考图的视觉结构

参考图 `[Image #1]`（仓库内副本：[refer-images/主页.png](../../../refer-images/主页.png)）呈现的是：

1. 顶部窄导航：白底、底部 1px 细线、无明显投影；当前项用暖灰色圆角矩形承载，普通项只在 hover 时出现浅底色。
2. 品牌和导航使用无衬线 UI 字体，正文大标题使用中文衬线字体，形成“工具界面 + 杂志标题”的层次。
3. 内容区采用约 1200px 的居中宽度，四列两行的轻卡片网格；卡片白底、细边框、圆角适中，不做大面积阴影或悬浮位移。
4. 每类内容有一枚彩色图标底和胶囊/圆角标签，颜色只承担分类和状态语义，不铺满页面。
5. “本周热门”“最新发布”等区块通过衬线小标题、右侧文字链接和轻量卡片组织信息；空状态是普通文本或提示卡，不是巨型占位面板。
6. 卡片 hover 以 `background`、`border-color`、文字/图标颜色变化为主，过渡短而克制；弹层才使用约 200ms 的位移和透明度动画。

### 2.2 xju-feiyue 实际实现的可迁移规则

已检查的来源：

- `../xju-feiyue/frontend/src/styles/tokens.css`
- `../xju-feiyue/frontend/src/styles/globals.css`
- `../xju-feiyue/frontend/src/styles/prose-claude.css`
- `../xju-feiyue/frontend/src/components/layout/Header.tsx`
- `../xju-feiyue/frontend/src/components/layout/Footer.tsx`
- `../xju-feiyue/frontend/src/components/layout/AppShell.tsx`
- `../xju-feiyue/frontend/src/features/home/sections/*`
- `../xju-feiyue/frontend/src/components/common/NoteCard.tsx`
- `../xju-feiyue/archive/design-refs/stylesheets/styles.css`

确认的参数：

| 维度 | Feiyue 规则 | OJ 迁移策略 |
| --- | --- | --- |
| 表面 | `#fff`、`#f7f6f3`、`#f1f1ef` | `body`/主内容只用白底；subtle 仅用于 hover、输入框、侧提示和次级区域 |
| 文字 | `#37352f`、`#787774`、`#9b9a97` | 统一映射正文、次要文字、弱提示 |
| 边框 | `#edece9`、`#dcdad4` | 组件默认细线；禁用深灰粗边框 |
| 链接 | `#2383e2` | 统一链接、更多、可点击状态 |
| 类别色 | research/course/recommend/competition/kaggle/tools/life 七色及 12% tint | 映射题目难度、比赛状态、结果状态和功能标签，不改变业务含义 |
| 圆角 | 6/8/12px；标签按语义使用胶囊圆角 | 小控件 6px、普通卡片 8px、弹层/大容器 12px，状态标签可用 9999px |
| 阴影 | `0 1px 2px rgba(0,0,0,.04)` | 仅保留低浮动卡片阴影；导航和主内容不使用重阴影 |
| 动效 | 默认 `150ms ease`，菜单/卡片约 200–220ms | 提交按钮单独定义 hover/active/loading/success 状态，尊重 reduced-motion |
| 字体 | Inter Tight、Source Serif 4、Noto Serif SC、JetBrains Mono | 网络字体失败时保留 PingFang/系统/Georgia/Menlo 等 fallback |
| 图标 | Lucide，常规 16–18px，约 1.75px 描边 | 增加 Vue 图标适配层，逐页替换旧 `Icon type`，不一次性破坏历史模板 |

### 2.3 OJ 当前基线与主要问题

已检查的来源：

- 用户端壳层：`frontend/src/pages/oj/App.vue`、`components/NavBar.vue`、`components/Panel.vue`
- 用户端首页：`views/general/Home.vue`、`views/general/Announcements.vue`
- 判题提交区：`views/problem/Problem.vue`
- 全局样式：`src/styles/common.less`、`index.less`、`iview-custom.less`、`markdown.less`
- 管理端壳层：`pages/admin/App.vue`、`components/TopNav.vue`、`components/SideMenu.vue`、`style.less`

当前主要问题：

- 用户端 `body/html` 使用 `#eee`，管理端使用深色 `#324157`，与参考图白底冲突。
- 用户端导航高度较大且有 `0 1px 5px` 阴影；旧 iView 图标类名无法提供一致的 Lucide 质感。
- 首页是单个带阴影的 contest `Panel`，缺少参考图式的 hero、快捷入口网格和轻量信息区块。
- `Panel`/Element Plus Card、表格、弹窗和按钮存在分散硬编码，圆角和阴影不统一。
- 题目提交按钮使用 warning 橙色和旧 `edit` 图标，loading/success 只有文字状态，缺少清晰的交互反馈。
- 页脚仍显示 `OnlineJudge` 链接，版本直接取构建 commit，不能满足产品名和 `0.2.0` 起始版本要求。

### 2.4 迁移边界

保留不变：API endpoint、请求参数和响应包装、路由 name/path、鉴权/CSRF、Element Plus/Vue Router/Pinia、CodeMirror/Tiptap/KaTeX/Highlight.js、ECharts 数据和双入口构建。

不直接迁移：React/TSX 组件、TanStack Query、Radix/shadcn、Tailwind utilities、Feiyue 的笔记业务模型和与 OJ 无关的 demo。

## 3. 阶段索引

按 `00 → 01 → 02 → 03 → 04 → 05` 执行。每个阶段先小范围落地、通过检查，再扩大选择器作用域。

| 阶段 | 文档 | 主要产出 | 状态 |
| --- | --- | --- | --- |
| 00 | [视觉审计与行为基线](./00-visual-audit-and-baseline.md) | 参考图/源代码审计、页面映射、基线截图与风险清单 | 已完成：自动基线与 5173 路由截图记录 |
| 01 | [设计令牌与全局基础样式](./01-design-tokens-and-global.md) | `tokens.css`、全局字体/背景/reset、Element Plus 主题桥接 | 已完成 |
| 02 | [双入口壳层、导航与首页](./02-shell-navigation-home.md) | 用户端/管理端壳层、XJU-OJ 品牌、页脚、首页结构、Lucide 导航 | 已完成 |
| 03 | [组件、状态、弹层与提交体验](./03-components-states-submit.md) | Panel/Card/Form/Table/Tag/Alert/Dialog、编辑器外围、提交按钮状态动画 | 已完成 |
| 04 | [开发态回归与构建验收](./04-dev-qa-build.md) | 5173 联调、关键路由烟测、响应式/动效检查、构建产物 | 已完成：lint/routes/build/diff-check 通过 |
| 05 | [提交拆分与回滚](./05-delivery-and-rollback.md) | 可审查提交序列、回滚点、合并前清单 | 已完成：保留用户工作区改动，未执行提交/push |

## 4. 执行门禁

- 每阶段只改与本阶段相关的前端文件；不覆盖当前工作区已有的后端、部署或运行时改动。
- 不把 `.env`、Cookie、OIDC 密钥、judge token、用户数据或构建产物写入提交。
- 全局规则必须通过 CSS 变量消费；页面特殊规则用组件作用域或页面根类隔离。
- 若视觉改动引入路由/API/编辑器行为差异，立即停止扩大范围，回退当前阶段提交并先修兼容层。
- “无灰色背景”是主视觉硬门禁；`--color-bg-subtle` 只能出现在 hover、次级区域、输入框或有明确语义的提示表面。

## 5. 总体验收标准

### 视觉

- `/`、`/problem`、`/contest`、`/status`、`/acm-rank`、`/oi-rank`、登录/注册、个人设置和 `/admin/` 使用统一暖白色板。
- 导航激活态、hover、搜索框、用户菜单、按钮、标签、提示卡片和弹窗与参考图的细边框/低浮动质感一致。
- 标题/正文/代码字体层次清楚；中文长标题、表格和代码块不溢出。
- 提交按钮在默认、hover、active、loading、成功、禁用状态均有稳定反馈；`prefers-reduced-motion` 下不持续播放动画。

### 行为与工程

- 路由、权限、API、Session/CSRF、提交 payload、编辑器 value/change 合同不变。
- `pnpm run lint:modern`、`pnpm run test:routes`、`pnpm run build` 通过；必要时另跑 `sh -n deploy.sh`。
- 双入口 `dist/index.html` 与 `dist/admin/index.html` 均生成，未提交 `dist/` 或 `node_modules/`。

## 6. 本轮计划状态

本轮已完成视觉迁移和本地演示数据验收。新增 Feiyue 令牌/全局样式、Element Plus 主题映射、Lucide 兼容层、用户端与 admin 壳层、首页信息看板和 Problem 提交状态样式；Rank 页面使用无卡片直出表格。题目、比赛和虚拟用户 fixtures 现在只在 `OJ_FRONTEND_DEV_MODE=true` 且通过 Vite development 模式启动时进入前端依赖图，正式构建改用空 fixtures 模块。开发态展示两道正式题目 1001/1002（均含完整题面、样例和 starter code），比赛 101/102 均索引 1001/1002；旧演示 API 行仅在开发归一化层中替换或隐藏，不进入生产构建。首页右栏 Notice Board 下方增加 User Ranking，Recent Contests 日期强制单行显示。已在 5173 对关键路由执行 Chrome headless 截图烟测。`lint:modern`、`test:routes`、`build`、`git diff --check` 与 `sh -n deploy.sh` 均通过。额外补上了只作用于 Vite dev server 的 admin history fallback，直接访问 `/admin/login` 现可加载 admin 入口。

本地数据库中可能仍保留旧演示题目行；前端开发归一化层会将 1001/1002 映射到正式题面并隐藏 1003，未写入删除性数据迁移。`/data/test_case` 测试点属于开发环境运行时数据，不写入仓库迁移文件，也不会改变生产 API、路由或鉴权合同。

## 7. 2026-08-27 跟进修复计划与结果

| 顺序 | 修复项 | 实施结果 |
| --- | --- | --- |
| 1 | 全局布局与中文文案 | 导航和内容统一使用 1400px 上限及 20px gutter；首页、比赛、题目、排名与设置页补齐三语文案，简体难度统一为“简单/中等/困难” |
| 2 | Status 结果展示 | 判题状态改为 Feiyue 语义胶囊，表格列宽和 cell padding 收紧；Pending/Judging/Submitting 存在时静默轮询并在完成后自动停止 |
| 3 | Contests/Problems/Problem | 比赛筛选与状态胶囊继续统一；题名左对齐、侧栏 tag 按内容自适应；题目详情的最近提交区域取消 hover 变色并补齐中文空状态 |
| 4 | 头像上传 | 裁剪结果在浏览器压缩为 WebP，再调用原头像上传端点；成功后重新读取 profile，后端仅扩展 WebP 后缀白名单 |
| 5 | 开发/生产隔离 | 新增 `OJ_FRONTEND_DEV_MODE`；生产禁止开启并使用空 fixtures，开发开启时关闭 OIDC 跳转、启用本地登录并提供 admin 快速登录 |
| 6 | 个人资料与设置 | 个人资料新增真实姓名/学号必填校验与后端 `student_id` 字段迁移；账号设置菜单隐藏，安全页 Current 使用 Feiyue 胶囊；头像继续保持 WebP 自动上传 |
| 7 | 验证 | `sh -n deploy.sh`、`lint:modern`、`test:routes`、production build、`git diff --check` 通过；production dist 未检出开发 fixture 标识字符串 |

本次没有改变题目、比赛、提交或用户 API 的路径/请求字段，没有修改路由表、CSRF/Session 合同、提交 payload 或 CodeMirror 编辑行为。头像接口只增加 `.webp` 文件格式支持。
