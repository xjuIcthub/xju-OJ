# 03 · 组件、状态、弹层与提交体验

## 目标

把 Feiyue 的卡片、标签、提示、弹窗和内容阅读规则应用到 OJ 高频页面，重点完成题目提交按钮的状态动画；不改任何业务数据流。

## 组件迁移矩阵

| OJ 组件/区域 | 目标表现 | 实施要点 |
| --- | --- | --- |
| `Panel.vue` / Element Card | 白底、细边框、8–12px 圆角、`--shadow-card` | 标题使用 Source Serif 4/Noto Serif SC；避免默认 hover 大幅浮起 |
| Button | primary 深色、outline、ghost、danger 语义明确 | 统一 6–8px 圆角、150ms hover、focus ring、disabled opacity |
| Input/Select/Captcha | 白底、细边框、placeholder muted | focus 只强化边框/ring，不改变尺寸导致抖动 |
| Tag/Badge | 12% tint + 语义色；短状态用胶囊 | 题目难度、比赛规则、AC/WA/pending 使用稳定映射 |
| Alert/提示卡 | 轻表面、左侧语义色或 Lucide 图标 | 成功/警告/错误不使用整块高饱和背景 |
| Modal/Dialog | 8–12px 圆角、低阴影、暗化但不过黑的 overlay | 200–220ms fade + 4px 上移；关闭、Esc、焦点管理保持 Element Plus |
| Tooltip/Popover/Dropdown | 细边框、白底、轻阴影、短延迟 | 不遮挡提交区和固定 header；teleport 到 body 时检查 z-index |
| Table/Pagination | 浅表头、行 hover、细分隔线、薄滚动条 | 保留排序、分页、AC/WA 颜色和固定列语义 |
| Markdown/代码 | prose-claude 标题、引用、表格、code block | 适配 OJ DOM；KaTeX、highlight、复制和编辑器主题优先 |

## Lucide 适配策略

当前 `package.json` 没有 Vue 版 Lucide。实施时：

1. 增加与 `xju-feiyue` 风格兼容的 `lucide-vue-next` 锁定版本，并通过 `pnpm-lock.yaml` 固定。
2. 新增轻量 `shared/ui/Icon.vue` 或 `icon-map.js`，将历史 `Icon type="home|trophy|..."` 映射到 Lucide 组件，未知 type 使用中性 fallback。
3. 首批替换 NavBar、首页快捷入口、Problem submit/status、admin 顶栏/侧栏；后续页面按访问频率逐步替换。
4. 不为了图标迁移重写旧模板的事件、slot 或 route 参数；图标尺寸和 stroke 由适配层统一。

## 提交按钮专门方案

修改 `frontend/src/pages/oj/views/problem/Problem.vue`，保留 `submitCode`、`submitting`、`submitted`、验证码和禁用条件：

### 默认

- 使用 `oj-submit-button` 样式，主色为 `--color-text`，文字白色；圆角 8px，最小高度 40px，图标使用 Lucide `Send/Rocket` 一类的线性图标。
- 文字保持国际化 `$t('m.Submit')`；不把业务状态写死在 CSS。

### hover / active / focus

- hover 仅加深背景、轻微提升 border contrast 和 1px 以内阴影；active `transform: scale(.98)`，focus 使用可见 ring。
- 动效通道拆开：颜色/边框 150ms，transform 180ms，避免 hover 时文字或布局抖动。

### loading

- 禁用重复提交；Lucide `LoaderCircle` 旋转 800–1000ms 一周，文字切换为 `$t('m.Submitting')`。
- 可使用一次性极淡的 sheen，但不持续闪烁、不影响 reduced-motion；reduced-motion 只保留静态 loading 图标或文字。

### success / error / disabled

- 成功由现有 Alert/Message 负责，按钮恢复到可提交或按现有 `submitted` 逻辑禁用；如增加 check 动画，必须是一次性 180–240ms 并可关闭。
- 禁用态降低透明度和对比度，不改变尺寸；错误提示靠现有 Alert/Message，不用红色大面积按钮覆盖页面。
- 验证码图片与输入框和按钮在同一 flex 行中对齐，窄屏可换行。

## 页面覆盖顺序

1. Problem 详情/提交区。
2. Login/Register/ResetPassword/Settings 表单和弹层。
3. Contest、Submission、Rank 表格/标签/分页。
4. UserHome、About、FAQ、Announcements。
5. admin Dashboard、Problem/Contest/User/Conf/Announcement 表单和表格。

## 验收

- 所有高频状态都能从 token 追踪到颜色；没有新增硬编码灰色/蓝色/橙色散点。
- 提交按钮默认、hover、active、focus、loading、success、disabled 逐项手测，并验证重复点击不会改变原有提交逻辑。
- 弹层、提示卡和下拉菜单在固定 header/admin 侧栏之上显示，Esc/点击遮罩/返回行为不变。
- Markdown、公式、代码复制、编辑器输入输出和表格横向滚动不回归。

实施结果：Element Plus Card/Button/Input/Dialog/Dropdown/Table/Pagination/Alert/Tag 统一主题；Problem 列表筛选器改为同高 flex 工具栏，Reset 使用 token 暖灰 ghost 样式，Low/Mid/High 使用固定宽度的绿/蓝/红小圆角胶囊，Tags 侧栏改为双列 tag cloud，Pick one 图标与文字留出间距；Tags 表格列由受控开关管理，重复切换不会追加重复列，点击已选 tag 可取消筛选。Problem 详情的 Information 标题与字段对齐加粗，内联 code 改为更浅背景/更小圆角，Sample Input 复制按钮保持同一行高且 hover 保持蓝色，编辑器 Reset/Upload 改为 hover 才显边框的图标按钮，Solarized/Monokai/Material 保留各自语法色与选区反馈，但代码面板和行号区统一透明、继承页面白底；代码字体使用 JetBrains Mono/Fira Code Nerd Font 等回退栈。CodeMirror 行号区与编辑区同色，仅保留分隔线，聚焦时取消虚线外框。Problem 详情右栏增加常驻 Submission 标题和短分隔线，按时间倒序展示最多 5 条最近提交，API 无数据时使用开发态示例记录；标题 hover 与导航栏一致。Problem 提交按钮加入 Send、LoaderCircle、Check 图标，防重复提交、loading、success、disabled、focus/active/hover 与验证码窄屏换行样式，`submitCode` 与 payload/API 未改动。Contest 列表筛选器、Lucide 比赛图标、规则彩色字、状态小圆角标签和 Status 页筛选器共用同一套 Feiyue filter-control 视觉。
