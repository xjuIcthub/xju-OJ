# Runtime Volume Inventory

> Step 02 path/permission inventory. Values are local baseline metadata only; no file contents were printed.

## Current Compose mounts

| Service | Host path | Container path | Role | Current declaration |
|---|---|---|---|---|
| `oj-redis` | `./data/redis` | `/data` | Redis 4 persistence | writable |
| `oj-postgres` | `./data/postgres` | `/var/lib/postgresql/data` | PostgreSQL 10 data directory | writable |
| `oj-judge` | `./data/backend/test_case` | `/test_case` | Judge test cases | read-only |
| `oj-judge` | `./data/judge_server/log` | `/log` | Judge logs | writable |
| `oj-judge` | `./data/judge_server/run` | `/judger` | Judge runtime workspace | writable |
| `oj-backend` | `./data/backend` | `/data` | backend runtime/public/config | writable |

The current Compose also publishes backend ports `80:8000` and `443:1443`; this is a recorded baseline mismatch with the Step 00 target topology, where only frontend publishes host ports.

## Local repository runtime metadata

| Path | Mode observed | Handling |
|---|---:|---|
| `backend/data` | 755 | local development runtime root |
| `backend/data/config` | 755 | private config directory; contents never printed |
| `backend/data/config/secret.key` | 600 | ignored by Git (`.gitignore` data rule); not committed or copied into inventory |
| `backend/data/log` | 755 | local logs |
| `backend/data/public` | 755 | frontend-readable public root |
| `backend/data/test_case` | 755 | test-case root |
| `server/judge-server/tests/test_case` | 755 | committed test corpus, not production data |

## Required future gates

- PostgreSQL major upgrades must use a new runtime root/volume and fresh restore; the PG10 directory cannot be mounted into PG18.
- Redis ladder hops must use separate snapshots/roots and preserve DB1/DB4 accounting; no volume pruning or `down -v` is allowed.
- Runtime root ownership, private config permissions, public read-only mounts, test-case read-only mounts, and Judge workspace permissions are rechecked in Step 03/19/22/28.
- Capacity, backup location, restore time, and production owner are deliberately not inferred from this local inventory and remain staging/production preflight work.
