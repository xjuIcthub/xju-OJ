let rendererPromise

const getRenderer = () => rendererPromise || (rendererPromise = Promise.all([
  import('katex/contrib/auto-render/auto-render.js'),
  import('katex/dist/katex.min.css')
]).then(([renderer]) => renderer.default))

const defaults = { throwOnError: false, delimiters: [
  {left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false},
  {left: '\\[', right: '\\]', display: true}, {left: '\\(', right: '\\)', display: false}
] }
const render = async (el, binding) => {
  const renderMathInElement = await getRenderer()
  if (!el.isConnected) return
  renderMathInElement(el, { ...defaults, ...((binding.value && binding.value.options) || {}) })
}
export default { install (app) { app.directive('katex', { mounted: render, updated: render }) } }
