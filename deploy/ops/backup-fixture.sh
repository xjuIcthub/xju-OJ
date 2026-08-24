#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ENV_FILE=${ENV_FILE:-"$ROOT/.env"}
COMPOSE_FILE=${COMPOSE_FILE:-"$ROOT/compose.yaml"}
[ -f "$ENV_FILE" ] || { printf '%s\n' "backup: env file is required" >&2; exit 1; }
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

[ -n "${BACKUP_ROOT:-}" ] || { printf '%s\n' "backup: BACKUP_ROOT is required" >&2; exit 1; }
[ -n "${RUNTIME_ROOT:-}" ] || { printf '%s\n' "backup: RUNTIME_ROOT is required" >&2; exit 1; }

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

umask 077
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
out="$BACKUP_ROOT/fixture/$timestamp"
mkdir -p "$out/postgres" "$out/redis" "$out/runtime"

postgres_id=$(compose ps -q postgres)
redis_id=$(compose ps -q redis)
[ -n "$postgres_id" ] || { printf '%s\n' "backup: postgres container is not running" >&2; exit 1; }
[ -n "$redis_id" ] || { printf '%s\n' "backup: redis container is not running" >&2; exit 1; }

docker exec "$postgres_id" sh -c "rm -rf /tmp/xju-oj-pg-dump && pg_dumpall -U '$POSTGRES_USER' --globals-only > /tmp/xju-oj-pg-globals.sql && pg_dump -U '$POSTGRES_USER' -Fd -j 2 -f /tmp/xju-oj-pg-dump '$POSTGRES_DB'"
docker cp "$postgres_id:/tmp/xju-oj-pg-globals.sql" "$out/postgres/globals.sql"
docker cp "$postgres_id:/tmp/xju-oj-pg-dump" "$out/postgres/database"
docker exec "$postgres_id" rm -rf /tmp/xju-oj-pg-dump /tmp/xju-oj-pg-globals.sql

docker exec "$redis_id" sh -c 'redis-cli --rdb /tmp/xju-oj-redis.rdb >/dev/null'
docker cp "$redis_id:/tmp/xju-oj-redis.rdb" "$out/redis/redis.rdb"
docker exec "$redis_id" rm -f /tmp/xju-oj-redis.rdb

# Only public/test_case runtime data is copied; config/secret and logs stay outside the artifact.
tar -C "$RUNTIME_ROOT" --numeric-owner -cf "$out/runtime/public-test-case.tar" backend/public backend/test_case

{
    printf '%s\n' "format=xju-oj-phase2-fixture-backup-v1"
    printf '%s\n' "created_at=$timestamp"
    printf '%s\n' "postgres_image=$POSTGRES_IMAGE_REF"
    printf '%s\n' "redis_image=$REDIS_IMAGE_REF"
    printf '%s\n' "postgres_database=$POSTGRES_DB"
    printf '%s\n' "runtime_scope=backend/public backend/test_case"
} > "$out/manifest.txt"

find "$out" -type f -print0 | sort -z | xargs -0 sha256sum > "$out/sha256sums"
printf '%s\n' "fixture backup written: $out"
