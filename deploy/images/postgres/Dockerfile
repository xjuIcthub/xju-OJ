# syntax=docker/dockerfile:1.7
ARG GO_IMAGE=golang:1.26.5-bookworm@sha256:53eeac89074db483fdf0ab3be1df32bf6e47562263d2d0d6baa7f26acb4957dd
ARG POSTGRES_IMAGE=postgres:18.6-alpine@sha256:d3e1620b530c944afa6e887d22eb899824da68e19c52024bf98f5220c88a65b2

FROM ${GO_IMAGE} AS gosu-builder
ARG GOSU_COMMIT=6456aaa0f3c854d199d0f037f068eb97515b7513
ENV CGO_ENABLED=0
WORKDIR /src/gosu
RUN set -eux; \
    git init .; \
    git remote add origin https://github.com/tianon/gosu.git; \
    git fetch --depth 1 origin "$GOSU_COMMIT"; \
    git checkout --detach FETCH_HEAD; \
    test "$(git rev-parse HEAD)" = "$GOSU_COMMIT"
RUN set -eux; \
    go mod download; \
    go build -trimpath -ldflags='-d -w' -o /out/gosu .; \
    go version -m /out/gosu; \
    /out/gosu --version

FROM ${POSTGRES_IMAGE}
COPY --from=gosu-builder /out/gosu /usr/local/bin/gosu
RUN set -eux; \
    test "$(postgres --version)" = 'postgres (PostgreSQL) 18.6'; \
    gosu --version; \
    gosu postgres id
