#!/bin/sh
set -eu

APP_ROOT=${APP_ROOT:-/app}
RUNTIME_ROOT=${RUNTIME_ROOT:-/data}
if [ -n "${OJ_DATA_DIR:-}" ]; then
    DATA_DIR=$OJ_DATA_DIR
elif [ "$RUNTIME_ROOT" = "/data" ]; then
    # Keep the legacy image/Compose default compatible.
    DATA_DIR=/data
else
    DATA_DIR="$RUNTIME_ROOT/backend"
fi
export OJ_DATA_DIR=$DATA_DIR

backend_user=backend

load_secret_file() {
    file_path=$1
    value_var=$2
    [ -n "$file_path" ] || return 0
    case "$value_var" in
        POSTGRES_PASSWORD) [ -n "${POSTGRES_PASSWORD:-}" ] && return 0 ;;
        JUDGE_SERVER_TOKEN) [ -n "${JUDGE_SERVER_TOKEN:-}" ] && return 0 ;;
        INITIAL_ADMIN_PASSWORD) [ -n "${INITIAL_ADMIN_PASSWORD:-}" ] && return 0 ;;
        *) return 1 ;;
    esac
    [ -r "$file_path" ] && [ -s "$file_path" ] || {
        printf '%s\n' "backend secret file is unreadable" >&2
        return 1
    }
    value=$(cat "$file_path")
    [ -n "$value" ] || {
        printf '%s\n' "backend secret file is empty" >&2
        return 1
    }
    export "$value_var=$value"
}

prepare_backend_secrets() {
    load_secret_file "${POSTGRES_PASSWORD_FILE:-}" POSTGRES_PASSWORD
    load_secret_file "${JUDGE_SERVER_TOKEN_FILE:-}" JUDGE_SERVER_TOKEN
    load_secret_file "${INITIAL_ADMIN_PASSWORD_FILE:-}" INITIAL_ADMIN_PASSWORD
}

