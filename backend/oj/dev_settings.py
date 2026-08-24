# coding=utf-8
import os
from utils.shortcuts import get_env, get_env_file

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': get_env('POSTGRES_HOST', '127.0.0.1'),
        'PORT': get_env('POSTGRES_PORT', '5435'),
        'NAME': get_env('POSTGRES_DB', 'onlinejudge'),
        'USER': get_env('POSTGRES_USER', 'onlinejudge'),
        'PASSWORD': get_env_file('POSTGRES_PASSWORD', 'POSTGRES_PASSWORD_FILE', 'onlinejudge')
    }
}

REDIS_CONF = {
    'host': get_env('REDIS_HOST', '127.0.0.1'),
    'port': get_env('REDIS_PORT', '6380')
}


DEBUG = True

ALLOWED_HOSTS = ["*"]

runtime_root = get_env("RUNTIME_ROOT", "")
DATA_DIR = get_env("OJ_DATA_DIR", os.path.join(runtime_root, "backend") if runtime_root else f"{BASE_DIR}/data")
