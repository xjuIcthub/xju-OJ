<template>
  <div style="margin: 0px 0px 15px 0px">
    <Row type="flex" justify="space-between" class="header">
      <Col :span=12>
      <div>
        <span>{{$t('m.Language')}}:</span>
        <Select :value="language" @on-change="onLangChange" class="adjust">
          <Option v-for="item in languages" :key="item" :value="item">{{item}}
          </Option>
        </Select>

        <Tooltip :content="this.$i18n.t('m.Reset_to_default_code_definition')" placement="top" style="margin-left: 10px">
          <Button icon="refresh" @click="onResetClick"></Button>
        </Tooltip>

        <Tooltip :content="this.$i18n.t('m.Upload_file')" placement="top" style="margin-left: 10px">
          <Button icon="upload" @click="onUploadFile"></Button>
        </Tooltip>

        <input type="file" id="file-uploader" style="display: none" @change="onUploadFileDone">

      </div>
      </Col>
      <Col :span=12>
      <div class="fl-right">
        <span>{{$t('m.Theme')}}:</span>
        <Select :value="theme" @on-change="onThemeChange" class="adjust">
          <Option v-for="item in themes" :key="item.label" :value="item.value">{{item.label}}
          </Option>
        </Select>
      </div>
      </Col>
    </Row>
    <CodeMirrorAdapter :value="value" :mode="mode[language]" @change="onEditorCodeChange" ref="myEditor" />
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
    data () { return { mode: { 'C++': 'text/x-csrc' }, themes: [
      {label: this.$i18n.t('m.Monokai'), value: 'monokai'}, {label: this.$i18n.t('m.Solarized_Light'), value: 'solarized'},
      {label: this.$i18n.t('m.Material'), value: 'material'} ] } },
    mounted () { utils.getLanguages().then(languages => { const mode = {}; languages.forEach(lang => { mode[lang.name] = lang.content_type }); this.mode = mode; this.$refs.myEditor.focus() }) },
    methods: {
      onEditorCodeChange (value) { this.$emit('update:value', value); this.$emit('input', value) },
      onLangChange (value) { this.$emit('changeLang', value) }, onThemeChange (value) { this.$emit('changeTheme', value) },
      onResetClick () { this.$emit('resetCode') }, onUploadFile () { document.getElementById('file-uploader').click() },
      onUploadFileDone (event) { const file = event.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onload = e => { this.$refs.myEditor.setValue(e.target.result); event.target.value = '' }; reader.readAsText(file, 'UTF-8') }
    }
  }
</script>

<style lang="less" scoped>
  .header {
    margin: 5px 5px 15px 5px;
    .adjust {
      width: 150px;
      margin-left: 10px;
    }
    .fl-right {
      float: right;
    }
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
