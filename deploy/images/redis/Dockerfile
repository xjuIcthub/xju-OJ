# syntax=docker/dockerfile:1.7
ARG REDIS_IMAGE=redis:8.2.8-alpine@sha256:a7859ed111db3c1f5404a973a4747505d559fb5ca32d37e447afc0ef845a2103
FROM ${REDIS_IMAGE}
RUN test "$(redis-server --version | awk '{print $3}')" = 'v=8.2.8'
