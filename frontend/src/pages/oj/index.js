import { createApp, defineAsyncComponent } from 'vue'
import App from './App.vue'
import router from './router'
import store from '@/store'
import i18n from '@/i18n'
import LegacyUI from '@/shared/ui/legacy-ui'
import Panel from '@oj/components/Panel.vue'
import VerticalMenu from '@oj/components/verticalMenu/verticalMenu.vue'
import VerticalMenuItem from '@oj/components/verticalMenu/verticalMenu-item.vue'
import '@/styles/index.less'
import highlight from '@/plugins/highlight'
import katex from '@/plugins/katex'
import filters from '@/utils/filters.js'

const LegacyECharts = defineAsyncComponent(() => import('@/shared/charts/LegacyECharts.js'))

const app = createApp(App)
app.use(router).use(store).use(i18n).use(LegacyUI, { i18n }).use(highlight).use(katex)
app.component('ECharts', LegacyECharts)
app.component(VerticalMenu.name, VerticalMenu)
app.component(VerticalMenuItem.name, VerticalMenuItem)
app.component(Panel.name, Panel)
app.config.globalProperties.$filters = filters
app.config.globalProperties.$copyText = text => navigator.clipboard.writeText(text)
app.config.globalProperties.$error = message => app.config.globalProperties.$Message.error(message)
app.config.globalProperties.$info = message => app.config.globalProperties.$Message.info(message)
app.config.globalProperties.$success = message => app.config.globalProperties.$Message.success(message)
app.mount('#app')
