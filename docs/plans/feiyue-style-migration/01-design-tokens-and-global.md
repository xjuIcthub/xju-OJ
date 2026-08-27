# 01 · 设计令牌与全局基础样式

## 目标

先建立单一视觉色源，再让用户端、管理端和 Element Plus 组件消费它。此阶段不重写页面业务模板。

## 文件策略

| Feiyue 来源 | OJ 目标 | 处理方式 |
| --- | --- | --- |
| `frontend/src/styles/tokens.css` | `frontend/src/styles/tokens.css` | 优先原样复制，保留语义变量和 alias；仅补 OJ 专用状态变量 |
| `frontend/src/styles/globals.css` | `frontend/src/styles/global.css` 或 `common.less` | 复制字体、reset、body、focus、caret、reduced-motion、scrollbar；移除 `@tailwind` 和 shadcn bridge |
| `frontend/src/styles/prose-claude.css` | `frontend/src/styles/markdown.less` 或独立 `feiyue-prose.less` | 按 OJ Markdown DOM 适配，保留 KaTeX/highlight 规则 |
| `tailwind.config.ts` | `feiyue-theme.less` | 只提取颜色/字体/radius/shadow 映射，不复制 Tailwind |
| `styles.css` 的 `.btn/.card/.tag/.avatar` | `feiyue-theme.less` + 组件局部样式 | 迁移为 Less mixin/Element Plus 覆盖，避免全局覆盖编辑器内部按钮 |

## 令牌合同

```css
--color-bg: #ffffff;
--color-bg-subtle: #f7f6f3;
--bg-hover: #f1f1ef;
--color-text: #37352f;
--color-text-muted: #787774;
--color-text-faint: #9b9a97;
--color-border: #edece9;
--line-strong: #dcdad4;
--color-link: #2383e2;
--radius-sm: 6px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-pill: 9999px;
--shadow-card: 0 1px 2px rgba(0, 0, 0, 0.04);
--transition: 150ms ease;
```

七类 `cat-*` 颜色和 `tag-*-bg` 透明色直接使用 Feiyue 源值；新增 OJ 结果映射时使用语义 alias，例如 AC → tools/teal、WA/RE → research/red、pending → text-faint，不在页面内重复写 hex。

## 全局表面规则

- `html`, `body`, `#app` 默认 `background: var(--color-bg)`，文字为 `var(--color-text)`。
- `var(--color-bg-subtle)` 只能用于 hover、输入框/次级控件、空状态提示、侧栏选中态和明确的弱表面；禁止将整个用户端或管理端 body 设为灰色。
- 页面容器使用 `max-width` 和 `margin-inline: auto` 控制节奏，避免用大 `margin-top` 伪装导航占位。
- `*` 使用 `box-sizing: border-box`；链接、按钮、图片、表单控件继承字体并有可见 focus ring。
- 默认过渡为 `150ms ease`；菜单/弹窗使用 200–220ms；不对大范围布局使用持续动画。
- `@media (prefers-reduced-motion: reduce)` 下关闭 shimmer、路由位移、Carousel 自动动画和提交按钮持续旋转，只保留状态变化。

## Element Plus 主题桥接

在 `feiyue-theme.less` 中把 `--el-color-*`、`--el-border-color-*`、`--el-bg-color-*`、`--el-fill-color-*`、`--el-text-color-*`、`--el-box-shadow-*` 映射到上述变量。重点覆盖：

- Button：默认深色主按钮、outline/ghost 次按钮、圆角 6–8px、禁用透明度。
- Input/Select：白底、`#edece9` 细边框，focus 使用深色 1px 或柔和 ring。
- Card：白底、细边框、`--shadow-card`；不保留 Element Plus 默认厚阴影。
- Table/Pagination：浅表头、行 hover `#f7f6f3`、状态文字使用语义色。
- Message/Notification/Alert/Popover/Dialog：12px 以内圆角、细边框、低阴影、淡入/轻微上移。

旧 `iview-custom.less` 的 AC/WA 状态、表格结构和编辑器内部主题必须在更具体的选择器中保留，不能用全局 reset 覆盖。

## 实施结果

- 新增 `src/styles/tokens.css`、`global.less` 与 `feiyue-theme.less`，并将用户端/admin 双入口接入同一套颜色、字体、圆角、阴影、Element Plus 变量和 reduced-motion 规则。
- Markdown、代码块、表格和状态色改为 token 驱动；保留 KaTeX、Highlight.js 与编辑器专用样式。

## 验收

- 浏览器计算样式中的主要颜色、半径、阴影、字体均来自 token，而不是页面散落硬编码。
- 用户端和 admin 的 body 都是白底；灰/暖灰只出现在语义明确的局部区域。
- Element Plus dialog、message、table、input、button 与 Markdown 预览无明显默认蓝紫/重阴影残留。
- 运行 `pnpm run lint:modern`、`pnpm run test:routes`、`pnpm run build`，并记录与阶段 00 基线的差异。

结果：三项检查均通过，构建生成 `dist/index.html` 与 `dist/admin/index.html`。
