# Source Inventory Baseline

> Step 02 inventory captured 2026-08-23 from `main` at `3e209be8e5574aa4f4ec211dc0da2ce054e0f358`. Counts exclude `frontend/node_modules` and Python `__pycache__` for source files.

## Counts and build roots

| Measurement | Actual value |
|---|---:|
| `frontend` + `backend` + `server` source files | 554 |
| Git-tracked files | 534 |
| Research reports | 7 |
| `frontend` tree size | 379M (includes local ignored `node_modules`/dist data) |
| `backend` tree size | 4.4M |
| `server` tree size | 932K |

The exact inventory commands were the Step 02 plan commands. Their temporary path lists were not committed because they contain no migration value beyond the counts and the tracked Git tree.

## Frontend

- Real entries: `frontend/src/pages/oj/index.js` and `frontend/src/pages/admin/index.js`.
- User Router and admin Router both use history mode; admin base is `/admin/`.
- Axios sets `baseURL=/api`, `xsrfHeaderName=X-CSRFToken`, and `xsrfCookieName=csrftoken` in both API modules.
- Current package manager is Yarn Classic (`frontend/yarn.lock`, lockfile v1); `package.json` has no `packageManager` field. `.nvmrc` is `14.21.3`; package engines still say Node `>=4.0.0` and npm `>=3.0.0`.
- Direct dependency count: 52 production + 23 development = 75. The lock contains 1,109 top-level lock entry lines.
- Observed implicit installed dependencies: `jquery` and `codemirror` exist in the ignored `node_modules` tree but are not direct declarations in `package.json`. `element-ui` and `iview` are direct; the `tar-simditor` packages are the current editor path.
- Compatibility pattern counts: `.sync` 14, `.native` 13, `slot-scope` 9, `new Vue` 6, `Vue.prototype` 6 across the inspected source set.
- The current production asset path is `/__STATIC_CDN_HOST__/`; this is recorded as a baseline dependency/configuration issue, not changed here.

## Backend

- Direct requirements: 23 pinned lines in `backend/deploy/requirements.txt`.
- Current Docker base is `python:3.12-alpine`; this is a recorded baseline difference from the Step 00 production Python 3.10 lock and is not changed in Step 02.
- `deploy/entrypoint.sh` has `bootstrap-runtime`, `migrate`, `configure-judge-token`, `create-initial-admin`, `api`, `worker`, and `manage` roles. It creates runtime directories only when explicitly invoked and keeps the private config directory separate from frontend public data.
- URL inventory: 14 files import `django.conf.urls`, with 75 `url(...)` calls. JSONField inventory: 6 files import the current JSONField shim and 8 files retain historical `jsonfield.fields` references.
- Settings freeze `DEFAULT_AUTO_FIELD=django.db.models.AutoField`, cache/session Redis DB1, and Dramatiq broker/result Redis DB4.
- The current dependency set includes Django 3.2.25, DRF 3.14.0, psycopg2 2.9.9, redis 4.6.0, django-redis 5.4.0, Dramatiq 1.16.0, and raven 6.10.0.

## Server/Judge

- The current CMake project is `server/judger`, with C99, `-Werror`, `-O3`, PIE/PIC, pthread, and libseccomp linkage.
- Current Judge runtime identities in the Dockerfile are compiler UID 901, code UID 902, and spj UID 903.
- `server/judge-server/Dockerfile` expects `COPY Judger/` and `COPY server/`; the repository has lowercase `server/judger` and `server/judge-server/server`, and no `server/Judger` directory. This build-context/case mismatch is a recorded blocker for the later server-boundary Step.
- The current Dockerfile also names Python 3.12, Go 1.22, NodeSource 20, GCC 13, and Debian Trixie, all recorded as baseline facts rather than silently corrected here.
- Existing positive/negative Judge protocol and Judger corpus paths are listed in `docs/contracts/judge-protocol.md` and the Step 01 inventory.

## Deploy/data boundary

- The root Compose still has Redis 4.0 Alpine, PostgreSQL 10 Alpine, a remote Judge `1.6.1`, and a remote backend `1.6.1`; it publishes backend ports 80 and 443 and has no frontend service.
- The Compose volume roles are `./data/redis:/data`, `./data/postgres:/var/lib/postgresql/data`, `./data/backend:/data`, and Judge test-case/log/run mounts. Exact mode/path facts are in `runtime-volume-inventory.md`.
- Compose validation passed with only the warning that the obsolete top-level `version` attribute is ignored.
