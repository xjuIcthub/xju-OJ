#!/bin/sh
set -eu

json_escape() {
    printf '%s' "$1" | sed 's/[\\"]/\\&/g'
}

app_domain=$(json_escape "${APP_DOMAIN:-_}")
public_base_url=$(json_escape "${PUBLIC_BASE_URL:-}")
version=$(json_escape "${GIT_COMMIT:-unknown}")

cat > /usr/share/nginx/html/runtime-config.js <<EOF
window.__XJU_RUNTIME_CONFIG__ = {
  APP_DOMAIN: "${app_domain}",
  PUBLIC_BASE_URL: "${public_base_url}",
  VERSION: "${version}"
};
EOF
