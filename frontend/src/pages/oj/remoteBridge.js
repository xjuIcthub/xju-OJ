const TASK_SCHEMA = 'xju-oj.remote-submit.v1'
const READY_ATTRIBUTE = 'data-xju-oj-remote-bridge-version'
const SUBMIT_EVENT = 'xju-oj:remote-bridge:submit'
const BRIDGE_EVENT = 'xju-oj:remote-bridge:event'
const MINIMUM_BRIDGE_VERSION = [0, 6, 1]

const EVENT_FIELDS = [
  'submission_id',
  'provider',
  'status',
  'remote_submission_id',
  'remote_url',
  'verdict',
  'message',
  'time_ms',
  'memory_bytes',
  'passed_tests',
  'total_tests',
  'score',
  'verification_source'
]

export function remoteBridgeVersion () {
  return document.documentElement.getAttribute(READY_ATTRIBUTE) || ''
}

export function isRemoteBridgeDetected () {
  return Boolean(remoteBridgeVersion())
}

export function isRemoteBridgeInstalled () {
  const parts = remoteBridgeVersion().split('.').map(value => Number.parseInt(value, 10))
  if (parts.some(Number.isNaN)) return false
  for (let index = 0; index < MINIMUM_BRIDGE_VERSION.length; ++index) {
    const actual = parts[index] || 0
    const required = MINIMUM_BRIDGE_VERSION[index]
    if (actual !== required) return actual > required
  }
  return true
}

export function dispatchRemoteSubmission (task, code) {
  if (!isRemoteBridgeInstalled()) throw new Error('REMOTE_BRIDGE_NOT_INSTALLED')
  if (!task || task.schema !== TASK_SCHEMA) throw new Error('REMOTE_BRIDGE_SCHEMA_MISMATCH')
  window.dispatchEvent(new CustomEvent(SUBMIT_EVENT, {
    detail: { task, code }
  }))
}

export function subscribeRemoteBridgeEvents (handler) {
  const listener = event => {
    const detail = event && event.detail
    if (!detail || detail.schema !== TASK_SCHEMA) return
    const payload = {}
    for (const field of EVENT_FIELDS) {
      if (detail[field] !== undefined && detail[field] !== null) payload[field] = detail[field]
    }
    handler(payload)
  }
  window.addEventListener(BRIDGE_EVENT, listener)
  return () => window.removeEventListener(BRIDGE_EVENT, listener)
}

export { TASK_SCHEMA }
