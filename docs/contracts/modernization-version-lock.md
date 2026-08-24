# Modernization Version Lock

> Step 00 decision source for the 2026 modernization. This file records facts rechecked during the Step 00 run; a later Step may change a version only through an explicit lock update and a new rollback point.
>
> Rechecked: 2026-08-23. Repository baseline: `d59d274ce3237bb10165fc9afadc4260aa79c359` on `main`.

## Non-negotiable constraints

- Production host: supported Ubuntu `>=22.04`; the verified target is Ubuntu `22.04`.
- Backend and JudgeServer production Python: `>=3.10,<3.11`. No Step 00–30 command may silently select Python 3.11+.
- Judge starts as root and drops to the fixed runtime identities defined by the existing Judge contract. No `privileged`, Docker socket, or `SYS_ADMIN` for the server service.
- Only frontend may publish host ports. Backend and JudgeServer remain on Compose networks.
- PostgreSQL and Redis generations use separate runtime directories/volumes. Existing data directories are never reused in-place for a major upgrade.
- Secrets, credentials, user data, dumps, RDB/AOF files, cookies, and tokens are never committed or written to ordinary logs.

## Host and container-tool facts

| Item | Rechecked value | Evidence/source |
|---|---|---|
| Host OS | Ubuntu `22.04` | `huawei1`: `/etc/os-release` |
| Kernel | `5.15.0-186-generic` | `huawei1`: `uname -r` |
| Architecture | `x86_64` | `huawei1`: `uname -m` |
| cgroup | v2 detected (`/sys/fs/cgroup/cgroup.controllers`) | `huawei1` preflight query |
| Docker Engine | `29.7.1` | `docker version --format '{{.Server.Version}}'` |
| Compose | `v5.4.0` | `docker compose version` |
| Buildx | `v0.36.0` | `docker buildx version` |
| Host Python | `3.10.12` | `huawei1`: `python3 --version` |
| Host Node | `v24.16.0` | local baseline query; not a production lock |
| Host pnpm | `10.14.0` | local baseline query; not a production lock |
| Host uv | `0.9.17` | local baseline query; not a production lock |

Ubuntu support status and the runtime-root/path/permission gates remain mandatory in Step 03; this Step does not treat a version string alone as deployment approval.

## Locked platform decisions

| Component | Production/bridge decision | Status label | Immutable source or lock rule | Rollback boundary |
|---|---|---|---|---|
| Python | **3.10.x only**; use maintained latest patch in the `3.10` line, currently locked for image resolution as `3.10.21` | security-maintained feature line; not LTS terminology | Official Python lifecycle plus Docker Official Image `python:3.10-slim-bookworm@sha256:7ed92b32353e8d8bd865b5ba811e0315d3999c3b57b1c2df2b504a359d4a1707` (manifest digest queried 2026-08-23) | backend/Judge image tag and digest |
| Node | `24.19.0` | **Active LTS** | Official `node:24.19.0-bookworm-slim@sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03` | frontend release |
| pnpm | `11.22.0`; pnpm 12 RC is forbidden | stable; no LTS label | pnpm official installation/compatibility page and frozen lockfile | frontend lock |
| Vite | bridge `7.3.6`, final `8.2.1` | supported stable minor; no LTS label | Vite release metadata; bridge and final are separate releases | frontend bridge/final |
| Vue | bridge `2.7.16`, final `3.5.41` | Vue 2 EOL bridge; Vue 3 stable | Vue/npm release metadata | frontend bridge/final |
| Django | `4.2.30` only as a compatibility checkpoint, then `5.2.17` | 5.2 LTS target; 4.2 is not a production target | Django release/support matrix | backend framework release |
| uv | `0.12.5` | stable; no LTS label | Astral official release/docs; `uv.lock` must be committed | backend dependency-manager release |
| PostgreSQL | **18.6 primary**, `17.11` fallback only after a documented PG18 blocker | supported major; no LTS label | `postgres:18.6-bookworm@sha256:7d2695c3aa88e792e8b3b233e7e4adb296a20412c6c0ca361e3edaaacfada108`; fallback `postgres:17.11-bookworm@sha256:84560e3b9c6874893fc4e2854f5dc3e7c1a37bc9d1dfd7a8c641310ae22ba5ad` | independent DB release and fresh runtime root |
| Redis | `6.2.23` → `7.4.10` → `8.2.8`; no direct 4→8.2 cutover | GA/Extended as applicable; no OSS LTS label | `redis:6.2.23-bookworm@sha256:a873de27e877d8ea401f530a4c7571bae34882a7178a0a0f3df12263bfba14a5` → `redis:7.4.10-bookworm@sha256:e9b2e45ecd47fbb69b877cf8d045d5cccaaaed52524b6e098b4abe8212994f73` → `redis:8.2.8-bookworm@sha256:2f7462b9e93e0a7ae2edf3a0a0babc8a4d29f8bfc50849b906b7caaef925edc1` | independent Redis release/volume |
| Debian Judge base | Debian `13`/Trixie | stable; later LTS maintenance | `debian:trixie-slim@sha256:3a39a0592364683e6bab97937b72cad5a8fa6dcbbee90edb3bb48c7f8e94f258` | Judge toolchain release |
| Judge compiler/runtime | Python 3.10, GCC 14.2, OpenJDK 21, Go 1.26.x, Node 24, libseccomp 2.6.x; amd64 production, arm64 experimental until green | mixed official status; never label all as LTS | per-tool official release metadata and toolchain image digest | independent Judge toolchain release |

