#!/usr/local/bin/python3
import json
import os
import sys
from urllib.request import urlopen


url = os.environ.get("BACKEND_HEALTH_URL", "http://127.0.0.1:8000/api/website/")
try:
    with urlopen(url, timeout=3) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"unexpected status {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
        if payload.get("error") is not None:
            raise RuntimeError("API returned an error")
except Exception as exc:
    print(f"backend API health check failed: {exc}", file=sys.stderr)
    raise SystemExit(1)

raise SystemExit(0)
