# 05 · 提交拆分与回滚

## 推荐提交序列

1. `docs: add feiyue style migration plan`：主索引与阶段文档。
2. `style(frontend): add feiyue tokens and global theme`：tokens、global、Element Plus 映射、全局背景与字体。
3. `style(frontend): align xju-oj shells and navigation`：用户端/admin 壳层、导航、XJU-OJ 品牌、footer、首页结构。
4. `style(frontend): polish oj components and submit flow`：卡片、标签、提示、弹层、表格、Lucide 适配、提交按钮状态动画。
5. `test(frontend): verify feiyue visual migration`：必要的检查脚本、路由/构建记录和验收文档，不提交构建产物。

每个提交都应能单独审查；如果某阶段改动很小，可以合并提交，但提交信息必须仍能对应阶段编号。

## 合并前清单

- 当前主工作区已有的 `deploy.sh`、backend、store、测试和其他用户改动未被覆盖。
- `git status --short` 只包含本计划允许的文件；无 `.env`、密钥、Cookie、judge token、dist/node_modules。
- `pnpm run lint:modern`、`pnpm run test:routes`、`pnpm run build`、`git diff --check` 通过。
- 关键用户端/admin 路由、提交按钮和弹层已在开发态检查；已知环境失败被明确记录。

## 回滚策略

- 视觉问题：优先回退当前阶段提交，保留已验证的 token 层和上一阶段运行版本。
- Lucide 依赖或适配问题：回退图标适配提交，恢复旧 `Icon type` 外壳；不改变页面行为和路由。
- Element Plus 全局覆盖影响编辑器/表格：撤销全局选择器，改为页面根类或组件 `:deep` 局部覆盖。
- 构建失败：恢复上一个可构建的前端提交，重新运行双入口 build；不执行 `docker compose down -v`，不触碰 backend/数据库/Redis/Judge。
- 合并到 main 后若发现严重回归，使用 `git revert` 回退对应视觉提交，不重置或覆盖主工作区其他用户改动。

## 完成标志

- 主计划阶段 00–04 的验收证据已记录，阶段 05 的提交边界清晰。
- 页面呈现 XJU-OJ，页脚呈现 `Powered by XJU-ICTHub · Version 0.2.0`。
- 视觉风格迁移完成，但 API、路由、鉴权、编辑器和判题行为保持原合同。

本轮交付状态：阶段 00–05 文档与代码均已整理；Contests/Status 筛选工具栏已统一为 Feiyue filter-control，比赛状态改为无下划线的 6px 小圆角标签，CodeMirror 三种主题统一透明底并加入 Nerd Font 回退栈。未执行 commit 或 push，以保护工作区中已有的部署、store、测试和 Vite 改动。新增依赖为 `lucide-vue-next@0.468.0`，已同步 `pnpm-lock.yaml`。