prepare_oidc_client_secret() {
    case "${AUTHENTIK_OIDC_ENABLED:-false}" in
        true|TRUE|1|yes|YES|on|ON) ;;
        *) return 0 ;;
    esac

    source_path=${AUTHENTIK_OIDC_CLIENT_SECRET_SOURCE_FILE:-}
    destination_path=${AUTHENTIK_OIDC_CLIENT_SECRET_FILE:-}
    [ -n "$source_path" ] && [ -n "$destination_path" ] || {
        printf '%s\n' "Authentik OIDC client secret paths are missing" >&2
        return 1
    }
    [ -r "$source_path" ] && [ -s "$source_path" ] || {
        printf '%s\n' "Authentik OIDC client secret source is unreadable" >&2
        return 1
    }

    case "$destination_path" in
        /run/xju-oj-secrets/*) ;;
        *)
            printf '%s\n' "Authentik OIDC runtime secret path is invalid" >&2
            return 1
            ;;
    esac

    destination_dir=${destination_path%/*}
    mkdir -p "$destination_dir"
    chown "$backend_user:$backend_user" "$destination_dir"
    chmod 700 "$destination_dir"

    secret_tmp="$destination_dir/.authentik_oidc_client_secret.$$"
    rm -f "$secret_tmp"
    umask 077
    cat "$source_path" > "$secret_tmp"
    [ -s "$secret_tmp" ] || {
        rm -f "$secret_tmp"
        printf '%s\n' "Authentik OIDC client secret source is empty" >&2
        return 1
    }
    chown "$backend_user:$backend_user" "$secret_tmp"
    chmod 400 "$secret_tmp"
    mv -f "$secret_tmp" "$destination_path"
    export AUTHENTIK_OIDC_CLIENT_SECRET_FILE=$destination_path
}

prepare_backend_process() {
    prepare_backend_secrets
    prepare_oidc_client_secret
}

run_backend() {
    if [ "$(id -u)" -eq 0 ]; then
        prepare_backend_process
        if command -v gosu >/dev/null 2>&1; then
            exec gosu "$backend_user" "$@"
        fi
    fi
    if [ "$(id -u)" -eq 0 ] && command -v su-exec >/dev/null 2>&1; then
        exec su-exec "$backend_user" "$@"
    fi
    exec "$@"
}

run_backend_shell() {
    if [ "$(id -u)" -eq 0 ]; then
        prepare_backend_process
        if command -v gosu >/dev/null 2>&1; then
            exec gosu "$backend_user" /bin/sh -c "$1"
        fi
    fi
    if [ "$(id -u)" -eq 0 ] && command -v su-exec >/dev/null 2>&1; then
        exec su-exec "$backend_user" /bin/sh -c "$1"
    fi
    exec /bin/sh -c "$1"
}

bootstrap_runtime() {
    if [ "${1:-}" = "--dry-run" ]; then
        test -d "$APP_ROOT/resources/bootstrap/public/avatar"
        test -d "$APP_ROOT/resources/bootstrap/public/website"
        if [ "${OJ_ENV:-dev}" = "production" ] && [ ! -s "$DATA_DIR/config/secret.key" ] && [ ! -s "${DJANGO_SECRET_KEY_FILE:-}" ]; then
            printf '%s\n' "production Django secret is missing" >&2
            return 1
        fi
        printf '%s\n' "runtime bootstrap check passed for $DATA_DIR"
        return
    fi

    umask 077
    mkdir -p "$DATA_DIR/config" "$DATA_DIR/log" "$DATA_DIR/ssl" "$DATA_DIR/test_case" \
        "$DATA_DIR/public/upload" "$DATA_DIR/public/avatar" "$DATA_DIR/public/website"

    if [ ! -f "$DATA_DIR/config/secret.key" ]; then
        secret_tmp="$DATA_DIR/config/.secret.key.$$"
        if [ -n "${DJANGO_SECRET_KEY_FILE:-}" ]; then
            test -r "$DJANGO_SECRET_KEY_FILE"
            test -s "$DJANGO_SECRET_KEY_FILE"
            cat "$DJANGO_SECRET_KEY_FILE" > "$secret_tmp"
        elif [ "${OJ_ENV:-dev}" = "production" ]; then
            printf '%s\n' "production Django secret is missing" >&2
            return 1
        else
            head -c 32 /dev/urandom | base64 | tr -d '\n' > "$secret_tmp"
            printf '\n' >> "$secret_tmp"
        fi
        test -s "$secret_tmp"
        chmod 600 "$secret_tmp"
        mv "$secret_tmp" "$DATA_DIR/config/secret.key"
    fi
    test -s "$DATA_DIR/config/secret.key"

    if [ ! -f "$DATA_DIR/public/avatar/default.png" ]; then
        install -m 0644 "$APP_ROOT/resources/bootstrap/public/avatar/default.png" \
            "$DATA_DIR/public/avatar/default.png"
    fi
    if [ ! -f "$DATA_DIR/public/website/favicon.ico" ]; then
        install -m 0644 "$APP_ROOT/resources/bootstrap/public/website/favicon.ico" \
            "$DATA_DIR/public/website/favicon.ico"
    fi

    # Older avatar uploads inherited umask 077 and cannot be read by the
    # frontend container's unprivileged Nginx worker. Repair only public avatar
    # files during bootstrap; private runtime data keeps its restrictive mode.
    find "$DATA_DIR/public/avatar" -maxdepth 1 -type f -exec chmod 0644 {} +

    # Frontend mounts only public/ read-only; keep config and mutable private data isolated.
    chmod 755 "$DATA_DIR" "$DATA_DIR/public" "$DATA_DIR/public/avatar" \
        "$DATA_DIR/public/upload" "$DATA_DIR/public/website"
    chmod 700 "$DATA_DIR/config"
    chmod 750 "$DATA_DIR/log" "$DATA_DIR/ssl" "$DATA_DIR/test_case"

    if [ "$(id -u)" -eq 0 ] && id "$backend_user" >/dev/null 2>&1; then
        chown -R "$backend_user:$backend_user" "$DATA_DIR"
        chmod 755 "$DATA_DIR" "$DATA_DIR/public" "$DATA_DIR/public/avatar" \
            "$DATA_DIR/public/upload" "$DATA_DIR/public/website"
        chmod 700 "$DATA_DIR/config"
        chmod 600 "$DATA_DIR/config/secret.key"
        chmod 750 "$DATA_DIR/log" "$DATA_DIR/ssl" "$DATA_DIR/test_case"
    fi
    printf '%s\n' "runtime bootstrap completed for $DATA_DIR"
}

case "${1:-}" in
    bootstrap-runtime)
        shift
        bootstrap_runtime "$@"
        ;;
    migrate)
        run_backend_shell 'python3 manage.py check --settings=oj.settings && python3 manage.py migrate --no-input --settings=oj.settings'
        ;;
    configure-judge-token)
        run_backend python3 manage.py configure_judge_token --settings=oj.settings
        ;;
    create-initial-admin)
        run_backend python3 manage.py create_initial_admin --settings=oj.settings
        ;;
    api)
        shift
        workers=${GUNICORN_WORKERS:-2}
        threads=${GUNICORN_THREADS:-4}
        run_backend gunicorn oj.wsgi:application --bind 0.0.0.0:8000 \
            --workers "$workers" --threads "$threads" --max-requests-jitter 10000 \
            --max-requests 1000000 --keep-alive 32 "$@"
        ;;
    worker)
        shift
        processes=${DRAMATIQ_PROCESSES:-1}
        threads=${DRAMATIQ_THREADS:-4}
        run_backend python3 manage.py rundramatiq --processes "$processes" --threads "$threads" "$@"
        ;;
    manage)
        shift
        run_backend python3 manage.py "$@"
        ;;
    *)
        cat >&2 <<'EOF'
Usage: entrypoint.sh {bootstrap-runtime|migrate|configure-judge-token|create-initial-admin|api|worker|manage}
EOF
        exit 2
        ;;
esac
