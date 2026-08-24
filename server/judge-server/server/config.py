import os
import pwd

import grp

JUDGER_WORKSPACE_BASE = "/judger/run"
JUDGER_LOCK_BASE = "/judger/locks"
COMPILER_LOCK_PATH = os.path.join(JUDGER_LOCK_BASE, "compiler.lock")
FILE_IO_LOCK_PATH = os.path.join(JUDGER_LOCK_BASE, "file-io.lock")
LOG_BASE = "/log"

COMPILER_LOG_PATH = os.path.join(LOG_BASE, "compile.log")
JUDGER_RUN_LOG_PATH = os.path.join(LOG_BASE, "judger.log")
SERVER_LOG_PATH = os.path.join(LOG_BASE, "judge_server.log")

RUN_USER_UID = pwd.getpwnam("code").pw_uid
RUN_GROUP_GID = grp.getgrnam("code").gr_gid

COMPILER_USER_UID = pwd.getpwnam("compiler").pw_uid
COMPILER_GROUP_GID = grp.getgrnam("compiler").gr_gid

SPJ_USER_UID = pwd.getpwnam("spj").pw_uid
SPJ_GROUP_GID = grp.getgrnam("spj").gr_gid

TEST_CASE_DIR = "/test_case"
SPJ_SRC_DIR = "/judger/spj"
SPJ_EXE_DIR = "/judger/spj"

MAX_EXPECTED_OUTPUT_SIZE = 64 * 1024 * 1024
MAX_RUNTIME_OUTPUT_SIZE = 128 * 1024 * 1024
MAX_RUNTIME_PROCESS_NUMBER = 192
MAX_SPJ_OUTPUT_SIZE = 16 * 1024 * 1024
MAX_SPJ_PROCESS_NUMBER = 32
