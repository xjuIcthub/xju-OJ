import hljs from 'highlight.js/lib/core'
import cpp from 'highlight.js/lib/languages/cpp'
import python from 'highlight.js/lib/languages/python'
import java from 'highlight.js/lib/languages/java'
import 'highlight.js/styles/atom-one-light.css'
hljs.registerLanguage('cpp', cpp); hljs.registerLanguage('java', java); hljs.registerLanguage('python', python)
const render = (el, binding) => Array.from(el.querySelectorAll('code')).forEach(target => {
  if (binding.value) target.textContent = binding.value
  hljs.highlightElement(target)
})
export default { install (app) { app.directive('highlight', { mounted: render, updated: render }) } }
