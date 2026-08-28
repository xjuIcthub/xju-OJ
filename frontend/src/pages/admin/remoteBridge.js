const IMPORT_SCHEMA = 'xju-oj.remote-import.v1'
const READY_ATTRIBUTE = 'data-xju-oj-remote-bridge-version'
const IMPORT_EVENT = 'xju-oj:remote-bridge:import'
const IMPORT_RESULT_EVENT = 'xju-oj:remote-bridge:import-event'

function bridgeVersionParts () {
  return (document.documentElement.getAttribute(READY_ATTRIBUTE) || '')
    .split('.')
    .map(value => Number.parseInt(value, 10))
}

export function supportsRemoteProblemImport () {
  const parts = bridgeVersionParts()
  if (!parts.length || parts.some(Number.isNaN)) return false
  return (parts[0] || 0) > 0 || (parts[1] || 0) >= 3
}

export function collectCodeforcesProblemPage (reference, onStatus) {
  if (!supportsRemoteProblemImport()) return Promise.reject(new Error('REMOTE_BRIDGE_IMPORT_NOT_INSTALLED'))
  const requestId = `${Date.now()}-${crypto.getRandomValues(new Uint32Array(2)).join('-')}`
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => finish(() => reject(new Error('Codeforces 题面导入超时'))), 180000)
    const listener = event => {
      const detail = event && event.detail
      if (!detail || detail.schema !== IMPORT_SCHEMA || detail.request_id !== requestId) return
      if (typeof onStatus === 'function') onStatus(detail)
      if (detail.status === 'FINISHED' && detail.page_html) {
        finish(() => resolve(detail.page_html))
      } else if (detail.status === 'FAILED') {
        finish(() => reject(new Error(detail.message || 'Codeforces 题面读取失败')))
      }
    }
    const finish = callback => {
      window.clearTimeout(timeout)
      window.removeEventListener(IMPORT_RESULT_EVENT, listener)
      callback()
    }
    window.addEventListener(IMPORT_RESULT_EVENT, listener)
    window.dispatchEvent(new CustomEvent(IMPORT_EVENT, {
      detail: {
        schema: IMPORT_SCHEMA,
        request_id: requestId,
        provider: 'CODEFORCES',
        reference
      }
    }))
  })
}
