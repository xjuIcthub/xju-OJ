<template><div ref="host" class="cm6-adapter"></div></template>
<script>
import { EditorState, Compartment } from '@codemirror/state'
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { EditorView, keymap, lineNumbers } from '@codemirror/view'
import { defaultKeymap, indentWithTab } from '@codemirror/commands'
import { cpp } from '@codemirror/lang-cpp'
import { java } from '@codemirror/lang-java'
import { python } from '@codemirror/lang-python'
import { javascript } from '@codemirror/lang-javascript'
import { tags } from '@lezer/highlight'

const languageFor = (mode = '') => {
  const value = mode.toLowerCase()
  if (value.includes('python')) return python()
  if (value.includes('java') && !value.includes('javascript')) return java()
  if (value.includes('javascript') || value.includes('node')) return javascript()
  return cpp()
}

const syntaxFor = (theme) => {
  const colors = {
    solarized: { keyword: '#859900', atom: '#b58900', string: '#2aa198', comment: '#93a1a1', variable: '#268bd2', type: '#b58900', number: '#d33682', operator: '#657b83' },
    monokai: { keyword: '#f92672', atom: '#ae81ff', string: '#e6db74', comment: '#75715e', variable: '#a6e22e', type: '#66d9ef', number: '#ae81ff', operator: '#f8f8f2' },
    material: { keyword: '#c792ea', atom: '#f78c6c', string: '#c3e88d', comment: '#7f848e', variable: '#82aaff', type: '#ffcb6b', number: '#f78c6c', operator: '#89ddff' }
  }[theme] || {
    keyword: '#586069', atom: '#b08800', string: '#22863a', comment: '#6a737d', variable: '#005cc5', type: '#6f42c1', number: '#005cc5', operator: '#24292e'
  }
  return syntaxHighlighting(HighlightStyle.define([
    { tag: tags.keyword, color: colors.keyword },
    { tag: [tags.atom, tags.bool, tags.null], color: colors.atom },
    { tag: tags.string, color: colors.string },
    { tag: tags.comment, color: colors.comment, fontStyle: 'italic' },
    { tag: [tags.variableName, tags.propertyName], color: colors.variable },
    { tag: [tags.typeName, tags.className], color: colors.type },
    { tag: tags.number, color: colors.number },
    { tag: tags.operator, color: colors.operator }
  ]))
}

const editorThemeFor = (theme) => {
  const themes = {
    solarized: {
      background: 'transparent', foreground: '#586e75', gutter: 'transparent', gutterText: '#839496', gutterBorder: 'var(--color-border)', selection: 'rgba(35, 131, 226, .16)', activeLine: 'rgba(247, 246, 243, .82)'
    },
    monokai: {
      background: 'transparent', foreground: '#37352f', gutter: 'transparent', gutterText: '#9b9a97', gutterBorder: 'var(--color-border)', selection: 'rgba(35, 131, 226, .16)', activeLine: 'rgba(241, 241, 239, .82)'
    },
    material: {
      background: 'transparent', foreground: '#37352f', gutter: 'transparent', gutterText: '#9b9a97', gutterBorder: 'var(--color-border)', selection: 'rgba(35, 131, 226, .16)', activeLine: 'rgba(247, 246, 243, .82)'
    }
  }
  const palette = themes[theme] || themes.solarized
  return EditorView.theme({
    '&': { color: palette.foreground, backgroundColor: palette.background },
    '.cm-content': { caretColor: palette.foreground },
    '.cm-cursor, .cm-dropCursor': { borderLeftColor: palette.foreground },
    '.cm-gutters': { backgroundColor: palette.gutter, color: palette.gutterText, border: 'none', borderRight: `1px solid ${palette.gutterBorder}` },
    '.cm-activeLine': { backgroundColor: palette.activeLine },
    '.cm-activeLineGutter': { backgroundColor: palette.gutter },
    '.cm-selectionBackground, ::selection': { backgroundColor: palette.selection },
    '&.cm-focused .cm-selectionBackground, &.cm-focused ::selection': { backgroundColor: palette.selection }
  }, { dark: false })
}

export default {
  name: 'CodeMirrorAdapter',
  props: {
    value: { type: String, default: '' },
    modelValue: { type: String, default: undefined },
    mode: { type: String, default: 'text/x-csrc' },
    theme: { type: String, default: 'solarized' },
    readOnly: { type: Boolean, default: false },
    lineWrapping: { type: Boolean, default: true },
    autofocus: { type: Boolean, default: false }
  },
  emits: ['input', 'change', 'update:value', 'update:modelValue'],
  data: () => ({ view: null, languageSlot: new Compartment(), editableSlot: new Compartment(), themeSlot: new Compartment() }),
  computed: { content () { return this.modelValue === undefined ? this.value : this.modelValue } },
  mounted () {
    this.view = new EditorView({
      parent: this.$refs.host,
      state: EditorState.create({
        doc: this.content || '',
        extensions: [
          lineNumbers(), keymap.of([...defaultKeymap, indentWithTab]),
          this.languageSlot.of(languageFor(this.mode)),
          this.editableSlot.of(EditorView.editable.of(!this.readOnly)),
          this.themeSlot.of([editorThemeFor(this.theme), syntaxFor(this.theme)]),
          this.lineWrapping ? EditorView.lineWrapping : [],
          EditorView.updateListener.of(update => {
            if (!update.docChanged) return
            const value = update.state.doc.toString()
            this.$emit('input', value)
            this.$emit('change', value)
            this.$emit('update:value', value)
            this.$emit('update:modelValue', value)
          })
        ]
      })
    })
    if (this.autofocus) this.view.focus()
  },
  beforeUnmount () { if (this.view) this.view.destroy() },
  watch: {
    content (value) {
      if (!this.view || value === this.view.state.doc.toString()) return
      this.view.dispatch({ changes: { from: 0, to: this.view.state.doc.length, insert: value || '' } })
    },
    mode (value) { this.reconfigure(this.languageSlot.reconfigure(languageFor(value))) },
    theme (value) { this.reconfigure(this.themeSlot.reconfigure([editorThemeFor(value), syntaxFor(value)])) },
    readOnly (value) { this.reconfigure(this.editableSlot.reconfigure(EditorView.editable.of(!value))) }
  },
  methods: {
    reconfigure (effect) { if (this.view) this.view.dispatch({ effects: effect }) },
    focus () { if (this.view) this.view.focus() },
    setValue (value) {
      if (this.view) this.view.dispatch({ changes: { from: 0, to: this.view.state.doc.length, insert: value || '' } })
    },
    setOption (name, value) {
      if (name === 'mode') this.reconfigure(this.languageSlot.reconfigure(languageFor(value)))
      if (name === 'readOnly') this.reconfigure(this.editableSlot.reconfigure(EditorView.editable.of(!value)))
    }
  }
}
</script>
<style>
.cm6-adapter .cm-editor { min-height: 300px; max-height: 1000px; overflow: auto; border: 1px solid var(--el-border-color); background: transparent !important; }
.cm6-adapter .cm-editor:focus,
.cm6-adapter .cm-editor.cm-focused { outline: none !important; box-shadow: none !important; }
.cm6-adapter .cm-gutters { background: transparent !important; }
.cm6-adapter .cm-scroller { font-family: 'JetBrainsMono Nerd Font', 'JetBrains Mono', 'Fira Code Nerd Font', 'Fira Code', 'Cascadia Code', 'SF Mono', Menlo, Consolas, monospace; font-variant-ligatures: contextual; }
</style>
