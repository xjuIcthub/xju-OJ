<template>
  <section class="contest-problem-composer">
    <div class="composer-header">
      <div>
        <h3>比赛题目</h3>
        <p>从本 OJ 题库索引题目，或导入外部 OJ 题目；保存比赛时按当前顺序自动编号 A、B、C。</p>
      </div>
      <div class="composer-actions">
        <el-button size="small" @click="openPublicPicker"><Icon type="search" />索引本 OJ 题目</el-button>
        <el-button size="small" type="primary" :disabled="ruleType !== 'ACM'" @click="remoteDialogVisible = true"><Icon type="download" />导入外部题目</el-button>
      </div>
    </div>

    <div v-if="items.length" class="composer-table-wrap">
      <table class="composer-table">
        <thead><tr><th class="sequence-column">序号</th><th>来源</th><th>题目</th><th class="operation-column">操作</th></tr></thead>
        <tbody>
          <tr v-for="(item, index) in items"
              :key="item.key"
              draggable="true"
              :class="{ 'is-dragging': dragIndex === index }"
              @dragstart="onDragStart(index, $event)"
              @dragover.prevent
              @drop.prevent="onDrop(index)"
              @dragend="dragIndex = null">
            <td class="sequence-cell"><span class="drag-handle" title="拖动排序">⋮⋮</span><strong>{{ displayId(index) }}</strong></td>
            <td><span :class="['source-badge', `is-${item.kind.toLowerCase()}`]">{{ item.kind === 'PUBLIC' ? '本 OJ' : item.provider }}</span></td>
            <td><strong class="problem-name">{{ item.title }}</strong><small>{{ item.reference }}</small></td>
            <td>
              <div class="row-actions">
                <button type="button" title="上移" :disabled="index === 0" @click="move(index, index - 1)">↑</button>
                <button type="button" title="下移" :disabled="index === items.length - 1" @click="move(index, index + 1)">↓</button>
                <button type="button" title="删除" class="is-danger" @click="remove(index)">×</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="composer-empty">尚未添加题目</div>

    <LegacyDialog title="索引本 OJ 题目"
                  width="760px"
                  :visible="publicDialogVisible"
                  @update:visible="publicDialogVisible = $event">
      <el-input v-model="publicKeyword" placeholder="按题号或标题搜索" clearable>
        <template #prefix><Icon type="search" /></template>
      </el-input>
      <el-table v-loading="publicLoading" :data="publicProblems" class="public-problem-table">
        <el-table-column prop="_id" label="题号" width="130"></el-table-column>
        <el-table-column prop="title" label="标题"></el-table-column>
        <el-table-column label="判题" width="120">
          <template #default="{row}">{{ row.judge_mode === 'REMOTE' ? row.remote_oj : 'LOCAL' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{row}"><el-button text type="primary" @click="addPublicProblem(row)">添加</el-button></template>
        </el-table-column>
      </el-table>
      <el-pagination class="public-pagination"
                     layout="prev, pager, next"
                     :page-size="publicLimit"
                     :total="publicTotal"
                     @current-change="loadPublicProblems"></el-pagination>
    </LegacyDialog>

    <LegacyDialog title="导入外部 OJ 题目"
                  width="680px"
                  :visible="remoteDialogVisible"
                  @update:visible="remoteDialogVisible = $event">
      <div class="provider-cards">
        <button v-for="provider in providers"
                :key="provider.value"
                type="button"
                :class="['provider-card', `provider-${provider.value.toLowerCase()}`, { active: remoteProvider === provider.value }]"
                @click="remoteProvider = provider.value">
          <strong>{{ provider.name }}</strong>
          <small>{{ provider.hint }}</small>
        </button>
      </div>
      <el-input v-model="remoteReference" :placeholder="remotePlaceholder" @keyup.enter="addRemoteProblem"></el-input>
      <template #footer>
        <cancel @click="remoteDialogVisible = false"></cancel>
        <el-button type="primary" @click="addRemoteProblem">加入比赛</el-button>
      </template>
    </LegacyDialog>
  </section>
</template>

<script>
import api from '../../api.js'
import { collectCodeforcesProblemPage, supportsRemoteProblemImport } from '../../remoteBridge'

