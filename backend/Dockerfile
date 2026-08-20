FROM python:3.12-alpine

ARG TARGETARCH
ARG TARGETVARIANT

ENV OJ_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./deploy/requirements.txt /app/deploy/requirements.txt

RUN --mount=type=cache,target=/var/cache/apk,id=backend-apk-$TARGETARCH$TARGETVARIANT,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,id=backend-pip-$TARGETARCH$TARGETVARIANT,sharing=locked \
    set -eux; \
    apk add --no-cache \
        libpq \
        libjpeg-turbo \
        zlib \
        freetype \
        su-exec; \
    apk add --no-cache --virtual .build-deps \
        gcc \
        libc-dev \
        python3-dev \
        libpq-dev \
        libjpeg-turbo-dev \
        zlib-dev \
        freetype-dev; \
    python3 -m pip install --no-cache-dir -r /app/deploy/requirements.txt; \
    apk del .build-deps

COPY ./ /app/

RUN set -eux; \
    addgroup -S backend; \
    adduser -S -D -H -G backend backend; \
    chmod -R u=rwX,go=rX /app; \
    chmod +x /app/deploy/entrypoint.sh; \
    chown -R backend:backend /app

EXPOSE 8000
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["api"]
