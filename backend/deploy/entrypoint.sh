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

run_backend() {
    if [ "$(id -u)" -eq 0 ] && command -v su-exec >/dev/null 2>&1; then
        exec su-exec "$backend_user" "$@"
    fi
    exec "$@"
}

run_backend_shell() {
    if [ "$(id -u)" -eq 0 ] && command -v su-exec >/dev/null 2>&1; then
        exec su-exec "$backend_user" /bin/sh -c "$1"
    fi
    exec /bin/sh -c "$1"
}

bootstrap_runtime() {
    if [ "${1:-}" = "--dry-run" ]; then
        test -d "$APP_ROOT/resources/bootstrap/public/avatar"
        test -d "$APP_ROOT/resources/bootstrap/public/website"
        printf '%s\n' "runtime bootstrap check passed for $DATA_DIR"
        return
    fi

    umask 077
    mkdir -p "$DATA_DIR/config" "$DATA_DIR/log" "$DATA_DIR/ssl" "$DATA_DIR/test_case" \
        "$DATA_DIR/public/upload" "$DATA_DIR/public/avatar" "$DATA_DIR/public/website"

    if [ ! -f "$DATA_DIR/config/secret.key" ]; then
        secret_tmp="$DATA_DIR/config/.secret.key.$$"
        head -c 32 /dev/urandom | base64 | tr -d '\n' > "$secret_tmp"
        printf '\n' >> "$secret_tmp"
        chmod 600 "$secret_tmp"
        mv "$secret_tmp" "$DATA_DIR/config/secret.key"
    fi

    if [ ! -f "$DATA_DIR/public/avatar/default.png" ]; then
        install -m 0644 "$APP_ROOT/resources/bootstrap/public/avatar/default.png" \
            "$DATA_DIR/public/avatar/default.png"
    fi
    if [ ! -f "$DATA_DIR/public/website/favicon.ico" ]; then
        install -m 0644 "$APP_ROOT/resources/bootstrap/public/website/favicon.ico" \
            "$DATA_DIR/public/website/favicon.ico"
    fi

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
