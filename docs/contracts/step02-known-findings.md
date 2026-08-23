# Step 02 Known Findings

1. The current frontend cold build fails under Node 24 without `NODE_OPTIONS=--openssl-legacy-provider` because the Webpack 3/Babel-loader cache requests an unsupported OpenSSL digest. The compatibility workaround passes, but it is not recorded as a production solution.
2. The host lacks the native `libseccomp` development header; the same Judger source compiles in an isolated Debian container after installing `libseccomp-dev`.
3. The current Judge Dockerfile has a case/build-context mismatch (`COPY Judger/` versus the repository's lowercase `server/judger`), and the current Dockerfile's Python/Node/Go/GCC declarations differ from the Step 00 lock.
4. Root Compose still points at floating tags in the file, publishes backend ports, and uses PostgreSQL 10/Redis 4. Exact current manifest digests were recorded in `dependency-inventory.md`; no mismatch was hidden.
5. The local build host has no Yarn executable. The baseline frontend build was run with the existing checked-out dependency tree through `npm run build`; Step 04 must establish pnpm from a clean lock rather than treating this as a successful Yarn installation.

These findings are inventory evidence. They are not fixed in Step 02 so that later Steps can keep one risk axis per commit.
