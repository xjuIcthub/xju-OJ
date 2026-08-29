import { createApp } from 'vue'
import App from './App.vue'
import store from '@/store'
import i18n from '@/i18n'
import LegacyUI from '@/shared/ui/legacy-ui'
import filters from '@/utils/filters'
import router from './router'
import katex from '@/plugins/katex'
import Panel from './components/Panel.vue'
import IconBtn from './components/btn/IconBtn.vue'
import Save from './components/btn/Save.vue'
import Cancel from './components/btn/Cancel.vue'
import './style.less'

i18n.global.locale.value = 'zh-CN'

const app = createApp(App)
app.use(router).use(store).use(i18n).use(LegacyUI, { i18n }).use(katex)
app.component(IconBtn.name, IconBtn)
app.component(Panel.name, Panel)
app.component(Save.name, Save)
app.component(Cancel.name, Cancel)
app.config.globalProperties.$filters = filters
app.config.globalProperties.$error = message => app.config.globalProperties.$message.error(message)
app.config.globalProperties.$warning = message => app.config.globalProperties.$message.warning(message)
app.config.globalProperties.$success = message => app.config.globalProperties.$message.success(message || '操作成功')
app.mount('#app')
