# Modernization Compatibility Contract

> Step 00 contract. These behaviors are frozen before implementation work. A change requires a characterization test, an explicit compatibility decision, and a rollback point.

## Browser and API

- Browser clients continue to access the backend same-origin through `/api`; no cross-origin Cookie design is introduced.
- Preserve Django Session and `csrftoken` behavior, `X-CSRFToken`, Referer/Origin checks, and the existing login/session lifecycle.
- Preserve the response envelope `{"error": ..., "data": ...}`, existing result keys, pagination parameters, and status/error semantics.
- Preserve `/admin/` history fallback, `/admin` → `/admin/`, `/public/`, uploads, and both SPA entry points.
- Frontend gateway changes must not expose backend or JudgeServer ports directly to the host.

## Django and database

- Do not change Django app labels, `db_table`, applied migration names, migration dependency history, or `DEFAULT_AUTO_FIELD`.
- Do not run production `makemigrations` or `migrate` as part of a build or image entrypoint.
- PostgreSQL major upgrades are fresh-cluster restore/cutover operations. Every PostgreSQL generation has a distinct runtime directory and rollback volume; the old PG10 directory is never mounted into PG18.
- JSON/JSONB values, indexes, constraints, owners, sequences, collation assumptions, and migration history require explicit restore evidence before cutover.
- Psycopg2 → psycopg3 is an application migration separate from the PostgreSQL server cutover.

## Redis and queues

- Redis DB1 continues to carry Session/cache/`waiting_queue`; Redis DB4 continues to carry Dramatiq broker/result data.
- `waiting_queue` is accounted for separately during every ladder rehearsal; it is not silently flushed.
- Redis 4 → 6.2.23 → 7.4.10 → 8.2.8 is a sequence of independent windows with real snapshot clones and rollback evidence.
- Queue drain, producer shutdown, worker stop, snapshot manifests, and post-restore accounting are mandatory. `docker compose down -v`, volume pruning, and Redis clearing are prohibited.

## JudgeServer protocol

- Keep `/judge`, `/compile_spj`, `/ping`, heartbeat, Token SHA-256 header semantics, the Judge `err`/`data` envelope, and result field names.
- `/test_case` is read-only inside JudgeServer. Fixed compiler/code/SPJ identities, resource limits, and Seccomp boundaries cannot be weakened.
- Judge starts as root only where required by the existing security model and Judger drops to the fixed UID/GID identities. The server service must not use `privileged`, Docker socket access, or `SYS_ADMIN`.
- JudgeServer remains internal on Compose networks; it does not publish port 8080 to the host.
- amd64 is the production architecture. arm64 is experimental until the complete protocol, compiler, resource, and Seccomp corpus is green.

## Build and deployment

- Build inputs are lockfiles plus immutable image digests; `latest`, `main`, floating `stable`, or an unrecorded tag cannot be a production rollback reference.
- Frontend, backend, server, and toolchain digests, source SHA, configuration version, and release time are recorded without secrets.
- Backend API, worker, migration, and bootstrap roles may share an image but remain separate runtime roles. Frontend is the only service permitted to publish host ports.
- Runtime roots are absolute, not `/`, outside the Git worktree's unignored sensitive paths, and use distinct PostgreSQL/Redis generations. `deploy.sh` checks required paths, permissions, and non-empty secret files without creating, printing, overwriting, or echoing their contents.
- Missing production Django Secret fails closed; production secrets are supplied only through the approved command-line/`.env` mechanism and never committed, copied into image layers, or printed in ordinary logs.

## Rollback contract

- Each frontend bridge/final, backend dependency/framework, Redis hop, PostgreSQL target, Judge toolchain, Compose/deploy, and final release has an independent rollback label and evidence set.
- A schema or message-format change first requires an expand/compatibility window; rollback is not approved while old workers/clients cannot safely consume the data.
- A failed Step stops at that Step's commit with logs, digests, test results, and data snapshot metadata preserved. No reset, squash, amend, destructive database command, or destructive Docker cleanup is allowed.
