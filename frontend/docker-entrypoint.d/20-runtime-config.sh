#!/bin/sh
set -eu

json_escape() {
    printf '%s' "$1" | sed 's/[\\"]/\\&/g'
}

app_domain=$(json_escape "${APP_DOMAIN:-_}")
public_base_url=$(json_escape "${PUBLIC_BASE_URL:-}")
version=$(json_escape "${GIT_COMMIT:-unknown}")
authentik_enabled=${AUTHENTIK_OIDC_ENABLED:-false}
authentik_register_url=$(json_escape "${AUTHENTIK_OIDC_REGISTER_URL:-https://auth.icthub.top/if/flow/icthub-public-registration/}")
local_login_enabled=${AUTHENTIK_LOCAL_LOGIN_ENABLED:-true}
local_register_enabled=${AUTHENTIK_LOCAL_REGISTER_ENABLED:-true}

cat > /usr/share/nginx/html/runtime-config.js <<EOF
window.__XJU_RUNTIME_CONFIG__ = {
  APP_DOMAIN: "${app_domain}",
  PUBLIC_BASE_URL: "${public_base_url}",
  VERSION: "${version}",
  OJ_FRONTEND_DEV_MODE: false,
  AUTHENTIK_OIDC_ENABLED: ${authentik_enabled},
  AUTHENTIK_OIDC_REGISTER_URL: "${authentik_register_url}",
  AUTHENTIK_LOCAL_LOGIN_ENABLED: ${local_login_enabled},
  AUTHENTIK_LOCAL_REGISTER_ENABLED: ${local_register_enabled}
};
EOF
