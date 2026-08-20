#!/usr/local/bin/python3
import json
import os
import sys
import time
from urllib.request import urlopen

from redis import Redis


def redis_client(db):
    return Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=db,
        socket_connect_timeout=3,
        socket_timeout=3,
        decode_responses=True,
    )


def check_api():
    url = os.environ.get("BACKEND_HEALTH_URL", "http://127.0.0.1:8000/api/website/")
    with urlopen(url, timeout=3) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"API returned HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("error") is not None:
        raise RuntimeError("API returned an error")


def check_redis():
    cache = redis_client(1)
    broker = redis_client(4)
    if not cache.ping() or not broker.ping():
        raise RuntimeError("Redis DB 1/4 ping failed")

    key = f"runtime_smoke:{os.getpid()}:{time.time_ns()}"
    cache.set(key, "ok", ex=30)
    try:
        if cache.get(key) != "ok":
            raise RuntimeError("Redis DB 1 probe failed")
    finally:
        cache.delete(key)


if __name__ == "__main__":
    try:
        if "--worker" not in sys.argv:
            check_api()
        check_redis()
    except Exception as exc:
        print(f"backend runtime smoke check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print("backend runtime smoke check passed")
