import renderMathInElement from 'katex/contrib/auto-render/auto-render.js'
import 'katex/dist/katex.min.css'
const defaults = { throwOnError: false, delimiters: [
  {left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false},
  {left: '\\[', right: '\\]', display: true}, {left: '\\(', right: '\\)', display: false}
] }
const render = (el, binding) => renderMathInElement(el, { ...defaults, ...((binding.value && binding.value.options) || {}) })
export default { install (app) { app.directive('katex', { mounted: render, updated: render }) } }
