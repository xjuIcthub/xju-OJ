<template>
  <div class="code-editor-shell" @mousedown="focusFromShell">
    <div class="editor-toolbar">
      <div class="editor-toolbar-group">
        <span class="toolbar-label">{{$t('m.Language')}}:</span>
        <Select :value="language" @on-change="onLangChange" class="adjust">
          <Option v-for="item in languages" :key="item" :value="item">{{item}}
          </Option>
        </Select>

        <Tooltip :content="this.$t('m.Reset_to_default_code_definition')" placement="top">
          <button type="button" class="editor-icon-button" :aria-label="this.$t('m.Reset_to_default_code_definition')" @click="onResetClick">
            <Icon type="undo"></Icon>
          </button>
        </Tooltip>

        <Tooltip :content="this.$t('m.Upload_file')" placement="top">
          <button type="button" class="editor-icon-button" :aria-label="this.$t('m.Upload_file')" @click="onUploadFile">
            <Icon type="upload"></Icon>
          </button>
        </Tooltip>

        <input id="file-uploader" ref="fileUploader" type="file" class="file-uploader" @change="onUploadFileDone">
      </div>
      <div class="editor-toolbar-group theme-control">
        <span class="toolbar-label">{{$t('m.Theme')}}:</span>
        <Select :value="theme" @on-change="onThemeChange" class="adjust">
          <Option v-for="item in themes" :key="item.label" :value="item.value">{{item.label}}
          </Option>
        </Select>
      </div>
    </div>
    <CodeMirrorAdapter :value="value" :mode="mode[language]" :theme="theme" @change="onEditorCodeChange" ref="myEditor" />
  </div>
</template>
<script>
  import utils from '@/utils/utils'
  import CodeMirrorAdapter from '@/shared/editors/CodeMirrorAdapter.vue'
  export default {
    name: 'CodeMirror', components: { CodeMirrorAdapter },
    props: {
      value: { type: String, default: '' }, languages: { type: Array, default: () => ['C', 'C++', 'Java', 'Python2'] },
      language: { type: String, default: 'C++' }, theme: { type: String, default: 'solarized' }
    },
    emits: ['update:value', 'input', 'changeLang', 'changeTheme', 'resetCode'],
    data () { return { mode: { 'C': 'text/x-csrc', 'C++': 'text/x-c++src' }, themes: [
      {label: 'Monokai', value: 'monokai'}, {label: 'Solarized Light', value: 'solarized'},
      {label: 'Material', value: 'material'} ] } },
    mounted () { utils.getLanguages().then(languages => { const mode = {}; languages.forEach(lang => { mode[lang.name] = lang.content_type }); this.mode = mode; this.$refs.myEditor.focus() }) },
    methods: {
      onEditorCodeChange (value) { this.$emit('update:value', value); this.$emit('input', value) },
      onLangChange (value) { this.$emit('changeLang', value) }, onThemeChange (value) { this.$emit('changeTheme', value) },
      onResetClick () { this.$emit('resetCode') }, onUploadFile () { this.$refs.fileUploader?.click() },
      onUploadFileDone (event) { const file = event.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onload = e => { this.$refs.myEditor.setValue(e.target.result); event.target.value = '' }; reader.readAsText(file, 'UTF-8') },
      focus () { this.$refs.myEditor?.focus() },
      focusFromShell (event) {
        if (event.target.closest('button, input, select, textarea, [role="button"], .el-select, .ivu-select')) return
        window.requestAnimationFrame(() => this.focus())
      }
    }
  }
</script>

<style lang="less" scoped>
  .code-editor-shell { margin: 0 0 15px; }
  .editor-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: 5px 5px 15px; }
  .editor-toolbar-group { display: flex; min-width: 0; align-items: center; gap: 9px; }
  .toolbar-label { flex: none; color: var(--color-text-muted); font-weight: 500; }
  .adjust { width: 150px; }
  .file-uploader { display: none; }
  .editor-icon-button {
    appearance: none;
    display: inline-grid;
    width: 34px;
    height: 34px;
    flex: none;
    place-items: center;
    padding: 0;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    transition: color var(--transition), border-color var(--transition), background-color var(--transition);
  }
  .editor-icon-button:hover { border-color: var(--color-border); background: var(--color-bg-subtle); color: var(--color-text); }
  .editor-icon-button:active { background: var(--bg-hover); transform: scale(.97); }
  .editor-icon-button :deep(.legacy-icon) { display: inline-flex; align-items: center; }

  @media (max-width: 700px) {
    .editor-toolbar { align-items: flex-start; flex-direction: column; }
    .theme-control { width: 100%; }
    .theme-control .adjust { flex: 1; width: auto; }
  }
</style>

<style>
  .CodeMirror {
    height: auto !important;
  }
  .CodeMirror-scroll {
    min-height: 300px;
    max-height: 1000px;
  }
</style>
