// Authentik OIDC failures reach the browser as a fixed `auth_error` query
// parameter (see backend/account/oidc.py `_error_redirect`). Only the codes in
// this explicit allow-list may select a message. Any other value is untrusted
// input and silently falls back to the generic key: the raw value is never
// returned for rendering.
export const AUTH_ERROR_FALLBACK_KEY = 'Auth_Error_Generic'

export const AUTH_ERROR_MESSAGES = Object.freeze({
  account_claim_conflict: 'Auth_Error_Account_Claim_Conflict',
  account_claim_invalid: 'Auth_Error_Account_Claim_Invalid',
  account_claim_mismatch: 'Auth_Error_Account_Claim_Mismatch',
  account_disabled: 'Auth_Error_Account_Disabled',
  account_link_required: 'Auth_Error_Account_Link_Required',
  account_missing: 'Auth_Error_Account_Missing',
  authorization_code_missing: 'Auth_Error_Authorization_Code_Missing',
  authorization_denied: 'Auth_Error_Authorization_Denied',
  discovery_unavailable: 'Auth_Error_Discovery_Unavailable',
  email_invalid: 'Auth_Error_Email_Invalid',
  email_not_verified: 'Auth_Error_Email_Not_Verified',
  identity_already_linked: 'Auth_Error_Identity_Already_Linked',
  id_token_algorithm: 'Auth_Error_Id_Token_Algorithm',
  id_token_invalid: 'Auth_Error_Id_Token_Invalid',
  id_token_key: 'Auth_Error_Id_Token_Key',
  id_token_missing: 'Auth_Error_Id_Token_Missing',
  issuer_mismatch: 'Auth_Error_Issuer_Mismatch',
  jwks_unavailable: 'Auth_Error_Jwks_Unavailable',
  link_login_required: 'Auth_Error_Link_Login_Required',
  link_session_changed: 'Auth_Error_Link_Session_Changed',
  oidc_configuration: 'Auth_Error_Oidc_Configuration',
  oidc_disabled: 'Auth_Error_Oidc_Disabled',
  oidc_protocol_error: 'Auth_Error_Oidc_Protocol_Error',
  provisioning_failed: 'Auth_Error_Provisioning_Failed',
  state_expired: 'Auth_Error_State_Expired',
  state_invalid: 'Auth_Error_State_Invalid',
  state_missing: 'Auth_Error_State_Missing',
  subject_mismatch: 'Auth_Error_Subject_Mismatch',
  token_exchange_failed: 'Auth_Error_Token_Exchange_Failed',
  userinfo_invalid: 'Auth_Error_Userinfo_Invalid',
  userinfo_unavailable: 'Auth_Error_Userinfo_Unavailable'
})

function splitPath (fullPath) {
  const hashIndex = fullPath.indexOf('#')
  const withoutHash = hashIndex === -1 ? fullPath : fullPath.slice(0, hashIndex)
  const hash = hashIndex === -1 ? '' : fullPath.slice(hashIndex)
  const queryIndex = withoutHash.indexOf('?')
  return {
    path: queryIndex === -1 ? withoutHash : withoutHash.slice(0, queryIndex),
    search: queryIndex === -1 ? '' : withoutHash.slice(queryIndex + 1),
    hash
  }
}

export function authErrorMessageKey (code) {
  return typeof code === 'string' && Object.prototype.hasOwnProperty.call(AUTH_ERROR_MESSAGES, code)
    ? AUTH_ERROR_MESSAGES[code]
    : AUTH_ERROR_FALLBACK_KEY
}

export function removeAuthError (fullPath) {
  if (typeof fullPath !== 'string') return fullPath
  const { path, search, hash } = splitPath(fullPath)
  if (!search) return fullPath
  const params = new URLSearchParams(search)
  if (!params.has('auth_error')) return fullPath
  params.delete('auth_error')
  const query = params.toString()
  return query ? `${path}?${query}${hash}` : `${path}${hash}`
}

// Returns null when the parameter is absent. A known code yields its canonical
// code and i18n key; anything else yields an empty code and the generic key, so
// attacker-controlled text never leaves this module.
export function parseAuthError (fullPath) {
  if (typeof fullPath !== 'string') return null
  const { search } = splitPath(fullPath)
  if (!search) return null
  const params = new URLSearchParams(search)
  if (!params.has('auth_error')) return null
  const code = params.get('auth_error') || ''
  const known = Object.prototype.hasOwnProperty.call(AUTH_ERROR_MESSAGES, code)
  return {
    code: known ? code : '',
    key: known ? AUTH_ERROR_MESSAGES[code] : AUTH_ERROR_FALLBACK_KEY,
    path: removeAuthError(fullPath)
  }
}
