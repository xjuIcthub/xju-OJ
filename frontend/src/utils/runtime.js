const defaults = {
  OJ_FRONTEND_DEV_MODE: false,
  DEV_LOGIN_USERNAME: '',
  DEV_LOGIN_PASSWORD: '',
  AUTHENTIK_OIDC_ENABLED: false,
  AUTHENTIK_OIDC_REGISTER_URL: 'https://auth.icthub.top/if/flow/icthub-public-registration/',
  AUTHENTIK_LOCAL_LOGIN_ENABLED: true,
  AUTHENTIK_LOCAL_REGISTER_ENABLED: true
}

const runtime = window.__XJU_RUNTIME_CONFIG__ || {}

export default { ...defaults, ...runtime }
