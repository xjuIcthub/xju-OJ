'use strict'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const userscriptPath = path.resolve(
  __dirname,
  '../static/userscripts/xju-oj-remote-bridge.user.js'
)
const source = fs.readFileSync(userscriptPath, 'utf8')
const frontendBridge = fs.readFileSync(
  path.resolve(__dirname, '../src/pages/oj/remoteBridge.js'),
  'utf8'
)

function section (startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  assert.notEqual(start, -1, `missing marker: ${startMarker}`)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(end, -1, `missing marker: ${endMarker}`)
  return source.slice(start, end)
}

assert.match(source, /^\/\/ @version\s+0\.5\.0$/m)
assert.match(frontendBridge, /\(parts\[1\] \|\| 0\) >= 5/)

const opener = section(
  'function openProviderActionTab',
  'function codeforcesImportTarget'
)
assert.match(opener, /status !== 'AUTH_REQUIRED'/)
assert.match(opener, /status !== 'VERIFICATION_REQUIRED'/)
assert.match(opener, /GM_openInTab\(task\.target_url/)

const runner = section(
  'async function runRemoteTaskFromOj',
  'async function startRemoteTask'
)
for (const provider of ['CODEFORCES', 'NOWCODER', 'LUOGU']) {
  assert.match(runner, new RegExp(`task\\.provider === '${provider}'`))
}

const submitEntry = section(
  'async function startRemoteTask',
  'function startRemoteImport'
)
assert.match(submitEntry, /await runRemoteTaskFromOj\(task\)/)
assert.doesNotMatch(submitEntry, /GM_openInTab/)

assert.match(source, /submitCodeforcesFromOj/)
assert.match(source, /submitNowcoderDirect/)
assert.match(source, /submitLuoguDirect/)

console.log('remote bridge contract passed')
