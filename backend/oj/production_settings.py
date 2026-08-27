import os
from urllib.parse import urlsplit

from utils.shortcuts import get_env, get_env_file

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': get_env("POSTGRES_HOST", "oj-postgres"),
        'PORT': get_env("POSTGRES_PORT", "5432"),
        'NAME': get_env("POSTGRES_DB"),
        'USER': get_env("POSTGRES_USER"),
        'PASSWORD': get_env_file("POSTGRES_PASSWORD", "POSTGRES_PASSWORD_FILE")
    }
}

REDIS_CONF = {
    "host": get_env("REDIS_HOST", "oj-redis"),
    "port": get_env("REDIS_PORT", "6379")
}

DEBUG = False

ALLOWED_HOSTS = ['*']


def _csrf_trusted_origins():
    raw_origins = get_env("CSRF_TRUSTED_ORIGINS", "https://oj.icthub.top")
    origins = [item.strip().rstrip("/") for item in raw_origins.split(",") if item.strip()]
    if not origins:
        raise RuntimeError("CSRF_TRUSTED_ORIGINS must contain at least one HTTPS origin")
    dev_mode = get_env("OJ_DEV_MODE", "0") == "1"
    for origin in origins:
        parsed = urlsplit(origin)
        insecure_loopback = (
            dev_mode
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost"}
        )
        if (parsed.scheme != "https" and not insecure_loopback) or not parsed.netloc or parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError("CSRF_TRUSTED_ORIGINS must contain strict HTTPS origins (or a dev loopback HTTP origin)")
    return origins


CSRF_TRUSTED_ORIGINS = _csrf_trusted_origins()

runtime_root = get_env("RUNTIME_ROOT", "")
DATA_DIR = get_env("OJ_DATA_DIR", os.path.join(runtime_root, "backend") if runtime_root else "/data")