The Python image digest above is an OCI manifest digest for the official multi-architecture tag; `docker run ... python --version` on `huawei1` returned `3.10.21` for the amd64 image. Step 13 must still verify the interpreter ABI inside the selected architecture image before any production build. A mutable tag must never be used without this digest.

## Phase 3 exact application pins

The WSL Phase 3 final lock resolved and froze these exact patches; later changes require a new lock diff and rollback point.

| Lane | Exact final versions |
|---|---|
| Frontend core | Vue `3.5.41`, Vue Router `5.2.0`, vue-i18n `11.4.8`, Pinia `4.0.3`, Element Plus `2.14.4`, Vite `8.2.1`, `@vitejs/plugin-vue` `6.0.8` |
| Frontend editors/visuals | Tiptap `3.30.3` packages, CodeMirror state `6.7.1` / view `6.43.9` / commands `6.11.0`, ECharts `6.1.0`, vue-echarts `8.1.0`, KaTeX `0.16.39`, highlight.js `11.11.1` |
| Backend framework/driver | Django `5.2.17`, Psycopg `[c] 3.3.4`, DRF `3.18.0`, Python `>=3.10,<3.11` |
| Backend cache/worker | django-redis `7.0.0`, redis-py `7.4.1` with RESP2 semantics, Dramatiq `2.2.0`, django-dramatiq `0.15.0` |
| Backend compatibility | jsonfield `3.2.0` for historical migration loading, django-cas-ng `5.1.1`, django-dbconn-retry `0.3.1`, sentry-sdk `[django] 2.68.0` |

## Resolved research conflicts

1. **Python 3.10 vs research recommendation for 3.13:** the user-specified `>=3.10,<3.11` production feature line overrides the research recommendation. Python 3.13 is not introduced by any production command in this plan.
2. **pnpm 11.21 vs 11.22:** the unified plan selects the official stable `11.22.0`; the RC `next-12` line is excluded.
3. **PostgreSQL 17 vs 18:** PG18.6 is the primary plan decision because the current plan requires a fresh PG18 restore rehearsal; PG17.11 remains a pre-approved fallback only if that rehearsal records a blocker.
4. **Redis 7.4/8.0/8.2 and Valkey:** Redis 8.0 is skipped, Redis 8.2.8 is the final target, and Valkey is a separate future project. The Redis ladder is mandatory.
5. **LTS terminology:** only products that officially use LTS (for example Node 24, Django 5.2, and OpenJDK 21) receive that label. pnpm, Vite, Python, PostgreSQL, Redis OSS, Go, and GCC are recorded with their official support terminology instead.

## Evidence sources

- Python lifecycle: <https://devguide.python.org/versions/>.
- Docker Official Image metadata: <https://hub.docker.com/_/python> (manifest query for `3.10-slim-bookworm`, digest recorded above).
- Node releases: <https://nodejs.org/en/about/previous-releases>.
- pnpm installation and compatibility: <https://pnpm.io/installation>.
- The seven checked research reports under `docs/research/` supply the project-specific compatibility and rollback rationale; their conflicting recommendations are resolved above by the plan and user constraints.

## Stop gates carried forward

- If Python 3.10 loses maintained security patches or the official image cannot be rebuilt from a verified digest, stop before production release; do not upgrade the feature line silently.
- If an exact digest cannot be recorded for a future production image, that image cannot enter Compose or a release.
- PG18 cannot be promoted without fresh-restore, extension, collation, sequence, and application evidence. Otherwise use the recorded PG17 fallback decision process.
- No candidate may alter app labels, table names, applied migration names/dependency history, Redis DB1/DB4 responsibilities, or the Judge protocol/security boundary.
