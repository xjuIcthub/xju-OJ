import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  AUTH_ERROR_FALLBACK_KEY,
  AUTH_ERROR_MESSAGES,
  authErrorMessageKey,
  parseAuthError,
  removeAuthError
} from '../src/pages/oj/authError.js'
import { m as enUS } from '../src/i18n/oj/en-US.js'
import { m as zhCN } from '../src/i18n/oj/zh-CN.js'
import { m as zhTW } from '../src/i18n/oj/zh-TW.js'

// The complete set of codes backend/account/oidc.py can place in the URL. A new
// backend code missing from the frontend allow-list would silently degrade to
// the generic message, so this list is the contract that keeps failures visible.
const BACKEND_AUTH_ERROR_CODES = [
  'account_claim_conflict',
  'account_claim_invalid',
  'account_claim_mismatch',
  'account_disabled',
  'account_link_required',
  'account_missing',
  'authorization_code_missing',
  'authorization_denied',
  'discovery_unavailable',
  'email_invalid',
  'email_not_verified',
  'identity_already_linked',
  'id_token_algorithm',
  'id_token_invalid',
  'id_token_key',
  'id_token_missing',
  'issuer_mismatch',
  'jwks_unavailable',
  'link_login_required',
  'link_session_changed',
  'oidc_configuration',
  'oidc_disabled',
  'oidc_protocol_error',
  'provisioning_failed',
  'state_expired',
  'state_invalid',
  'state_missing',
  'subject_mismatch',
  'token_exchange_failed',
  'userinfo_invalid',
  'userinfo_unavailable'
]
// These two are attached as a `_cached_json` failure reason instead of an
// `OIDCError("...")` literal, so the source scan below cannot discover them and
// they are pinned here instead.
const CACHED_JSON_ERROR_CODES = ['discovery_unavailable', 'jwks_unavailable']
const LOCALES = { 'en-US': enUS, 'zh-CN': zhCN, 'zh-TW': zhTW }

// Drift guard: every code discoverable in the backend source must be covered by
// the documented contract above, so adding a backend code without a user-facing
// message fails this test instead of silently hiding the failure.
const oidcSource = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'backend', 'account', 'oidc.py'),
  'utf8'
)
const sourceCodes = new Set([
  ...[...oidcSource.matchAll(/OIDCError\(\s*"([a-z_]+)"/g)].map((match) => match[1]),
  ...[...oidcSource.matchAll(/_error_redirect\([^)]*?"([a-z_]+)"\s*\)/g)].map((match) => match[1])
])
assert.ok(sourceCodes.size >= 28, `backend auth_error source scan found only ${sourceCodes.size} codes`)
for (const code of [...sourceCodes, ...CACHED_JSON_ERROR_CODES]) {
  assert.ok(BACKEND_AUTH_ERROR_CODES.includes(code), `backend can emit ${code} but the contract omits it`)
}
assert.equal(BACKEND_AUTH_ERROR_CODES.length, 31, 'the documented backend auth_error code set changed')
for (const code of BACKEND_AUTH_ERROR_CODES) {
  assert.ok(
    Object.prototype.hasOwnProperty.call(AUTH_ERROR_MESSAGES, code),
    `auth_error code ${code} has no message mapping`
  )
  const key = authErrorMessageKey(code)
  assert.notEqual(key, AUTH_ERROR_FALLBACK_KEY, `${code} must select a specific message`)
  assert.equal(key, AUTH_ERROR_MESSAGES[code])
  for (const [locale, messages] of Object.entries(LOCALES)) {
    assert.equal(typeof messages[key], 'string', `${locale} is missing ${key}`)
    assert.ok(messages[key].length > 0, `${locale}.${key} must not be empty`)
  }
}
for (const [locale, messages] of Object.entries(LOCALES)) {
  assert.ok(messages[AUTH_ERROR_FALLBACK_KEY], `${locale} is missing the generic fallback message`)
}

// Untrusted values must never select a specific message nor be echoed back for
// rendering; only our own canonical codes survive the allow-list.
const UNTRUSTED_VALUES = ['attacker_code', '<img src=x onerror=alert(1)>', '__proto__', 'constructor', 'toString', 'State_Invalid', ' ']
for (const raw of UNTRUSTED_VALUES) {
  const parsed = parseAuthError(`/user-home?auth_error=${encodeURIComponent(raw)}`)
  assert.equal(parsed.key, AUTH_ERROR_FALLBACK_KEY, `untrusted value ${JSON.stringify(raw)} must use the fallback`)
  assert.equal(parsed.code, '', `untrusted value ${JSON.stringify(raw)} must not yield a code`)
  assert.equal(parsed.path, '/user-home')
  assert.ok(!JSON.stringify(parsed).includes(raw), `untrusted value ${JSON.stringify(raw)} leaked from the parser`)
}
for (const value of [null, undefined, 42, {}, [], 'state_invalid ']) {
  assert.equal(authErrorMessageKey(value), AUTH_ERROR_FALLBACK_KEY)
}

// Absent parameter means no message and no URL rewriting.
assert.equal(parseAuthError('/user-home'), null)
assert.equal(parseAuthError('/user-home?tab=profile'), null)
assert.equal(parseAuthError('/user-home?tab=profile#section'), null)
assert.equal(parseAuthError(undefined), null)
assert.equal(removeAuthError('/user-home?tab=profile'), '/user-home?tab=profile')

// A known code resolves to its specific key and produces a clean URL that keeps
// every other query parameter, the path, and the fragment.
const parsed = parseAuthError('/setting/security?auth_error=link_session_changed&tab=password#top')
assert.equal(parsed.code, 'link_session_changed')
assert.equal(parsed.key, 'Auth_Error_Link_Session_Changed')
assert.equal(parsed.path, '/setting/security?tab=password#top')
assert.equal(removeAuthError('/?auth_error=state_invalid&next=%2Fproblem'), '/?next=%2Fproblem')
assert.equal(removeAuthError('/?auth_error=state_invalid'), '/')
assert.equal(removeAuthError('/user-home?auth_error=state_missing&a=1&b=2'), '/user-home?a=1&b=2')
assert.equal(parseAuthError('/?auth_error=state_expired').path, '/')

// The first value wins and every auth_error occurrence is removed.
const duplicated = parseAuthError('/?auth_error=state_invalid&auth_error=account_disabled')
assert.equal(duplicated.code, 'state_invalid')
assert.equal(duplicated.key, 'Auth_Error_State_Invalid')
assert.equal(duplicated.path, '/')

// An empty value still cleans the URL and shows the generic message.
const empty = parseAuthError('/?auth_error=')
assert.equal(empty.key, AUTH_ERROR_FALLBACK_KEY)
assert.equal(empty.code, '')
assert.equal(empty.path, '/')

console.log('OIDC auth error handling passed')
