import { defineComponent, h, ref } from 'vue'
// vue-echarts@8 uses ECharts' on-demand registry. Keep the full registry in
// this lazy chunk so existing line/bar/toolbox options remain compatible
// without making every page download ECharts during initial startup.
import 'echarts'
import ECharts from 'vue-echarts'

export default defineComponent({
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
    return () => {
      const { options, ...forwardedAttrs } = attrs
      return h(ECharts, {
        ...forwardedAttrs,
        option: attrs.option || options,
        loading: loading.value,
        loadingOptions: loadingOptions.value,
        ref: chart
      }, slots)
    }
  }
})
