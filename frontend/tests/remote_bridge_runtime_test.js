'use strict'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const OJ_ORIGIN = 'https://oj.icthub.top'
const source = fs.readFileSync(
  path.resolve(__dirname, '../static/userscripts/xju-oj-remote-bridge.user.js'),
  'utf8'
)

class FakeFormData {
  constructor () {
    this.values = new Map()
  }

  set (name, value) { this.values.set(name, value) }
  append (name, value) { this.values.set(name, value) }
  delete (name) { this.values.delete(name) }
}

class FakeFile {
  constructor (parts, name, options) {
    this.parts = parts
    this.name = name
    this.options = options
  }
}

function emptyDocument () {
  return {
    title: '',
    forms: [],
    querySelector: () => null,
    querySelectorAll: () => [],
    getElementById: () => null
  }
}

function codeforcesProblemDocument () {
  const language = { name: 'programTypeId', options: [{ value: '54' }] }
  const sourceFile = { name: 'sourceFile' }
  const submitter = { name: 'action', value: 'submit' }
  const form = {
    getAttribute: name => name === 'action' ? '/problemset/submit' : '',
    querySelector: selector => {
      if (selector === '[name="programTypeId"]') return language
      if (selector === '[name="sourceFile"], [name="source"]') return sourceFile
      if (selector === 'input[type="file"][name="sourceFile"]') return sourceFile
      if (selector === 'button[type="submit"][name], input[type="submit"][name]') return submitter
      return null
    }
  }
  return {
    ...emptyDocument(),
    title: 'Watermelon - Codeforces',
    forms: [form],
    querySelectorAll: selector => selector === '#header a[href^="/profile/"]'
      ? [{ getAttribute: () => '/profile/tester' }]
      : []
  }
}

function luoguProblemDocument () {
  return {
    ...emptyDocument(),
    title: 'P1001 A+B Problem',
    getElementById: id => id === 'lentille-context'
      ? { textContent: JSON.stringify({ user: { uid: 1 } }) }
      : null,
    querySelector: selector => selector === 'meta[name="csrf-token"]'
      ? { getAttribute: () => 'csrf-token' }
      : null
  }
}

function makeDomParser () {
  return class FakeDOMParser {
    parseFromString (html) {
      if (html === 'CF_PROBLEM') return codeforcesProblemDocument()
      if (html === 'LUOGU_PROBLEM') return luoguProblemDocument()
      return emptyDocument()
    }
  }
}

function jsonResponse (payload, extra = {}) {
  return {
    status: 200,
    responseText: JSON.stringify(payload),
    finalUrl: '',
    ...extra
  }
}

function taskFor (provider) {
  const common = {
    schema: 'xju-oj.remote-submit.v1',
    submission_id: `submission-${provider.toLowerCase()}`,
    provider,
    language: 'C++',
    created_at: new Date().toISOString()
  }
  if (provider === 'CODEFORCES') {
    return {
      ...common,
      problem_id: '4A',
      language_id: '54',
      target_url: 'https://codeforces.com/problemset/problem/4/A',
      provider_data: { contest_id: 4, index: 'A' }
    }
  }
  if (provider === 'LUOGU') {
    return {
      ...common,
      problem_id: 'P1001',
      language_id: '28',
      target_url: 'https://www.luogu.com.cn/problem/P1001',
      provider_data: { problem_id: 'P1001' }
    }
  }
  return {
    ...common,
    problem_id: 'NC322024',
    language_id: '3',
    target_url: 'https://ac.nowcoder.com/acm/problem/322024',
    provider_data: { problem_id: 'NC322024', question_id: '11742270', tag_id: 0 }
  }
}

async function waitFor (predicate) {
  for (let attempt = 0; attempt < 50; ++attempt) {
    if (predicate()) return
    await new Promise(resolve => setImmediate(resolve))
  }
  assert.fail('userscript scenario did not finish')
}

