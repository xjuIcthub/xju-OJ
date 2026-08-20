#!/bin/sh
set -eu

if [ ! -f manage.py ]; then
    echo "No manage.py, wrong location" >&2
    exit 1
fi

: "${POSTGRES_USER:?set POSTGRES_USER for the development database}"
: "${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD for the development database}"

postgres_env=$(mktemp)
trap 'rm -f "$postgres_env"' EXIT
chmod 600 "$postgres_env"
printf 'POSTGRES_DB=onlinejudge\nPOSTGRES_USER=%s\nPOSTGRES_PASSWORD=%s\n' \
    "$POSTGRES_USER" "$POSTGRES_PASSWORD" > "$postgres_env"

docker rm -f oj-postgres-dev oj-redis-dev >/dev/null 2>&1 || true
docker run -d --env-file "$postgres_env" -p 127.0.0.1:5435:5432 --name oj-postgres-dev postgres:10
docker run -d -p 127.0.0.1:6380:6379 --name oj-redis-dev redis:4.0-alpine

if [ "${1:-}" = "--migrate" ]; then
    sleep 3
    umask 077
    mkdir -p data/config
    secret_tmp=data/config/.secret.key.$$
    head -c 32 /dev/urandom | base64 | tr -d '\n' > "$secret_tmp"
    printf '\n' >> "$secret_tmp"
    chmod 600 "$secret_tmp"
    mv "$secret_tmp" data/config/secret.key
    python manage.py migrate
    : "${INITIAL_ADMIN_PASSWORD_FILE:?set INITIAL_ADMIN_PASSWORD_FILE for the one-time admin password}"
    export INITIAL_ADMIN_USERNAME="${INITIAL_ADMIN_USERNAME:-root}"
    python manage.py create_initial_admin
fi
