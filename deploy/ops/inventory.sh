#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$ROOT/.env"}
COMPOSE_FILE=${COMPOSE_FILE:-"$ROOT/compose.yaml"}
[ -f "$ENV_FILE" ] || { printf '%s\n' "inventory: env file is required" >&2; exit 1; }
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

[ -n "${BACKUP_ROOT:-}" ] || { printf '%s\n' "inventory: BACKUP_ROOT is required" >&2; exit 1; }
[ -n "${RUNTIME_ROOT:-}" ] || { printf '%s\n' "inventory: RUNTIME_ROOT is required" >&2; exit 1; }

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

umask 077
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
out="$BACKUP_ROOT/inventory/$timestamp"
mkdir -p "$out"

{
    printf '%s\n' "format=xju-oj-phase2-inventory-v1"
    printf '%s\n' "created_at=$timestamp"
    printf '%s\n' "compose_sha256=$(sha256sum "$COMPOSE_FILE" | awk '{print $1}')"
    printf '%s\n' "runtime_root=$RUNTIME_ROOT"
    printf '%s\n' "postgres_image=$POSTGRES_IMAGE_REF"
    printf '%s\n' "redis_image=$REDIS_IMAGE_REF"

    printf '%s\n' '[runtime files]'
    for path in backend/public backend/test_case judge-server/log judge-server/run; do
        runtime_path="$RUNTIME_ROOT/$path"
        if [ ! -d "$runtime_path" ]; then
            printf '%s files=0 bytes=0\n' "$path"
        elif [ ! -r "$runtime_path" ] || [ ! -x "$runtime_path" ]; then
            # WSL rootless containers may leave a bind-mounted directory owned by an unmapped UID.
            # Record the access boundary instead of emitting noisy permission errors or claiming zero files.
            printf '%s files=unavailable bytes=unavailable access=denied\n' "$path"
        else
            count=$(find "$runtime_path" -type f 2>/dev/null | wc -l | tr -d ' ')
            bytes=$(du -sb "$runtime_path" 2>/dev/null | awk 'NR == 1 {print $1}')
            if [ -n "$bytes" ]; then
                printf '%s files=%s bytes=%s\n' "$path" "$count" "$bytes"
            else
                printf '%s files=%s bytes=unavailable access=partial\n' "$path" "$count"
            fi
        fi
    done

    printf '%s\n' '[postgres]'
    compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
        "select current_setting('server_version'), current_setting('server_encoding'), current_setting('TimeZone'), pg_database_size(current_database());"
    compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
        "select count(*) from django_migrations;"

    printf '%s\n' '[redis]'
    compose exec -T redis redis-cli INFO server | awk -F: '/^redis_version:/{print}'
    compose exec -T redis redis-cli -n 1 INFO keyspace | awk '/^db1:/{print}'
    compose exec -T redis redis-cli -n 4 INFO keyspace | awk '/^db4:/{print}'
    printf '%s\n' "db1_waiting_queue_length=$(compose exec -T redis redis-cli -n 1 LLEN waiting_queue | tr -d '\r')"
} > "$out/manifest.txt"

sha256sum "$out/manifest.txt" > "$out/manifest.sha256"
printf '%s\n' "inventory written: $out"
