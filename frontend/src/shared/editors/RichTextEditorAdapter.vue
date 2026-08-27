<template>
  <div class="rich-editor-adapter">
    <div class="rich-editor-toolbar">
      <button type="button" @click="command('toggleHeading', { level: 2 })">H2</button>
      <button type="button" @click="command('toggleBold')"><b>B</b></button>
      <button type="button" @click="command('toggleItalic')"><i>I</i></button>
      <button type="button" @click="command('toggleUnderline')"><u>U</u></button>
      <button type="button" @click="command('toggleBulletList')">• List</button>
      <button type="button" @click="command('toggleOrderedList')">1. List</button>
      <button type="button" @click="command('toggleBlockquote')">Quote</button>
      <button type="button" @click="setLink">Link</button>
      <button type="button" @click="command('insertTable', { rows: 3, cols: 3, withHeaderRow: true })">Table</button>
      <button type="button" @click="command('setTextAlign', 'left')">Left</button>
      <button type="button" @click="command('setTextAlign', 'center')">Center</button>
      <button type="button" @click="command('setTextAlign', 'right')">Right</button>
      <input type="color" title="Text color" @input="setColor($event.target.value)">
      <button type="button" @click="command('setHorizontalRule')">Rule</button>
      <button type="button" @click="$refs.image.click()">Image</button>
      <button type="button" @click="$refs.file.click()">File</button>
      <input ref="image" hidden type="file" accept="image/*" @change="upload($event, true)">
      <input ref="file" hidden type="file" @change="upload($event, false)">
    </div>
    <EditorContent :editor="editor" />
  </div>
</template>
<script>
import axios from 'axios'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Color from '@tiptap/extension-color'
import TextAlign from '@tiptap/extension-text-align'
import { Table, TableCell, TableHeader, TableRow } from '@tiptap/extension-table'
import { TextStyle } from '@tiptap/extension-text-style'

export default {
  name: 'RichTextEditorAdapter',
  components: { EditorContent },
  props: { value: { type: String, default: '' }, modelValue: { type: String, default: undefined } },
  emits: ['input', 'change', 'update:value', 'update:modelValue', 'upload'],
  data: () => ({ editor: null }),
  computed: { content () { return this.modelValue === undefined ? this.value : this.modelValue } },
  mounted () {
    this.editor = new Editor({
      content: this.content || '',
      extensions: [
        StarterKit.configure({ link: { openOnClick: false } }),
        Image,
        TextStyle,
        Color,
        TextAlign.configure({ types: ['heading', 'paragraph'] }),
        Table.configure({ resizable: true }),
        TableRow,
        TableHeader,
        TableCell
      ],
      onUpdate: ({ editor }) => this.emitValue(editor.getHTML())
    })
  },
  beforeUnmount () { if (this.editor) this.editor.destroy() },
  watch: {
    content (value) {
      if (this.editor && value !== this.editor.getHTML()) this.editor.commands.setContent(value || '', { emitUpdate: false })
    }
  },
  methods: {
    emitValue (value) {
      this.$emit('input', value); this.$emit('change', value)
      this.$emit('update:value', value); this.$emit('update:modelValue', value)
    },
    command (name, options) {
      if (!this.editor) return
      const chain = this.editor.chain().focus()
      if (typeof chain[name] !== 'function') return
      if (options === undefined) chain[name]().run()
      else chain[name](options).run()
    },
    setColor (color) { if (this.editor) this.editor.chain().focus().setColor(color).run() },
    setLink () {
      if (!this.editor) return
      const current = this.editor.getAttributes('link').href || ''
      const href = window.prompt('Link URL', current)
      if (href === null) return
      if (!href) this.editor.chain().focus().extendMarkRange('link').unsetLink().run()
      else this.editor.chain().focus().extendMarkRange('link').setLink({ href }).run()
    },
    async upload (event, image) {
      const file = event.target.files && event.target.files[0]
      event.target.value = ''
      if (!file) return
      const data = new FormData()
      data.append(image ? 'image' : 'file', file)
      const url = image ? '/api/admin/upload_image/' : '/api/admin/upload_file'
      const response = await axios.post(url, data)
      const body = response.data || {}
      if (body.success === false) throw new Error(body.msg || 'Upload failed')
      const payload = body.data && typeof body.data === 'object' ? body.data : body
      const href = payload.file_path || payload.url
      if (!href) throw new Error('Upload response did not contain a URL')
      if (image) this.editor.chain().focus().setImage({ src: href }).run()
      else this.editor.chain().focus().insertContent(`<a target="_blank" class="simditor-attach-link" href="${href}">${payload.file_name || file.name}</a>`).run()
      this.$emit('upload', body)
    }
  }
}
</script>
<style>
.rich-editor-adapter { border: 1px solid var(--el-border-color); }
.rich-editor-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; padding: 8px; border-bottom: 1px solid var(--el-border-color); }
.rich-editor-toolbar button { appearance: none; margin: 0; padding: 4px 7px; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; color: var(--color-text-muted); cursor: pointer; line-height: 1.2; transition: color var(--transition), background-color var(--transition), border-color var(--transition); }
.rich-editor-toolbar button:hover, .rich-editor-toolbar button:focus-visible { border-color: var(--color-border); background: var(--color-bg-subtle); color: var(--color-text); }
.rich-editor-toolbar input[type='color'] { width: 28px; height: 26px; padding: 2px; border: 1px solid var(--color-border); border-radius: var(--radius-sm); background: transparent; }
.rich-editor-adapter .tiptap { min-height: 180px; padding: 12px; outline: none; }
</style>
