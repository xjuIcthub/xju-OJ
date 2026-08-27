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
const applicationStore = fs.readFileSync(path.join(root, 'src/store/index.js'), 'utf8')
assert.ok(applicationStore.includes('authProviders: {'), 'runtime auth provider state is missing')
assert.ok(!/getters:\s*{[\s\S]*?authProviders:\s*state\s*=>\s*state\.authProviders/.test(applicationStore), 'authProviders must not be duplicated as a Pinia getter')
const frontendDockerfile = fs.readFileSync(path.join(root, 'Dockerfile'), 'utf8')
assert.ok(frontendDockerfile.includes('FROM ${NODE_IMAGE} AS frontend-base'), 'frontend toolchain base is missing')
assert.ok(frontendDockerfile.includes('FROM ${FRONTEND_BASE_IMAGE} AS frontend-deps'), 'frontend dependency stage must reuse its base')
const bake = fs.readFileSync(path.join(root, '..', 'docker-bake.hcl'), 'utf8')
assert.ok(bake.includes('target "frontend-base"'), 'frontend base bake target is missing')
const deploy = fs.readFileSync(path.join(root, '..', 'deploy.sh'), 'utf8')
assert.ok(deploy.includes('--frontend-only'), 'frontend-only deploy mode is missing')
assert.ok(deploy.includes('frontend_only_source_guard'), 'frontend-only source guard is missing')
assert.ok(deploy.includes('compose up -d --no-deps --force-recreate --wait frontend'), 'frontend-only deploy must not restart dependencies')
assert.ok(deploy.includes('target_status=$(git -C "$ROOT" status --porcelain --untracked-files=all -- "$target_path")'), 'unchanged target reuse must handle clean git status explicitly')
assert.ok(!deploy.includes('git status --porcelain --untracked-files=all -- "$target_path" | grep -q . && exit 1'), 'unchanged target reuse must not invert clean git status')
const nginx = fs.readFileSync(path.join(root, 'nginx/nginx.conf'), 'utf8')
assert.ok(/runtime-config\.js[\s\S]*no-store/.test(nginx))
const device = fs.readFileSync(path.join(root, 'src/utils/device.js'), 'utf8')
assert.ok(device.includes("Windows 10/11"), 'Windows fallback label is missing')
assert.ok(device.includes('getHighEntropyValues'), 'current-device client hints are missing')
const profileSetting = fs.readFileSync(path.join(root, 'src/pages/oj/views/setting/children/ProfileSetting.vue'), 'utf8')
assert.ok(profileSetting.includes('api.uploadAvatar(form)'), 'avatar upload must use the shared API client')
assert.ok(!profileSetting.includes('this.$http'), 'legacy undefined $http client remains')
assert.ok(profileSetting.includes('OJ profile fields are optional'), 'profile save must advertise optional onboarding fields')
assert.ok(!profileSetting.includes('Complete your OJ profile fields below before continuing'), 'profile save must not require onboarding fields')
console.log('frontend modern stack scan passed')
