#!/bin/sh
set -eu

clear_scratch() {
    find "$1" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
}

mkdir -p /judger/run /judger/spj /log
clear_scratch /judger/run
clear_scratch /judger/spj

chmod 711 /judger/run
chown compiler:code /judger/run

chmod 710 /judger/spj
chown compiler:spj /judger/spj

CPU_CORE_NUM="$(nproc)"
if [ "$CPU_CORE_NUM" -lt 2 ]; then
    WORKER_NUM=2
else
    WORKER_NUM="$CPU_CORE_NUM"
fi

heartbeat_loop() {
    while :; do
        if [ -n "${BACKEND_URL:-}" ] && [ -n "${SERVICE_URL:-}" ]; then
            if ! /app/.venv/bin/python /app/service.py; then
                printf '%s\n' 'JudgeServer heartbeat degraded' >&2
            fi
        fi
        sleep "${HEARTBEAT_INTERVAL:-5}"
    done
}

heartbeat_loop &
HEARTBEAT_PID=$!

/app/.venv/bin/gunicorn server:app \
    --workers "$WORKER_NUM" \
    --threads 4 \
    --error-logfile /log/gunicorn.log \
    --bind 0.0.0.0:8080 &
SERVER_PID=$!

cleanup() {
    kill "$SERVER_PID" "$HEARTBEAT_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    wait "$HEARTBEAT_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

wait "$SERVER_PID"
