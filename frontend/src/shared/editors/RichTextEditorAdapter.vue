<template>
  <div class="rich-editor-adapter">
    <div class="rich-editor-toolbar">
      <button type="button" @click="command('toggleBold')"><b>B</b></button>
      <button type="button" @click="command('toggleItalic')"><i>I</i></button>
      <button type="button" @click="command('toggleBulletList')">• List</button>
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
import Link from '@tiptap/extension-link'

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
      extensions: [StarterKit, Image, Link.configure({ openOnClick: false })],
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
    command (name) { if (this.editor) this.editor.chain().focus()[name]().run() },
    async upload (event, image) {
      const file = event.target.files && event.target.files[0]
      event.target.value = ''
      if (!file) return
      const data = new FormData()
      data.append(image ? 'image' : 'file', file)
      const url = image ? '/api/admin/upload_image/' : '/api/admin/upload_file'
      const response = await axios.post(url, data)
      const body = response.data || {}
      const href = body.file_path || (body.data && (body.data.file_path || body.data.url)) || body.url
      if (!href) throw new Error('Upload response did not contain a URL')
      if (image) this.editor.chain().focus().setImage({ src: href }).run()
      else this.editor.chain().focus().insertContent(`<a target="_blank" class="simditor-attach-link" href="${href}">${body.file_name || file.name}</a>`).run()
      this.$emit('upload', body)
    }
  }
}
</script>
<style>
.rich-editor-adapter { border: 1px solid var(--el-border-color); }
.rich-editor-toolbar { padding: 8px; border-bottom: 1px solid var(--el-border-color); }
.rich-editor-toolbar button { margin-right: 6px; }
.rich-editor-adapter .tiptap { min-height: 180px; padding: 12px; outline: none; }
</style>