async function runScenario (provider, mode = 'success') {
  const listeners = new Map()
  const valueListeners = new Map()
  const storage = new Map()
  const backendEvents = []
  const openedTabs = []
  let codeforcesApiCalls = 0

  const documentElement = {
    attributes: new Map(),
    setAttribute (name, value) { this.attributes.set(name, String(value)) },
    getAttribute (name) { return this.attributes.get(name) || '' }
  }
  const document = {
    ...emptyDocument(),
    documentElement,
    readyState: 'complete',
    cookie: ''
  }
  const window = {
    location: {
      origin: OJ_ORIGIN,
      hostname: 'oj.icthub.top',
      pathname: '/contest/2/problem/A',
      hash: ''
    },
    addEventListener (name, handler) {
      const handlers = listeners.get(name) || []
      handlers.push(handler)
      listeners.set(name, handlers)
    },
    dispatchEvent (event) {
      for (const handler of listeners.get(event.type) || []) handler(event)
      return true
    },
    setTimeout (handler, delay) {
      if (delay < 5000) queueMicrotask(handler)
      return 1
    },
    clearTimeout () {},
    fetch (_url, options) {
      if (options && options.body) backendEvents.push(JSON.parse(options.body))
      return Promise.resolve({ ok: true })
    },
    focus () {}
  }
  window.window = window

  function remoteResponse (request) {
    const url = request.url
    if (provider === 'NOWCODER') {
      if (url.includes('/profile/user-info-v2')) {
        return mode === 'auth'
          ? jsonResponse({ msg: '请先登录' }, { status: 401 })
          : jsonResponse({ code: 0, data: { userId: 123, isMember: false } })
      }
      if (url.includes('/access-token')) {
        return jsonResponse({ success: true, data: { accessToken: 'token' } })
      }
      if (url.endsWith('/api/service/judge/submit')) {
        return mode === 'verification'
          ? jsonResponse({ code: 1, msg: '请完成安全验证' })
          : jsonResponse({ code: 0, data: { id: 456 } })
      }
      if (url.includes('/submit-status')) {
        return jsonResponse({
          code: 0,
          data: {
            status: 3,
            judgeReplyDesc: 'ACCEPTED',
            timeConsumption: 1,
            memoryConsumption: 1,
            rightCaseNum: 1,
            allCaseNum: 1
          }
        })
      }
    }
    if (provider === 'LUOGU') {
      if (request.method === 'GET' && url.includes('/problem/P1001')) {
        return { status: 200, responseText: 'LUOGU_PROBLEM', finalUrl: url }
      }
      if (request.method === 'POST' && url.includes('/fe/api/problem/submit/P1001')) {
        return jsonResponse({ rid: 789 })
      }
      if (url.includes('/record/789')) {
        return jsonResponse({ data: { record: { status: 12, time: 1, memory: 1, score: 100 } } })
      }
    }
    if (provider === 'CODEFORCES') {
      if (request.method === 'GET' && url.includes('/problemset/problem/4/A')) {
        return { status: 200, responseText: 'CF_PROBLEM', finalUrl: url }
      }
      if (url.includes('/api/user.status')) {
        codeforcesApiCalls += 1
        return jsonResponse({
          status: 'OK',
          result: codeforcesApiCalls === 1 ? [] : [{
            id: 999,
            contestId: 4,
            creationTimeSeconds: Math.floor(Date.now() / 1000),
            problem: { contestId: 4, index: 'A' },
            verdict: 'OK',
            timeConsumedMillis: 1,
            memoryConsumedBytes: 1024,
            passedTestCount: 1
          }]
        })
      }
      if (request.method === 'POST' && url.includes('/problemset/submit')) {
        return { status: 200, responseText: 'CF_SUBMIT', finalUrl: 'https://codeforces.com/submissions/tester' }
      }
    }
    throw new Error(`unexpected request: ${request.method} ${url}`)
  }

  const context = vm.createContext({
    console,
    window,
    document,
    unsafeWindow: window,
    URL,
    TextEncoder,
    FormData: FakeFormData,
    File: FakeFile,
    DOMParser: makeDomParser(),
    CustomEvent: class CustomEvent {
      constructor (type, options = {}) {
        this.type = type
        this.detail = options.detail
      }
    },
    MutationObserver: class MutationObserver {
      observe () {}
      disconnect () {}
    },
    GM_info: { script: { version: '0.5.0' } },
    GM_getValue: (key, fallback) => storage.has(key) ? storage.get(key) : fallback,
    GM_setValue: (key, value) => {
      const previous = storage.get(key)
      storage.set(key, value)
      for (const listener of valueListeners.get(key) || []) listener(key, previous, value, false)
    },
    GM_deleteValue: key => storage.delete(key),
    GM_addValueChangeListener: (key, listener) => {
      const handlers = valueListeners.get(key) || []
      handlers.push(listener)
      valueListeners.set(key, handlers)
      return handlers.length
    },
    GM_openInTab: url => openedTabs.push(url),
    GM_registerMenuCommand: () => {},
    GM_xmlhttpRequest: request => queueMicrotask(() => {
      try {
        request.onload(remoteResponse(request))
      } catch (error) {
        request.onerror(error)
      }
    }),
    setTimeout: window.setTimeout,
    clearTimeout: window.clearTimeout,
    queueMicrotask
  })

  vm.runInContext(source, context, { filename: 'xju-oj-remote-bridge.user.js' })
  const submitHandler = (listeners.get('xju-oj:remote-bridge:submit') || [])[0]
  assert.ok(submitHandler, 'submit listener was not installed')
  await submitHandler({ detail: { task: taskFor(provider), code: 'int main() { return 0; }' } })

  const terminalStatus = mode === 'success'
    ? 'FINISHED'
    : mode === 'auth' ? 'AUTH_REQUIRED' : 'VERIFICATION_REQUIRED'
  await waitFor(() => backendEvents.some(event => event.status === terminalStatus))
  return { backendEvents, openedTabs }
}

;(async () => {
  for (const provider of ['CODEFORCES', 'LUOGU', 'NOWCODER']) {
    const result = await runScenario(provider)
    assert.equal(result.openedTabs.length, 0, `${provider} opened a tab for a normal submission`)
    assert.ok(result.backendEvents.some(event => event.status === 'FINISHED'))
  }

  const auth = await runScenario('NOWCODER', 'auth')
  assert.equal(auth.openedTabs.length, 1)
  assert.ok(auth.backendEvents.some(event => event.status === 'AUTH_REQUIRED'))

  const verification = await runScenario('NOWCODER', 'verification')
  assert.equal(verification.openedTabs.length, 1)
  assert.ok(verification.backendEvents.some(event => event.status === 'VERIFICATION_REQUIRED'))

  console.log('remote bridge runtime passed')
})().catch(error => {
  console.error(error)
  process.exitCode = 1
})
