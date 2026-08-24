<template><div ref="host" class="cm6-adapter"></div></template>
<script>
import { EditorState, Compartment } from '@codemirror/state'
import { EditorView, keymap, lineNumbers } from '@codemirror/view'
import { defaultKeymap, indentWithTab } from '@codemirror/commands'
import { cpp } from '@codemirror/lang-cpp'
import { java } from '@codemirror/lang-java'
import { python } from '@codemirror/lang-python'
import { javascript } from '@codemirror/lang-javascript'

const languageFor = (mode = '') => {
  const value = mode.toLowerCase()
  if (value.includes('python')) return python()
  if (value.includes('java') && !value.includes('javascript')) return java()
  if (value.includes('javascript') || value.includes('node')) return javascript()
  return cpp()
}

export default {
  name: 'CodeMirrorAdapter',
  props: {
    value: { type: String, default: '' },
    modelValue: { type: String, default: undefined },
    mode: { type: String, default: 'text/x-csrc' },
    readOnly: { type: Boolean, default: false },
    lineWrapping: { type: Boolean, default: true },
    autofocus: { type: Boolean, default: false }
  },
  emits: ['input', 'change', 'update:value', 'update:modelValue'],
  data: () => ({ view: null, languageSlot: new Compartment(), editableSlot: new Compartment() }),
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
.cm6-adapter .cm-editor { min-height: 300px; max-height: 1000px; overflow: auto; border: 1px solid var(--el-border-color); }
.cm6-adapter .cm-scroller { font-family: monospace; }
</style>
