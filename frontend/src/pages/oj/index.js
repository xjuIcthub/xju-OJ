import { createApp, defineComponent, h, ref } from 'vue'
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
// vue-echarts@8 uses ECharts' on-demand registry; import the full bundle so
// existing line/bar/toolbox options retain their renderer and component support.
import 'echarts'
import ECharts from 'vue-echarts'

// Keep the legacy `$refs.chart.showLoading()/hideLoading()/resize()` contract
// while using vue-echarts@8, which exposes loading through component props.
const LegacyECharts = defineComponent({
  name: 'LegacyECharts',
  inheritAttrs: false,
  setup (_, { attrs, slots, expose }) {
    const chart = ref(null)
    const loading = ref(false)
    const loadingOptions = ref({})
    const showLoading = options => {
      loadingOptions.value = options || {}
      loading.value = true
    }
    const hideLoading = () => { loading.value = false }
    const resize = (...args) => chart.value && chart.value.resize(...args)
    expose({ showLoading, hideLoading, resize, chart })
    return () => h(ECharts, {
      ...attrs,
      loading: loading.value,
      loadingOptions: loadingOptions.value,
      ref: chart
    }, slots)
  }
})

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