const providers = [
  { value: 'NOWCODER', name: '牛客', hint: 'NC322024 或 ACM 题目链接' },
  { value: 'LUOGU', name: '洛谷', hint: 'P1001 或题目链接' },
  { value: 'CODEFORCES', name: 'Codeforces', hint: '4A 或题目链接' }
]

function indexToLabel (index) {
  let value = index + 1
  let label = ''
  while (value > 0) {
    value -= 1
    label = String.fromCharCode(65 + (value % 26)) + label
    value = Math.floor(value / 26)
  }
  return label
}

export default {
  name: 'ContestProblemComposer',
  props: {
    modelValue: { type: Array, default: () => [] },
    ruleType: { type: String, default: 'ACM' }
  },
  emits: ['update:modelValue'],
  data () {
    return {
      providers,
      dragIndex: null,
      publicDialogVisible: false,
      publicKeyword: '',
      publicProblems: [],
      publicLoading: false,
      publicLimit: 8,
      publicTotal: 0,
      remoteDialogVisible: false,
      remoteProvider: 'NOWCODER',
      remoteReference: ''
    }
  },
  computed: {
    items () { return this.modelValue },
    remotePlaceholder () {
      return {
        NOWCODER: 'NC322024 或 https://ac.nowcoder.com/acm/problem/322024',
        LUOGU: 'P1001 或 https://www.luogu.com.cn/problem/P1001',
        CODEFORCES: '4A 或 https://codeforces.com/problemset/problem/4/A'
      }[this.remoteProvider]
    }
  },
  methods: {
    displayId: indexToLabel,
    updateItems (items) { this.$emit('update:modelValue', items) },
    move (from, to) {
      if (to < 0 || to >= this.items.length || from === to) return
      const items = this.items.slice()
      const [item] = items.splice(from, 1)
      items.splice(to, 0, item)
      this.updateItems(items)
    },
    remove (index) {
      const items = this.items.slice()
      items.splice(index, 1)
      this.updateItems(items)
    },
    onDragStart (index, event) {
      this.dragIndex = index
      if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
    },
    onDrop (index) {
      if (this.dragIndex === null) return
      this.move(this.dragIndex, index)
      this.dragIndex = null
    },
    openPublicPicker () {
      this.publicDialogVisible = true
      this.loadPublicProblems(1)
    },
    loadPublicProblems (page = 1) {
      this.publicLoading = true
      api.getProblemList({
        keyword: this.publicKeyword,
        offset: (page - 1) * this.publicLimit,
        limit: this.publicLimit,
        rule_type: this.ruleType
      }).then(res => {
        const data = res.data.data || {}
        this.publicProblems = data.results || []
        this.publicTotal = data.total || 0
      }).finally(() => { this.publicLoading = false })
    },
    addPublicProblem (problem) {
      const key = `PUBLIC:${problem.id}`
      if (this.items.some(item => item.key === key)) {
        this.$error('该题目已经在比赛中')
        return
      }
      this.updateItems([...this.items, {
        key,
        kind: 'PUBLIC',
        problemId: problem.id,
        ruleType: problem.rule_type,
        title: problem.title,
        reference: problem._id
      }])
      this.$success('已加入题目编排')
    },
    addRemoteProblem () {
      const reference = this.remoteReference.trim()
      if (!reference) {
        this.$error('请输入外部题号或链接')
        return
      }
      const key = `REMOTE:${this.remoteProvider}:${reference.toLowerCase()}`
      if (this.items.some(item => item.key === key)) {
        this.$error('该外部题目已经在比赛中')
        return
      }
      const provider = providers.find(item => item.value === this.remoteProvider)
      this.updateItems([...this.items, {
        key,
        kind: 'REMOTE',
        provider: this.remoteProvider,
        remoteId: reference,
        title: `${provider.name} · ${reference}`,
        reference
      }])
      this.remoteReference = ''
      this.remoteDialogVisible = false
    },
    async materialize (contestId) {
      for (let index = 0; index < this.items.length; ++index) {
        const item = this.items[index]
        const displayId = indexToLabel(index)
        if (item.kind === 'PUBLIC') {
          await api.addProblemFromPublic({ problem_id: item.problemId, contest_id: contestId, display_id: displayId })
          continue
        }
        let pageHtml = ''
        if (item.provider === 'CODEFORCES') {
          if (!supportsRemoteProblemImport()) throw new Error('Codeforces 导题需要最新版远程提交助手')
          pageHtml = await collectCodeforcesProblemPage(item.remoteId)
        }
        await api.importRemoteProblem({
          provider: item.provider,
          remote_id: item.remoteId,
          display_id: displayId,
          contest_id: contestId,
          public_display_id: '',
          page_html: pageHtml
        })
      }
    }
  },
  watch: {
    publicKeyword () { if (this.publicDialogVisible) this.loadPublicProblems(1) }
  }
}
</script>

