# Build Baseline

> Measurements captured 2026-08-23 in isolated temporary directories/containers. They describe the current source and build graph; no production image was retagged or published.

## Frontend Webpack baseline

Command shape:

```text
npm run build --prefix /tmp/xju-oj-step02-frontend
```

The cold build with the current Node `v24.16.0` failed in 1.15 seconds with `ERR_OSSL_EVP_UNSUPPORTED` from the old `babel-loader` filesystem cache. This is a real current-toolchain compatibility blocker.

With the explicitly recorded compatibility workaround `NODE_OPTIONS=--openssl-legacy-provider` (not a production fix), the same current source and existing dependency tree produced:

| Run | Time | Max RSS | Result |
|---|---:|---:|---|
| cold | 16.91 s | 1,097,452 KB | passed |
| warm | 8.17 s | 966,424 KB | passed |

The isolated output was 7.8M across 79 files and produced both `index.html` and `admin/index.html`. The output directory was outside the repository and was removed after measurement.

## Backend image baseline

Current `backend/Dockerfile` was built with Buildx using host proxy/network settings needed by the sandbox:

| Run | Time | Max RSS | Result |
|---|---:|---:|---|
| cold (`--no-cache`) | 142.03 s | 52,608 KB | passed |
| warm | 1.35 s | 52,224 KB | passed |

The current image uses the Docker-resolved `python:3.12-alpine` base and is not a Step 00 production image. Temporary tags `xju-oj-step02-backend:cold` and `:warm` were removed after the measurement; no registry push occurred.

## Judger C/libseccomp baseline

- Native Ubuntu compile configured with CMake in 1.68 s but failed during compilation because the host lacks `seccomp.h`.
- An isolated Debian Bookworm container with `build-essential`, CMake, and `libseccomp-dev` compiled the current `server/judger` source successfully. The output library was 281,872 bytes.
- Cold container compile including apt/package setup: 171.14 s, 29,440 KB max RSS.
- Warm command: 180.16 s, 29,312 KB max RSS. The second run still installed packages in a new disposable container, so the time is package-install dominated and is not a BuildKit cache hit measurement.
- The generated CMake output was staged outside the repository and removed.

## Global/tooling observations

- Local host: Python 3.10.12, Node 24.16.0, npm 11.13.0, no Yarn executable, CMake 3.30.2, GCC 11.4.0, Docker Engine 28.4.0, Buildx 0.27.0.
- `docker compose config --quiet` passed with the current file and test-only placeholder variables, while warning that the top-level `version` field is obsolete.
- The remote deployment target's verified Docker/Compose/Buildx versions are recorded in the Step 00 lock; the local build host is not treated as the production host.
- No backend/DB/Redis production data was used. All service containers and runtime roots for measurements were temporary.
