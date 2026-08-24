import _judger
import hashlib
import logging
import os
import socket
import stat

import psutil

from config import SERVER_LOG_PATH
from exception import JudgeClientError

logger = logging.getLogger(__name__)
handler = logging.FileHandler(SERVER_LOG_PATH)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)


def server_info():
    ver = _judger.VERSION
    return {"hostname": socket.gethostname(),
            "cpu": psutil.cpu_percent(),
            "cpu_core": psutil.cpu_count(),
            "memory": psutil.virtual_memory().percent,
            "judger_version": ".".join([str((ver >> 16) & 0xff), str((ver >> 8) & 0xff), str(ver & 0xff)])}


def open_root_lock(path):
    fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
    file_stat = os.fstat(fd)
    if (not stat.S_ISREG(file_stat.st_mode) or file_stat.st_uid != 0 or
            file_stat.st_gid != 0 or file_stat.st_nlink != 1 or
            stat.S_IMODE(file_stat.st_mode) != 0o600):
        os.close(fd)
        raise JudgeClientError("invalid judge lock file")
    return os.fdopen(fd, "r+")


def get_token():
    token_file = os.environ.get("TOKEN_FILE")
    if token_file:
        try:
            with open(token_file, "r", encoding="utf-8") as handle:
                token = handle.read().strip()
            if token:
                return token
        except OSError:
            pass

    token = os.environ.get("TOKEN")
    if token:
        return token
    raise JudgeClientError("judge token not configured")


class ProblemIOMode:
    standard = "Standard IO"
    file = "File IO"


token = hashlib.sha256(get_token().encode("utf-8")).hexdigest()