<style scoped lang="less">
.contest-problem-composer { margin: 4px 0 24px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); }
.composer-header { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 16px 18px; border-bottom: 1px solid var(--color-border); }
.composer-header h3 { margin: 0 0 4px; color: var(--color-text); font-size: 15px; }
.composer-header p { margin: 0; color: var(--color-text-muted); font-size: 12px; }
.composer-actions { display: flex; flex: none; gap: 8px; }
.composer-table-wrap { overflow-x: auto; }
.composer-table { width: 100%; border-collapse: collapse; }
.composer-table th, .composer-table td { padding: 11px 14px; border-bottom: 1px solid var(--color-border); color: var(--color-text-muted); font-size: 13px; text-align: left; }
.composer-table th { background: var(--color-bg-subtle); color: var(--color-text-faint); font-size: 11px; font-weight: 650; }
.composer-table tbody tr:last-child td { border-bottom: 0; }
.composer-table tbody tr.is-dragging { opacity: .45; }
.sequence-column { width: 100px; }
.operation-column { width: 135px; }
.sequence-cell { display: flex; align-items: center; gap: 10px; }
.sequence-cell strong { color: var(--color-text); }
.drag-handle { color: var(--color-text-faint); cursor: grab; font-size: 16px; letter-spacing: -3px; }
.source-badge { display: inline-flex; min-height: 23px; align-items: center; padding: 0 8px; border-radius: var(--radius-pill); background: var(--color-bg-subtle); color: var(--color-text-muted); font-size: 11px; font-weight: 650; }
.source-badge.is-remote { background: var(--tag-kaggle-bg); color: var(--cat-kaggle); }
.problem-name, .composer-table small { display: block; }
.problem-name { color: var(--color-text); font-weight: 600; }
.composer-table small { margin-top: 2px; color: var(--color-text-faint); }
.row-actions { display: flex; gap: 3px; }
.row-actions button { appearance: none; width: 28px; height: 28px; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--color-text-muted); cursor: pointer; }
.row-actions button:hover:not(:disabled) { background: var(--color-bg-subtle); color: var(--color-text); }
.row-actions button:disabled { opacity: .3; cursor: default; }
.row-actions button.is-danger:hover { color: var(--oj-error); }
.composer-empty { padding: 34px 18px; color: var(--color-text-faint); font-size: 13px; text-align: center; }
.public-problem-table { margin-top: 12px; }
.public-pagination { margin-top: 12px; justify-content: flex-end; }
.provider-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px; }
.provider-card { appearance: none; min-height: 92px; padding: 14px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-bg); color: var(--color-text-muted); text-align: left; cursor: pointer; transition: border-color var(--transition), background-color var(--transition), transform var(--transition); }
.provider-card:hover { transform: translateY(-1px); }
.provider-card.active { border-color: var(--color-link); background: color-mix(in srgb, var(--color-link) 5%, var(--color-bg)); }
.provider-card strong, .provider-card small { display: block; }
.provider-card strong { color: var(--color-text); font-size: 14px; }
.provider-card small { margin-top: 7px; font-size: 11px; line-height: 1.5; }
.provider-nowcoder.active { border-color: var(--cat-course); }
.provider-luogu.active { border-color: var(--cat-tools); }
.provider-codeforces.active { border-color: var(--cat-kaggle); }

@media (max-width: 760px) {
  .composer-header { align-items: flex-start; flex-direction: column; }
  .composer-actions { width: 100%; flex-wrap: wrap; }
  .provider-cards { grid-template-columns: 1fr; }
}
</style>
