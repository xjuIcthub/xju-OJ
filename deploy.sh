#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ENV_FILE=${ENV_FILE:-"$ROOT/.env"}
COMPOSE_FILE=${COMPOSE_FILE:-"$ROOT/compose.yaml"}
DRY_RUN=0
CONFIG_ONLY=0

usage() {
    cat <<'EOF'
Usage: ./deploy.sh [--dry-run] [--config-only]

Environment:
  ENV_FILE       .env path (default: repository/.env)
  COMPOSE_FILE   Compose path (default: repository/compose.yaml)
EOF
}

for arg in "$@"; do
    case "$arg" in
        --help|-h) usage; exit 0 ;;
        --dry-run) DRY_RUN=1 ;;
        --config-only) CONFIG_ONLY=1 ;;
        *) printf '%s\n' "unknown option: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

fail() {
    printf '%s\n' "deploy: $*" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker is required"
docker info >/dev/null 2>&1 || fail "docker daemon is unavailable"
docker compose version >/dev/null 2>&1 || fail "docker compose is required"
[ -f "$ENV_FILE" ] || fail "env file is required: $ENV_FILE"
[ -f "$COMPOSE_FILE" ] || fail "compose file is required: $COMPOSE_FILE"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

required() {
    name=$1
    eval "value=\${$name:-}"
    [ -n "$value" ] || fail "$name is required"
}

for name in COMPOSE_PROJECT_NAME APP_DOMAIN PUBLIC_BASE_URL HTTP_BIND_ADDRESS HTTP_PORT \
    RUNTIME_ROOT BACKUP_ROOT FRONTEND_IMAGE_REF BACKEND_IMAGE_REF JUDGE_IMAGE_REF \
    POSTGRES_IMAGE_REF REDIS_IMAGE_REF POSTGRES_DB POSTGRES_USER \
    POSTGRES_PASSWORD_FILE DJANGO_SECRET_KEY_FILE JUDGE_SERVER_TOKEN_FILE \
    INITIAL_ADMIN_PASSWORD_FILE; do
    required "$name"
done

case "$RUNTIME_ROOT" in
    /*) ;;
    *) fail "RUNTIME_ROOT must be absolute" ;;
esac
[ "$RUNTIME_ROOT" != "/" ] || fail "RUNTIME_ROOT cannot be /"
case "$RUNTIME_ROOT" in
    "$ROOT"|"$ROOT"/*) fail "RUNTIME_ROOT must be outside the checkout" ;;
esac

check_secret_file() {
    path=$1
    [ -f "$path" ] || fail "secret file is missing: $path"
    [ -r "$path" ] || fail "secret file is unreadable: $path"
    [ -s "$path" ] || fail "secret file is empty: $path"
    mode=$(stat -c '%a' "$path")
    case "$mode" in
        400|440|600|640) ;;
        *) fail "secret file must be owner-readable and not writable by others: $path" ;;
    esac
}

check_secret_file "$POSTGRES_PASSWORD_FILE"
check_secret_file "$DJANGO_SECRET_KEY_FILE"
check_secret_file "$JUDGE_SERVER_TOKEN_FILE"
check_secret_file "$INITIAL_ADMIN_PASSWORD_FILE"

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

compose config --quiet || fail "compose config validation failed"

config_json=$(mktemp)
cleanup_config() { rm -f "$config_json"; }
trap cleanup_config EXIT
compose config --format json > "$config_json"
python3 - "$config_json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    config = json.load(handle)

published = []
for name, service in config.get("services", {}).items():
    if service.get("ports"):
        published.append(name)
if published != ["frontend"]:
    raise SystemExit("only frontend may publish host ports: " + ",".join(published))
PY

if [ "$DRY_RUN" -eq 1 ]; then
    printf '%s\n' "deploy dry-run passed"
    exit 0
fi
if [ "$CONFIG_ONLY" -eq 1 ]; then
    printf '%s\n' "deploy config-only passed"
    exit 0
fi

umask 077
ensure_dir() {
    path=$1
    mode=$2
    if [ -e "$path" ]; then
        [ -d "$path" ] || fail "runtime path is not a directory: $path"
        return 0
    fi
    mkdir -p "$path"
    chmod "$mode" "$path" || fail "cannot set permissions on new runtime path: $path"
}

ensure_dir "$RUNTIME_ROOT" 0750
ensure_dir "$RUNTIME_ROOT/backend" 0750
ensure_dir "$RUNTIME_ROOT/backend/public" 0750
ensure_dir "$RUNTIME_ROOT/backend/test_case" 0750
# PostgreSQL 18 re-execs its entrypoint as uid 999; the parent mount must be traversable.
ensure_dir "$RUNTIME_ROOT/postgres" 0755
ensure_dir "$RUNTIME_ROOT/redis" 0750
ensure_dir "$RUNTIME_ROOT/judge-server" 0750
ensure_dir "$RUNTIME_ROOT/judge-server/run" 0750
ensure_dir "$RUNTIME_ROOT/judge-server/log" 0750
ensure_dir "$RUNTIME_ROOT/deployments" 0750
ensure_dir "$RUNTIME_ROOT/deployments/history" 0750
ensure_dir "$BACKUP_ROOT" 0700

attempt_dir="$RUNTIME_ROOT/deployments/history/attempt-$(date -u +%Y%m%dT%H%M%SZ)-$$"
ensure_dir "$attempt_dir" 0700

on_exit() {
    rc=$?
    if [ "$rc" -ne 0 ]; then
        compose ps > "$attempt_dir/compose-ps.txt" 2>&1 || true
        compose logs --no-color --tail=200 > "$attempt_dir/compose-logs.txt" 2>&1 || true
        printf '%s\n' "deploy failed; diagnostic files retained under $attempt_dir" >&2
    fi
    exit "$rc"
}
trap on_exit EXIT

run_step() {
    name=$1
    pattern=$2
    shift 2
    log="$attempt_dir/$name.log"
    if "$@" >"$log" 2>&1; then
        printf '%s\n' "$name: PASS"
        if [ -n "$pattern" ]; then
            grep -nE "$pattern" "$log" | tail -20 || true
        fi
        return 0
    fi
    printf '%s\n' "$name: FAIL (key lines; full log: $log)" >&2
    grep -nE 'ERROR|error|failed|unhealthy|timeout|permission|Traceback|OperationalError|CommandError' "$log" | tail -80 >&2 || true
    fail "$name failed"
}

if [ "$CONFIG_ONLY" -eq 0 ]; then
    case "${DEPLOY_MODE:-build}" in
        build)
            command -v docker >/dev/null 2>&1 || fail "docker is required for build mode"
            build_network=${BUILD_NETWORK:-default}
            build_http_proxy=${BUILD_HTTP_PROXY:-}
            build_https_proxy=${BUILD_HTTPS_PROXY:-}
            build_all_proxy=${BUILD_ALL_PROXY:-}
            case "$build_network" in
                default|host|none) ;;
                *) fail "BUILD_NETWORK must be default, host, or none" ;;
            esac
            for build_proxy in "$build_http_proxy" "$build_https_proxy" "$build_all_proxy"; do
                [ -n "$build_proxy" ] || continue
                if ! python3 - "$build_proxy" "$build_network" >/dev/null 2>&1 <<'PY'
from urllib.parse import urlparse
import socket
import sys

proxy, network = sys.argv[1:]
parsed = urlparse(proxy)
if parsed.scheme not in {"http", "https", "socks5", "socks5h"}:
    raise SystemExit(1)
if not parsed.hostname or not parsed.port:
    raise SystemExit(1)
if parsed.hostname in {"127.0.0.1", "localhost", "::1"} and network != "host":
    raise SystemExit(1)
socket.create_connection((parsed.hostname, parsed.port), timeout=1).close()
PY
                then
                    fail "configured build proxy is not reachable from BuildKit; leave BUILD_*_PROXY empty or use a reachable endpoint"
                fi
            done
            git_sha=${GIT_COMMIT:-local}
            build_version=${BUILD_VERSION:-phase2}
            build_allow=
            [ "$build_network" = host ] && build_allow=--allow=network.host
            build_targets=${BUILD_TARGETS:-"frontend backend judge-toolchain server"}
            for build_target in $build_targets; do
                case "$build_target" in
                    frontend)
                        target_ref=$FRONTEND_IMAGE_REF
                        target_http_proxy=$build_http_proxy
                        target_https_proxy=$build_https_proxy
                        target_all_proxy=$build_all_proxy
                        ;;
                    backend)
                        target_ref=$BACKEND_IMAGE_REF
                        target_http_proxy=
                        target_https_proxy=
                        target_all_proxy=
                        ;;
                    server)
                        target_ref=$JUDGE_IMAGE_REF
                        target_http_proxy=
                        target_https_proxy=
                        target_all_proxy=
                        ;;
                    judge-toolchain)
                        target_ref=${JUDGE_TOOLCHAIN_IMAGE_REF:-xju-oj-judge-toolchain:tc-$git_sha}
                        target_http_proxy=
                        target_https_proxy=
                        target_all_proxy=
                        ;;
                    *)
                        fail "BUILD_TARGETS contains unsupported target: $build_target"
                        ;;
                esac
                build_log="$attempt_dir/build-$build_target.log"
                if ! BUILD_NETWORK="$build_network" GIT_SHA="$git_sha" BUILD_VERSION="$build_version" BUILD_CREATED="${BUILD_CREATED:-unknown}" \
                    docker buildx bake $build_allow --progress=plain --file "$ROOT/docker-bake.hcl" \
                    --set '*.platform=linux/amd64' \
                    --set "$build_target.args.HTTP_PROXY=$target_http_proxy" \
                    --set "$build_target.args.HTTPS_PROXY=$target_https_proxy" \
                    --set "$build_target.args.ALL_PROXY=$target_all_proxy" \
                    --set "$build_target.tags=$target_ref" \
                    --load "$build_target" >"$build_log" 2>&1
                then
                    printf '%s\n' "build chunk $build_target failed; key lines (full log: $build_log):" >&2
                    grep -nE 'ERROR|error|failed|ECONNREFUSED|CANCELED|cancelled' "$build_log" | tail -80 >&2 || true
                    fail "image build failed in chunk $build_target"
                fi
                printf '%s\n' "build chunk $build_target passed:"
                grep -E 'naming to |writing image ' "$build_log" | tail -10 || true
                if grep -qE 'WARN|warning' "$build_log"; then
                    printf '%s\n' "non-fatal warnings in $build_target (tail; full log: $build_log):"
                    grep -nE 'WARN|warning' "$build_log" | tail -20
                fi
            done
            ;;
        pull)
            compose pull postgres redis frontend backend-api backend-worker judge-server
            ;;
        *)
            fail "DEPLOY_MODE must be build or pull"
            ;;
    esac
fi

run_step infra-ready 'Healthy|healthy' compose up -d --wait postgres redis

if [ "$CONFIG_ONLY" -eq 0 ]; then
    run_step backend-bootstrap 'completed|passed' compose --profile init run --rm --no-deps backend-bootstrap
    run_step backend-migrate 'Applying |No migrations to apply|Operations to perform|Running migrations:' compose --profile init run --rm --no-deps backend-migrate

    token_log="$attempt_dir/backend-configure-token.log"
    if compose --profile init run --rm --no-deps backend-configure-token >"$token_log" 2>&1; then
        printf '%s\n' 'backend-configure-token: PASS'
        grep -nE 'configured|already' "$token_log" | tail -10 || true
    else
        token_check_log="$attempt_dir/backend-configure-token-check.log"
        if ! compose run --rm --no-deps backend-api manage shell -c \
            'from options.models import SysOptions; raise SystemExit(0 if SysOptions.objects.filter(key="judge_server_token").exists() else 1)' >"$token_check_log" 2>&1; then
            printf '%s\n' "backend-configure-token: FAIL (key lines; full log: $token_log)" >&2
            grep -nE 'ERROR|error|failed|Traceback|CommandError' "$token_log" | tail -80 >&2 || true
            fail "JudgeServer token initialization failed"
        fi
        printf '%s\n' 'backend-configure-token: PASS (already configured; no overwrite)'
    fi

    run_step judge-token-volume 'PASS|already|error|failed' compose --profile init run --rm --no-deps judge-token-init
    run_step backend-create-admin 'administrator|created|ignored' compose --profile init run --rm --no-deps backend-create-admin
fi

run_step services-ready 'Healthy|healthy' compose up -d --remove-orphans --wait

http_host=127.0.0.1
http_url="http://${http_host}:${HTTP_PORT}"
http_smoke() {
    curl --noproxy '*' --fail --silent --show-error --retry 15 --retry-all-errors --retry-delay 1 "$http_url/" >/dev/null
    curl --noproxy '*' --fail --silent --show-error --retry 15 --retry-all-errors --retry-delay 1 -I "$http_url/admin" | grep -q '301'
    curl --noproxy '*' --fail --silent --show-error --retry 15 --retry-all-errors --retry-delay 1 "$http_url/admin/" >/dev/null
    curl --noproxy '*' --fail --silent --show-error --retry 15 --retry-all-errors --retry-delay 1 "$http_url/api/website/" | grep -q '"error"'
    curl --noproxy '*' --fail --silent --show-error --retry 15 --retry-all-errors --retry-delay 1 "$http_url/runtime-config.js" | grep -q '__XJU_RUNTIME_CONFIG__'
}
run_step http-smoke 'PASS' http_smoke

run_step runtime-worker-smoke 'passed|PASS' compose exec -T backend-api python deploy/worker_smoke.py
run_step runtime-judge-smoke 'passed|PASS' compose exec -T backend-api python -c '
import hashlib, os, requests
with open(os.environ["JUDGE_SERVER_TOKEN_FILE"], encoding="utf-8") as handle:
    token = handle.read().strip()
response = requests.post("http://judge-server:8080/ping", headers={"X-Judge-Server-Token": hashlib.sha256(token.encode()).hexdigest()}, timeout=5)
response.raise_for_status()
assert response.json().get("err") is None
print("Judge /ping passed")
'

heartbeat_ok=0
for i in $(seq 1 20); do
    if compose exec -T backend-api python manage.py shell -c \
        'from conf.models import JudgeServer; raise SystemExit(0 if JudgeServer.objects.filter(is_disabled=False).exists() else 1)' >/dev/null 2>&1; then
        heartbeat_ok=1
        break
    fi
    sleep 1
done
[ "$heartbeat_ok" -eq 1 ] || fail "JudgeServer heartbeat was not observed"

release_dir="$RUNTIME_ROOT/deployments"
if [ -f "$release_dir/current.json" ]; then
    cp "$release_dir/current.json" "$release_dir/previous.json"
fi
image_id() {
    docker image inspect --format '{{.Id}}' "$1"
}
compose_hash=$(sha256sum "$COMPOSE_FILE" | awk '{print $1}')
cat > "$attempt_dir/release.json" <<EOF
{
  "source_commit": "${GIT_COMMIT:-unknown}",
  "compose_sha256": "$compose_hash",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "images": {
    "frontend": {"reference": "$FRONTEND_IMAGE_REF", "image_id": "$(image_id "$FRONTEND_IMAGE_REF")"},
    "backend": {"reference": "$BACKEND_IMAGE_REF", "image_id": "$(image_id "$BACKEND_IMAGE_REF")"},
    "server": {"reference": "$JUDGE_IMAGE_REF", "image_id": "$(image_id "$JUDGE_IMAGE_REF")"}
  }
}
EOF
mv "$attempt_dir/release.json" "$release_dir/current.json"
cp "$release_dir/current.json" "$attempt_dir/release-success.json"

trap - EXIT
printf '%s\n' "deploy succeeded; release metadata written to $release_dir/current.json"
