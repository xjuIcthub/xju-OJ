<template>
  <div class="markdown-editor-adapter">
    <div class="markdown-editor-toolbar">
      <div class="markdown-format-actions" aria-label="Markdown formatting">
        <button type="button" title="Bold" aria-label="Bold" @click="wrapSelection('**', '**', 'bold')"><strong>B</strong></button>
        <button type="button" title="Italic" aria-label="Italic" @click="wrapSelection('*', '*', 'italic')"><em>I</em></button>
        <button type="button" title="Underline" aria-label="Underline" @click="wrapSelection('<u>', '</u>', 'underline')"><u>U</u></button>
        <button type="button" title="Strikethrough" aria-label="Strikethrough" @click="wrapSelection('~~', '~~', 'strikethrough')"><s>S</s></button>
        <button type="button" title="Inline code" aria-label="Inline code" @click="wrapSelection('`', '`', 'code')"><span>&lt;/&gt;</span></button>
        <button type="button" title="Inline formula" aria-label="Inline formula" @click="wrapSelection('$', '$', 'a+b')"><span>∑</span></button>
      </div>
      <div class="markdown-mode-switch" role="group" aria-label="Editor mode">
        <button type="button" :class="{ active: mode === 'raw' }" @click="setMode('raw')">Raw</button>
        <button type="button" :class="{ active: mode === 'preview' }" @click="setMode('preview')">Preview</button>
      </div>
    </div>
    <textarea v-show="mode === 'raw'"
              ref="rawEditor"
              v-model="source"
              class="markdown-raw-editor"
              spellcheck="false"
              @input="emitMarkdown"></textarea>
    <div v-show="mode === 'preview'"
         class="markdown-preview markdown-body"
         v-html="previewHtml"
         v-katex
         v-highlight></div>
  </div>
</template>

<script>
import markdownIt from 'markdown-it'
import TurndownService from 'turndown'
import { gfm } from 'turndown-plugin-gfm'

const renderer = markdownIt({
  html: true,
  breaks: true,
  linkify: true
})

function createTurndown () {
  const service = new TurndownService({
    bulletListMarker: '-',
    codeBlockStyle: 'fenced',
    emDelimiter: '*',
    strongDelimiter: '**'
  })
  service.use(gfm)
  service.keep(['u'])
  return service
}

function htmlToMarkdown (value, turndown) {
  const content = String(value || '')
  if (!/<[a-z][\s\S]*>/i.test(content)) return content
  const math = []
  const protectedHtml = content.replace(
    /\$\$[\s\S]*?\$\$|\$[^$]+\$|\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]/g,
    expression => {
      const token = `MARKDOWNMATHPLACEHOLDER${math.length}X`
      math.push(expression)
      return token
    }
  )
  let markdown = turndown.turndown(protectedHtml)
  math.forEach((expression, index) => {
    markdown = markdown.replace(`MARKDOWNMATHPLACEHOLDER${index}X`, expression)
  })
  return markdown
}

export default {
  name: 'RichTextEditorAdapter',
  props: {
    value: { type: String, default: '' },
    modelValue: { type: String, default: undefined }
  },
  emits: ['input', 'change', 'update:value', 'update:modelValue'],
  data () {
    return {
      mode: 'raw',
      source: '',
      previewHtml: '',
      lastRenderedHtml: '',
      turndown: null
    }
  },
  computed: {
    content () {
      return this.modelValue === undefined ? this.value : this.modelValue
    }
  },
  mounted () {
    this.turndown = createTurndown()
    this.source = htmlToMarkdown(this.content, this.turndown)
    this.previewHtml = renderer.render(this.source)
    this.lastRenderedHtml = this.previewHtml
  },
  watch: {
    content (value) {
      if (!this.turndown || value === this.lastRenderedHtml) return
      this.source = htmlToMarkdown(value, this.turndown)
      this.previewHtml = renderer.render(this.source)
      this.lastRenderedHtml = this.previewHtml
    }
  },
  methods: {
    emitMarkdown () {
      const html = renderer.render(this.source || '')
      this.previewHtml = html
      this.lastRenderedHtml = html
      this.$emit('input', html)
      this.$emit('change', html)
      this.$emit('update:value', html)
      this.$emit('update:modelValue', html)
    },
    setMode (mode) {
      this.mode = mode
      if (mode === 'raw') this.$nextTick(() => this.$refs.rawEditor?.focus())
    },
    wrapSelection (before, after, placeholder) {
      this.mode = 'raw'
      this.$nextTick(() => {
        const editor = this.$refs.rawEditor
        if (!editor) return
        const start = editor.selectionStart
        const end = editor.selectionEnd
        const selection = this.source.slice(start, end) || placeholder
        const replacement = `${before}${selection}${after}`
        this.source = `${this.source.slice(0, start)}${replacement}${this.source.slice(end)}`
        this.emitMarkdown()
        this.$nextTick(() => {
          editor.focus()
          const selectionStart = start + before.length
          editor.setSelectionRange(selectionStart, selectionStart + selection.length)
        })
      })
    }
  }
}
</script>

<style scoped lang="less">
.markdown-editor-adapter { overflow: hidden; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: var(--color-bg); }
.markdown-editor-toolbar { display: flex; min-height: 42px; align-items: center; justify-content: space-between; gap: 12px; padding: 5px 7px; border-bottom: 1px solid var(--color-border); background: var(--color-bg); }
.markdown-format-actions, .markdown-mode-switch { display: flex; align-items: center; gap: 2px; }
.markdown-editor-toolbar button { appearance: none; display: inline-grid; min-width: 30px; height: 30px; place-items: center; padding: 0 7px; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--color-text-muted); cursor: pointer; font-family: var(--font-sans); font-size: 13px; transition: color var(--transition), background-color var(--transition); }
.markdown-editor-toolbar button:hover, .markdown-editor-toolbar button:focus-visible { background: var(--color-bg-subtle); color: var(--color-text); outline: none; }
.markdown-mode-switch { padding: 2px; border: 1px solid var(--color-border); border-radius: var(--radius-pill); background: var(--color-bg-subtle); }
.markdown-mode-switch button { min-width: 62px; height: 26px; border-radius: var(--radius-pill); font-size: 12px; }
.markdown-mode-switch button.active { background: var(--color-bg); color: var(--color-text); box-shadow: 0 1px 3px rgba(55, 53, 47, .09); }
.markdown-raw-editor { display: block; width: 100%; min-height: 190px; resize: vertical; padding: 13px 15px; border: 0; outline: 0; background: var(--color-bg); color: var(--color-text); font-family: var(--font-mono); font-size: 13px; line-height: 1.7; tab-size: 2; }
.markdown-preview { min-height: 190px; padding: 13px 15px; color: var(--color-text); }
.markdown-preview :deep(> :last-child) { margin-bottom: 0; }

@media (max-width: 640px) {
  .markdown-editor-toolbar { align-items: flex-start; flex-direction: column; }
  .markdown-mode-switch { align-self: flex-end; }
}
</style>
