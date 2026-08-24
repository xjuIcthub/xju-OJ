#!/usr/local/bin/python3
import os
import sys
import time
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")
django.setup()

from utils.tasks import delete_files  # noqa: E402


path = Path("/data/.worker-smoke-{}".format(os.getpid()))
path.write_text("worker-smoke", encoding="utf-8")
delete_files.send(str(path))

deadline = time.monotonic() + float(os.environ.get("WORKER_SMOKE_TIMEOUT", "20"))
while time.monotonic() < deadline:
    if not path.exists():
        print("worker smoke passed")
        raise SystemExit(0)
    time.sleep(0.2)

print("worker smoke timed out", flush=True)
raise SystemExit(1)
