# 02 · 双入口壳层、导航与首页

## 目标

将参考图的 Header/hero/网格/页脚节奏映射到 OJ 用户端和管理端，同时保持所有现有路由和权限行为。

## 用户端 Header

修改 `frontend/src/pages/oj/components/NavBar.vue`，保留现有 `handleRoute`、登录/注册判断、用户菜单和 modal 状态，只替换表现层：

- 品牌固定显示 `XJU-OJ`；aria-label、`index.html` title 和可见文案不再写 `Online Judge`。
- 使用白色 sticky header、底部 1px `--color-border`、无重阴影或仅 `--shadow-card`；目标高度约 56px，左右内边距 24px。
- 菜单项使用 `height: 36px`、6–8px 圆角、12px 左右内边距；激活态是 `bg-subtle` + 深色文字，hover 是 `bg-hover` + 深色文字。
- Rank/About 下拉标题与普通菜单项共用 36px 点击区域和同一垂直基线；激活灰框不再撑满 56px Header。
- 下拉标题移除 Element Plus 默认的额外右侧占位，Rank→About 与 Status→Rank 的内容间距保持一致。
- 导航图标逐步替换为 Lucide Vue 组件，常规尺寸 16–18px、stroke 1.75；没有对应图标时优先使用语义相近图标，不保留 Font Awesome/iView 的粗重视觉。
- 搜索框采用白底细边框、Search 图标、32–36px 高度和 240px 左右宽度；窄屏收缩菜单内容但不让 Header 出现横向滚动，不改变搜索提交路由。
- 菜单与搜索框之间不保留竖向分隔线；菜单项图标和文字使用同一 flex 基线并保持 16px 图标盒，避免 Home/Problems 视觉错位。
- 登录/注册使用主按钮 + ghost/outline 次按钮；游客状态使用中性胶囊标签。
- 用户菜单 avatar 保持圆形，菜单弹层使用 8–12px 圆角、轻阴影和 200ms 淡入/上移；菜单文案和 logout 行为不变。

## 用户端 App 与页脚

修改 `frontend/src/pages/oj/App.vue`：

- 用统一内容容器承载 `router-view`，取消 80/160px 的大顶部补偿，改为按 header 高度和页面内边距布局。
- 路由过渡由当前 0.8s 大幅 `fadeInUp` 调整为 180–240ms 的轻淡入/4–8px 上移；reduced-motion 时关闭位移。
- 页脚继续允许显示后端配置的站点提示，但固定补充一行：`Powered by XJU-ICTHub · Version 0.2.0`。
- `0.2.0` 作为产品显示版本常量；构建 commit/runtime config 可继续用于诊断，不覆盖用户看到的起始版本。

## 首页改造

在不新增后端接口的前提下，将 `views/general/Home.vue` 组织成 Feiyue 式信息看板：

1. **主体双栏信息区**：左栏上下排列 **Recent Contests** 与按提交量降序展示的 **Problems Set** 热门题目；右栏为更窄的 **Notice Board**。
2. **即将开始的比赛与公告**：保留现有 contest/announcement API，使用轻卡片和轻列表；日期、时长、规则与标题链接行为不变。
3. 首页不再显示额外 hero 标题或 Quick access 入口，避免信息层级与用户需要的比赛/题库/公告看板冲突。
5. 空状态使用普通弱文字或小提示卡，不再用带重阴影的大面板。

首页每个区块用页面根类隔离，避免影响题目详情和 admin。

## 管理端壳层

修改 `frontend/src/pages/admin/App.vue`、`TopNav.vue`、`SideMenu.vue`、`style.less`：

- body/主工作区改为暖白体系；侧栏可以保留信息密度，但用白色/`bg-subtle` 和细分隔线，不使用深蓝大底。
- 顶栏和 breadcrumb 使用细边框、轻阴影、8px 左右圆角；active/hover 采用 token。
- admin logo 和导航图标统一 Lucide 视觉；权限菜单、router index 和折叠行为不变。
- admin 允许卡片和表格更紧凑，但仍禁用大面积灰色背景和默认厚阴影。

## 验收

- 用户端与 `/admin/` 刷新、激活态、登录/注册弹层、用户下拉、admin 权限菜单均保持原行为。
- 参考图的暖白底、细边框、轻卡片信息流和弱 footer 视觉在首页可见；首页主体聚焦比赛、热门题目与公告。
- 桌面和窄屏没有新增不可接受的横向溢出；固定 header、dialog、dropdown、BackTop z-index 正常。
- 可见品牌和页脚文案分别为 `XJU-OJ`、`Powered by XJU-ICTHub · Version 0.2.0`。

实施结果：用户端 header、搜索、登录/注册/用户菜单、首页比赛/热门题目/公告看板和 footer 已完成；按页面需求移除了 hero 与 Quick Access。首页左栏上下排列 Recent Contests/Problems Set，右栏为窄版 Notice Board，并在公告下方加入 A题数、ACM Rank、OI Rank 三项 User Ranking；日期使用 nowrap 保证 `Aug 29` 等月份日期始终一行。admin 侧栏、顶栏、面包屑、登录页与工作区改为暖白细边框主题。Lucide 图标通过兼容层接入，历史 Icon type 模板无需改动。
