import hashlib
import os
import sys

import requests


def configured_token():
    token_file = os.environ.get("TOKEN_FILE")
    if token_file:
        try:
            with open(token_file, "r", encoding="utf-8") as handle:
                value = handle.read().strip()
            if value:
                return value
        except OSError:
            pass
    value = os.environ.get("TOKEN", "").strip()
    return value or None


def main():
    raw_token = configured_token()
    if not raw_token:
        return 1
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    response = requests.post(
        "http://127.0.0.1:8080/ping",
        headers={"X-Judge-Server-Token": digest},
        timeout=3,
    )
    response.raise_for_status()
    payload = response.json()
    return 0 if payload.get("err") is None and payload.get("data", {}).get("action") == "pong" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(1)
