const assert = require('node:assert')
const fs = require('node:fs')
const path = require('node:path')
const root = path.join(__dirname, '..')
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'))
const exact = {
  vue: '3.5.41', 'vue-router': '5.2.0', 'vue-i18n': '11.4.8', 'element-plus': '2.14.4',
  pinia: '4.0.3', vite: '8.2.1', '@tiptap/vue-3': '3.30.3', '@tiptap/extension-table': '3.30.3',
  '@tiptap/extension-color': '3.30.3', '@tiptap/extension-text-align': '3.30.3', '@codemirror/state': '6.7.1'
}
for (const [name, version] of Object.entries(exact)) assert.strictEqual(pkg.dependencies[name] || pkg.devDependencies[name], version)
for (const name of ['vuex', 'element-ui', 'iview', '@vue/compat', 'vue-codemirror-lite', 'tar-simditor', 'webpack']) {
  assert.ok(!pkg.dependencies[name] && !pkg.devDependencies[name], `${name} remains declared`)
}
const files = []
const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).forEach(entry => entry.isDirectory() ? walk(path.join(dir, entry.name)) : /\.(js|vue|mjs)$/.test(entry.name) && files.push(path.join(dir, entry.name)))
walk(path.join(root, 'src'))
const source = files.map(file => fs.readFileSync(file, 'utf8')).join('\n')
for (const pattern of [
  /from ['"]vuex['"]/, /from ['"]element-ui/, /from ['"]iview/, /new Vue\s*\(/, /Vue\.prototype/, /Vue\.util/,
  /\sslot(?:-scope)?\s*=/, /\.native(?:[.="])/, /\.sync=/, /\$i18n\.t/, /beforeDestroy\s*\(/,
  /template:\s*['"]/, /<\/?Button\b/, /<\/?el-dialog\b/, /<transition[^>]*>\s*<router-view/
]) assert.ok(!pattern.test(source), `legacy source matched ${pattern}`)
const vite = fs.readFileSync(path.join(root, 'vite.config.mjs'), 'utf8')
assert.ok(vite.includes("index: resolve('index.html')") && vite.includes("admin: resolve('admin/index.html')"))
const nginx = fs.readFileSync(path.join(root, 'nginx/nginx.conf'), 'utf8')
assert.ok(/runtime-config\.js[\s\S]*no-store/.test(nginx))
console.log('frontend modern stack scan passed')
