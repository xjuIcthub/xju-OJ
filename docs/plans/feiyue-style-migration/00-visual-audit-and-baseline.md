# 00 · 视觉审计与行为基线

## 目标

把参考图、xju-feiyue 实现和 xju-OJ 当前实现转换成可执行的视觉合同。此阶段只记录基线和映射，不修改业务行为。

## 审计结果

### 参考图分区

| 区域 | 观察 | OJ 对应落点 |
| --- | --- | --- |
| Header | 白底、细底线、窄高度；当前导航暖灰底，普通项 hover 才显色 | `oj/components/NavBar.vue`、admin `TopNav/SideMenu` |
| Brand | 图标 + `Feiyue`，UI 字体/衬线混用 | 固定显示 `XJU-OJ`，保留站点配置只用于非品牌文案 |
| Hero | 小号 eyebrow + 大号衬线标题 + muted 描述 + 分隔线 | OJ 首页增加欢迎/说明区，不调用新后端接口 |
| 快捷网格 | 4×2 轻卡片，彩色图标底，描述截断，最后一格为全量入口 | 映射为题库、比赛、状态、排行榜、公告、帮助等现有路由 |
| 内容流 | 热门/最新标题和右侧链接，卡片白底细边框 | 映射 upcoming contests、announcements、problem/status 摘要 |
| Footer | 低存在感、细线、弱文字 | 固定 `Powered by XJU-ICTHub · Version 0.2.0` |

### Feiyue 源码结论

- `tokens.css` 是完整语义色源，包含 surface/text/line/link、七类颜色、12% tag tint、6/8/12px radius、轻阴影、150ms 过渡和字体栈。
- `globals.css` 负责字体导入、reset、body 基础字阶、焦点/插入符和 reduced-motion；其中 `@tailwind` 与 shadcn HSL bridge 不适合直接放入 OJ 的 Less/Element Plus 运行时。
- `Header.tsx` 的关键尺寸是约 56px header、24px 左右内边距、36px nav item、32px avatar、240px 左右搜索框；激活项使用 `bg-subtle`，不是厚重底色。
- `CategoryGrid.tsx` 与 `NoteCard.tsx` 采用 `border + bg + hover:bg-subtle`，不依赖大面积投影或 translate 浮起。
- `prose-claude.css` 证明正文标题用 Source Serif 4/Noto Serif SC，代码用 JetBrains Mono，表格和 code block 也使用浅色表面和细线。

### OJ 当前基线结论

- `src/styles/common.less` 将 `html/body` 设为 `#eee`，`App.vue` 通过 80/160px 顶部间距补偿固定导航。
- `NavBar.vue` 固定 64px 左右导航并使用旧 `Icon type` 与较重 box-shadow；登录、注册、用户下拉仍是 Element Plus 旧风格。
- `views/general/Home.vue` 只展示 contest Carousel 与 announcements Panel；无法直接形成参考图的分区节奏。
- `views/problem/Problem.vue` 的 `#submit-code` 是普通 Card，submit 使用 `warning` + `edit`，loading 只有按钮文字替换。
- admin `App.vue`/`SideMenu.vue` 默认深色底和固定侧栏；需要主题化，但不能破坏 admin 路由和权限菜单。

## 页面 → 目标规则 → 影响文件

| 页面/组件 | 目标规则 | 主要文件 |
| --- | --- | --- |
| 用户端壳层 | 白底、细底线、低阴影、内容 max-width 和 footer | `oj/App.vue`、`NavBar.vue`、`styles/common.less` |
| 首页 | hero + 快捷入口网格 + 比赛/公告轻卡片 | `views/general/Home.vue`、`Announcements.vue` |
| Panel/Card | 6/8/12px 半径、细边框、轻阴影、标题衬线化 | `oj/components/Panel.vue`、Element Plus theme |
| Problem | 阅读区 prose、信息侧栏、提交区状态和按钮动画 | `views/problem/Problem.vue`、`CodeMirror.vue` |
| Contest/Status/Rank | 表头、行 hover、状态标签和分页统一 | 对应 `views/contest/**`、`submission/**`、`rank/**` |
| Login/Register/Settings | 表单、提示卡和弹窗统一 | `views/user/**`、`views/setting/**` |
| Admin | 暖白内容、轻侧栏/顶栏、密度稍高但不重浮动 | `pages/admin/App.vue`、`TopNav.vue`、`SideMenu.vue`、`style.less` |

## 基线执行

在开始阶段 01 前记录以下结果。当前用户已经启动 `./deploy.sh --dev frontend`，优先复用 `http://127.0.0.1:5173/`，不要重复启动生产服务。

```bash
cd frontend
pnpm run lint:modern
pnpm run test:routes
pnpm run build
```

本轮已执行的自动基线结果：

- `pnpm run lint:modern`：通过（`frontend modern stack scan passed`）。
- `pnpm run test:routes`：通过（`frontend route contract manifest passed`）。
- `pnpm run build`：通过，生成用户端和 admin 双入口；Vite 仅报告已有的 runtime-config module 提示和大 chunk 警告。
- `git diff --check` 与计划文档空白检查：通过。

浏览器/交互基线已补记：使用 Chrome headless 在 5173 检查 `/`、`/problem/1000`、`/contest`、`/status`、`/acm-rank`、`/oi-rank`、`/login`、`/about`、`/faq`、`/setting/profile` 与 `/admin/`。后端 API 空数据/未鉴权状态以空状态或登录页呈现，未发现样式运行时错误。

开发服务器增加了 admin history fallback；直接请求 `/admin/login` 与从 `/admin/` 进入 history 路由现在均渲染 admin login，生产双入口构建合同不变。

浏览器/手工记录：

- `/`、`/problem`、`/contest`、`/status`、`/acm-rank`、`/oi-rank`
- `/login`、注册/找回密码、`/user-home`、`/setting/profile`
- `/admin/`、`/admin/login`、问题列表、比赛列表、用户/公告配置
- 导航激活态、用户下拉、登录弹窗、表格 hover、分页、返回顶部、窄屏横向溢出
- `prefers-reduced-motion: reduce` 下的路由切换、Carousel、弹窗和提交按钮

若后端未运行导致 API 代理失败，只记录为环境状态；不能把它归因于本轮视觉改造。

## 风险与停止条件

- 发现 API、路由、权限、CSRF、提交 payload 或编辑器事件在改 CSS 时发生变化：停止并拆出兼容修复。
- `global.css` 的 Tailwind 指令在当前构建链中产生解析问题：保留令牌和安全 reset，移除 Tailwind/shadcn 专属指令，不引入 Tailwind 运行时。
- 参考图与 OJ 业务信息密度冲突时，优先保证判题/表格可读性，再使用 Feiyue 的颜色、间距和动效语言。
