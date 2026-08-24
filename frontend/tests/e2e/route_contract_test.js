const assert = require('assert')
const fs = require('fs')
const path = require('path')

const manifestPath = path.join(__dirname, 'route-contract.json')
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))

assert.deepStrictEqual(manifest.entrypoints.map((item) => item.path), ['/', '/admin/'])
assert.ok(manifest.entrypoints.every((item) => item.refresh === true))
assert.ok(manifest.deep_links.includes('/problem/1'))
assert.ok(manifest.deep_links.includes('/admin/problem/create'))
assert.ok(manifest.api.some((item) => item.path === '/api/website/' && item.same_origin === true))
assert.ok(manifest.public.some((item) => item.missing_fallback === '404'))
assert.deepStrictEqual(manifest.redirects[0], {from: '/admin', to: '/admin/', status: 301})

const routes = fs.readFileSync(path.join(__dirname, '../../src/pages/oj/router/routes.js'), 'utf8')
assert.ok(!/path:\s*['"]\*['"]/.test(routes))
assert.ok(routes.includes('/:pathMatch(.*)*'))

const nginx = fs.readFileSync(path.join(__dirname, '../../nginx/nginx.conf'), 'utf8')
assert.ok(nginx.includes('location = /admin'))
assert.ok(nginx.includes('return 301 /admin/'))
assert.ok(nginx.includes('location ^~ /api/'))
assert.ok(/location(?:\s+\^~)?\s+\/public\//.test(nginx))
assert.ok(nginx.includes('try_files $uri =404'))

console.log('frontend route contract manifest passed')
