# Step 09：Frontend 编辑器与持久化兼容

## 目标

独立迁移 CodeMirror 和富文本编辑器，保护数据库中既有 HTML、代码文本、上传路径和 v-model 语义。不做批量数据库 HTML 重写。

## 进入条件

- Step 08 UI 组件迁移稳定。
- Step 01 已建立编辑器 HTML corpus 和上传样本。
- 已确认数据库中旧 HTML 的来源、允许标签、附件路径和 sanitizer 边界。

## 目标方向

- CodeMirror 5/`vue-codemirror-lite` → CodeMirror 6 + 本地 Vue3 adapter。
- Simditor/tar-simditor → Tiptap Vue3 + 本地 `EditorAdapter`，只有 POC 和 round-trip 通过才替换。
- 不为迁移方便直接改变后端字段、HTML 存储编码或上传 URL。

## 文件范围

- `frontend/src/pages/admin/components/CodeMirror.vue`
- `frontend/src/pages/oj/components/CodeMirror.vue`
- `frontend/src/pages/admin/components/Simditor.vue`
- `frontend/src/pages/admin/components/simditor-file-upload.js`
- 新增 `frontend/src/shared/editors/**`
- 编辑器 fixture、测试和依赖声明

## CodeMirror 批次

1. adapter 保持 `value/input` 兼容。
2. 迁移语言模式、主题、tab、换行、只读和 resize。
3. 验证题目编辑、提交代码、复制、错误提示和大文本。
4. 对用户代码只做传输，不做格式化或换行规范化。

## 富文本批次

1. 建立旧 HTML → 编辑器 → HTML 的 round-trip corpus。
2. 处理图片/文件上传、失败回滚、已有附件和权限。
3. 只允许明确的 sanitizer/语义差异；保留未知标签样本并停止自动转换。
4. 先在新记录或 staging 数据上运行，禁止对生产历史 HTML 批量 save。

## 计划命令

```bash
cd frontend
pnpm add @codemirror/state @codemirror/view @codemirror/lang-javascript
pnpm add @tiptap/vue-3 @tiptap/starter-kit
pnpm install --frozen-lockfile
pnpm run test:unit -- editors
pnpm run test:e2e -- --grep 'editor|upload'
```

包名和版本必须以 Step 00 锁和实际 POC 为准；命令只是目标形态。

## 验收

- 旧 HTML 不编辑直接保存时 normalized semantic diff 为零，或有逐项批准差异。
- 新旧编辑器均保持 v-model、上传 URL、图片显示、权限和错误行为。
- 代码编辑器的行号、语言高亮、tab、换行和提交 payload 与基线一致。
- XSS/sanitizer 负向样本仍被拒绝或安全处理。
- 数据库没有新增批量 migration、字段重写或隐式内容格式化。

## 停止条件

- 需要批量重写历史 HTML 才能启动。
- 上传路径、附件权限或 API payload 改变。
- adapter 通过双写造成内容竞态。
- 任何不在白名单中的语义差异无法解释。

## 回滚

切回旧编辑器组件和 frontend digest；保留新依赖但不执行数据回写。若已经写入新格式，必须先证明旧编辑器可读取，否则进入数据恢复/forward-fix，不可简单降镜像。

## 完成标志

提交格式建议：

```text
feat(frontend): migrate editors behind compatibility adapters
```

完成后进入 Step 10 的最终 frontend 平台清理。
