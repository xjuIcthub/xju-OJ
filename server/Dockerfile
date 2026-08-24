# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.10-slim-bookworm@sha256:7ed92b32353e8d8bd865b5ba811e0315d3999c3b57b1c2df2b504a359d4a1707
ARG GCC_IMAGE=gcc:14-trixie@sha256:468b5b959b5f4025724d8549f45550c6ad38a32474733cbf130f8f2c1bc80805
ARG NODE_IMAGE=node:24.19.0-bookworm-slim@sha256:3638d9a6fe4030bd716be989438248074489337ba3275657f93595428be4fc03
ARG GO_IMAGE=golang:1.26.5-bookworm@sha256:53eeac89074db483fdf0ab3be1df32bf6e47562263d2d0d6baa7f26acb4957dd
ARG JAVA_IMAGE=eclipse-temurin:21-jdk@sha256:85f00967bcc624fc19fa9c2cf124ea426a5363898e267141726f31f358c2e14b
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1

FROM ${PYTHON_IMAGE} AS python-runtime
FROM ${NODE_IMAGE} AS node-runtime
FROM ${GO_IMAGE} AS go-runtime
FROM ${JAVA_IMAGE} AS java-runtime
FROM ${UV_IMAGE} AS uv-runtime

FROM ${GCC_IMAGE} AS judge-toolchain
ARG TARGETARCH
ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:/usr/local/go/bin:/usr/local/bin:$PATH

COPY --from=python-runtime /usr/local /usr/local
COPY --from=node-runtime /usr/local /usr/local
COPY --from=go-runtime /usr/local/go /usr/local/go
COPY --from=java-runtime /opt/java/openjdk /opt/java/openjdk
COPY --from=uv-runtime /uv /uvx /usr/local/bin/

RUN set -eux; \
    sed -i \
        -e 's|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' \
        -e 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
        -e 's|https://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' \
        -e 's|https://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
        /etc/apt/sources.list.d/debian.sources; \
    apt-get -o Acquire::Retries=5 update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libfreetype6 \
        libjpeg62-turbo \
        libseccomp2 \
        strace \
        zlib1g; \
    ln -sf /usr/local/bin/gcc /usr/bin/gcc; \
    ln -sf /usr/local/bin/g++ /usr/bin/g++; \
    ln -sf /usr/local/bin/python3 /usr/bin/python; \
    ln -sf /usr/local/bin/python3 /usr/bin/python3; \
    ln -sf /usr/local/bin/node /usr/bin/node; \
    ln -sf /usr/local/go/bin/go /usr/bin/go; \
    ln -sf /opt/java/openjdk/bin/java /usr/bin/java; \
    ln -sf /opt/java/openjdk/bin/javac /usr/bin/javac; \
    rm -rf /var/lib/apt/lists/*; \
    useradd --uid 901 --system --home-dir /nonexistent --shell /usr/sbin/nologin compiler; \
    useradd --uid 902 --system --home-dir /nonexistent --shell /usr/sbin/nologin code; \
    useradd --uid 903 --system --home-dir /nonexistent --shell /usr/sbin/nologin --groups code spj; \
    mkdir -p /usr/lib/judger /app /judger/run /judger/spj /log /test_case; \
    chmod 755 /app /usr/lib/judger /test_case; \
    chmod 770 /log /judger /judger/run /judger/spj

FROM judge-toolchain AS judger-build
ARG TARGETARCH
RUN set -eux; \
    sed -i \
        -e 's|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' \
        -e 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
        -e 's|https://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' \
        -e 's|https://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
        /etc/apt/sources.list.d/debian.sources; \
    apt-get -o Acquire::Retries=5 update; \
    apt-get install -y --no-install-recommends cmake libseccomp-dev make; \
    rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY server/judger/ /src/judger/
RUN --mount=type=cache,target=/root/.cache/cmake,id=judger-cmake-${TARGETARCH},sharing=locked \
    set -eux; \
    cmake -S /src/judger -B /src/judger/build; \
    cmake --build /src/judger/build --parallel "$(nproc)"
RUN set -eux; \
    cd /src/judger/bindings/Python; \
    uv build --wheel --no-build-isolation --out-dir /src/judger-wheel

FROM judge-toolchain AS judge-server-deps
ARG TARGETARCH
WORKDIR /app
COPY server/judge-server/pyproject.toml server/judge-server/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv,id=judge-uv-${TARGETARCH}-py310,sharing=locked \
    uv sync --locked --no-dev --no-install-project

FROM judge-toolchain AS judge-server
ARG VCS_REF=unknown
ARG BUILD_VERSION=phase1
ENV PATH=/app/.venv/bin:/opt/java/openjdk/bin:/usr/local/go/bin:/usr/local/bin:$PATH
WORKDIR /app
COPY --from=judge-server-deps /app/.venv /app/.venv
COPY --from=judger-build /src/judger/output/libjudger.so /usr/lib/judger/libjudger.so
COPY --from=judger-build /src/judger-wheel/*.whl /tmp/
RUN set -eux; \
    uv pip install --python /app/.venv/bin/python --no-deps /tmp/*.whl; \
    rm -f /tmp/*.whl
COPY server/judge-server/server/ /app/
RUN set -eux; \
    chmod -R u=rwX,go=rX /app; \
    chmod +x /app/entrypoint.sh; \
    gcc -shared -fPIC -o /app/unbuffer.so /app/unbuffer.c

LABEL org.opencontainers.image.source="xju-OJ" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.version="$BUILD_VERSION"

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 CMD ["/app/.venv/bin/python", "/app/healthcheck.py"]
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
