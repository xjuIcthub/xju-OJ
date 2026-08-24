#!/bin/sh
set -eu

umask 0007

clear_scratch() {
    find "$1" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
}

mkdir -p /judger/run /judger/spj /judger/locks /log
chmod 755 /judger
chown root:root /judger
clear_scratch /judger/run
clear_scratch /judger/spj

# Only the root launcher may create top-level submission workspaces. Individual
# workspaces grant the compiler/runtime group access without exposing siblings.
chmod 711 /judger/run
chown root:root /judger/run

# Only the root launcher publishes versioned SPJ artifacts. Compiler and SPJ
# users may traverse to private staging/final files but cannot replace entries.
chmod 711 /judger/spj
chown root:root /judger/spj

# Cross-worker synchronization files live outside all sandbox-writable trees.
chmod 700 /judger/locks
chown root:root /judger/locks
: > /judger/locks/compiler.lock
: > /judger/locks/file-io.lock
chmod 600 /judger/locks/compiler.lock /judger/locks/file-io.lock
chown root:root /judger/locks/compiler.lock /judger/locks/file-io.lock

chmod 770 /log
chown root:root /log

CPU_CORE_NUM="$(nproc)"
WORKER_NUM="${JUDGER_HTTP_WORKERS:-$CPU_CORE_NUM}"
if [ "$WORKER_NUM" -lt 1 ]; then
    WORKER_NUM=1
fi
if [ "$WORKER_NUM" -gt 4 ]; then
    WORKER_NUM=4
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
    --threads "${JUDGER_HTTP_THREADS:-2}" \
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
