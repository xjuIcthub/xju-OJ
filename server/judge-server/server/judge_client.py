import fcntl
import hashlib
import json
import os
import shlex
import shutil
import stat
from concurrent.futures import ThreadPoolExecutor

import _judger
import psutil

from config import (FILE_IO_LOCK_PATH, JUDGER_RUN_LOG_PATH,
                    MAX_EXPECTED_OUTPUT_SIZE, MAX_RUNTIME_OUTPUT_SIZE,
                    MAX_RUNTIME_PROCESS_NUMBER, MAX_SPJ_OUTPUT_SIZE,
                    MAX_SPJ_PROCESS_NUMBER, RUN_GROUP_GID, RUN_USER_UID,
                    SPJ_EXE_DIR, SPJ_GROUP_GID, SPJ_USER_UID)
from exception import JudgeClientError
from utils import ProblemIOMode, open_root_lock

SPJ_WA = 1
SPJ_AC = 0
SPJ_ERROR = -1


def _run(instance, test_case_file_id):
    try:
        return instance._judge_one(test_case_file_id)
    finally:
        instance._seal_case(test_case_file_id)


def _require_filename(value, field):
    if not isinstance(value, str) or not value or value in (".", "..") or os.path.basename(value) != value:
        raise JudgeClientError("invalid %s" % field)
    return value


def _write_all(fd, content):
    view = memoryview(content)
    while view:
        written = os.write(fd, view)
        if written < 1:
            raise OSError("short write")
        view = view[written:]


def _create_regular_file(path, group_gid, mode, content=b""):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    fd = os.open(path, flags, mode)
    try:
        os.fchown(fd, 0, group_gid)
        os.fchmod(fd, mode)
        if content:
            _write_all(fd, content)
    finally:
        os.close(fd)


def _open_regular_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    file_stat = os.fstat(fd)
    if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
        os.close(fd)
        raise JudgeClientError("invalid runtime output")
    return fd


def _read_regular_file(path, max_size=None):
    fd = _open_regular_file(path)
    with os.fdopen(fd, "rb") as f:
        if max_size is None:
            return f.read()
        if os.fstat(fd).st_size > max_size:
            raise JudgeClientError("runtime output exceeded limit")
        content = f.read(max_size + 1)
        if len(content) > max_size:
            raise JudgeClientError("runtime output exceeded limit")
        return content


def _verify_regular_file(path):
    fd = _open_regular_file(path)
    os.close(fd)


def _chmod_regular_file(path, mode):
    fd = _open_regular_file(path)
    try:
        os.fchmod(fd, mode)
    finally:
        os.close(fd)


def _copy_regular_file(source, destination, group_gid, mode):
    source_fd = _open_regular_file(source)
    destination_fd = os.open(destination,
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                             mode)
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise JudgeClientError("invalid source file")
        os.fchown(destination_fd, 0, group_gid)
        os.fchmod(destination_fd, mode)
        with os.fdopen(source_fd, "rb", closefd=False) as source_file, \
                os.fdopen(destination_fd, "wb", closefd=False) as destination_file:
            shutil.copyfileobj(source_file, destination_file)
    finally:
        os.close(source_fd)
        os.close(destination_fd)


class JudgeClient(object):
    def __init__(self, run_config, exe_path, max_cpu_time, max_memory, test_case_dir,
                 submission_dir, spj_version, spj_config, io_mode, output=False):
        self._run_config = run_config
        self._exe_path = exe_path
        self._max_cpu_time = max_cpu_time
        self._max_memory = max_memory
        self._max_real_time = self._max_cpu_time * 3
        self._test_case_dir = test_case_dir
        self._submission_dir = submission_dir

        self._test_case_info = self._load_test_case_info()

        self._spj_version = spj_version
        self._spj_config = spj_config
        self._output = output
        self._io_mode = io_mode

        if self._spj_version and self._spj_config:
            self._spj_exe = os.path.join(
                SPJ_EXE_DIR,
                self._spj_config["exe_name"].format(spj_version=self._spj_version),
            )
            try:
                _verify_regular_file(self._spj_exe)
            except (FileNotFoundError, OSError, JudgeClientError):
                raise JudgeClientError("spj exe not found")

    def _load_test_case_info(self):
        try:
            directory_stat = os.lstat(self._test_case_dir)
            if not stat.S_ISDIR(directory_stat.st_mode):
                raise JudgeClientError("Test case not found")
            content = _read_regular_file(os.path.join(self._test_case_dir, "info"),
                                         4 * 1024 * 1024)
            info = json.loads(content.decode("utf-8"))
            if not isinstance(info, dict) or not isinstance(info.get("test_cases"), dict):
                raise ValueError("invalid test case info")
            return info
        except (FileNotFoundError, OSError):
            raise JudgeClientError("Test case not found")
        except (UnicodeDecodeError, ValueError):
            raise JudgeClientError("Bad test case config")

    def _get_test_case_file_info(self, test_case_file_id):
        return self._test_case_info["test_cases"][test_case_file_id]

    def _compare_output(self, test_case_file_id, content):
        output_md5 = hashlib.md5(content.rstrip()).hexdigest()
        result = output_md5 == self._get_test_case_file_info(test_case_file_id)["stripped_output_md5"]
        return output_md5, result

    def _spj(self, case_dir, in_file_path, user_out_file_path):
        # Each testcase gets a root-created SPJ directory. The SPJ runtime can
        # read only copies of its input and candidate output, cannot traverse
        # other testcase data, and never shares stdout/stderr with another SPJ.
        spj_dir = os.path.join(case_dir, ".spj")
        spj_input_path = os.path.join(spj_dir, "input")
        spj_user_output_path = os.path.join(spj_dir, "output")
        spj_log_path = os.path.join(spj_dir, "stdio")
        _copy_regular_file(in_file_path, spj_input_path, SPJ_GROUP_GID, 0o440)
        _copy_regular_file(user_out_file_path, spj_user_output_path, SPJ_GROUP_GID, 0o440)
        _create_regular_file(spj_log_path, SPJ_GROUP_GID, 0o640)

        command = self._spj_config["command"].format(
            exe_path=self._spj_exe,
            in_file_path=spj_input_path,
            user_out_file_path=spj_user_output_path,
        )
        command = shlex.split(command)
        result = _judger.run(max_cpu_time=self._max_cpu_time * 3,
                             max_real_time=self._max_cpu_time * 9,
                             max_memory=self._max_memory * 3,
                             max_stack=128 * 1024 * 1024,
                             max_output_size=MAX_SPJ_OUTPUT_SIZE,
                             max_process_number=MAX_SPJ_PROCESS_NUMBER,
                             exe_path=command[0],
                             input_path=spj_input_path,
                             output_path=spj_log_path,
                             error_path=spj_log_path,
                             args=command[1::],
                             env=["PATH=" + os.environ.get("PATH", "")],
                             log_path=JUDGER_RUN_LOG_PATH,
                             seccomp_rule_name=self._spj_config["seccomp_rule"],
                             uid=SPJ_USER_UID,
                             gid=SPJ_GROUP_GID,
                             cwd=spj_dir)

        if result["result"] == _judger.RESULT_SUCCESS or \
                (result["result"] == _judger.RESULT_RUNTIME_ERROR and
                 result["exit_code"] in [SPJ_WA, SPJ_ERROR] and result["signal"] == 0):
            return result["exit_code"]
        return SPJ_ERROR

    def _prepare_case(self, test_case_file_id, in_file):
        case_name = _require_filename(str(test_case_file_id), "test case id")
        case_dir = os.path.join(self._submission_dir, case_name)
        os.mkdir(case_dir)
        os.chown(case_dir, 0, RUN_GROUP_GID)

        stdio_path = os.path.join(case_dir, ".judger-stdio")
        runtime_input_path = os.path.join(case_dir, ".judger-input")
        _create_regular_file(stdio_path, RUN_GROUP_GID, 0o640)
        _copy_regular_file(in_file, runtime_input_path, RUN_GROUP_GID, 0o440)
        if self._test_case_info.get("spj"):
            spj_dir = os.path.join(case_dir, ".spj")
            os.mkdir(spj_dir)
            os.chown(spj_dir, 0, SPJ_GROUP_GID)
            os.chmod(spj_dir, 0o750)

        if self._io_mode["io_mode"] == ProblemIOMode.file:
            input_name = _require_filename(self._io_mode.get("input"), "input filename")
            output_name = _require_filename(self._io_mode.get("output"), "output filename")
            reserved_names = {".judger-input", ".judger-stdio", ".spj"}
            if input_name == output_name or input_name in reserved_names or output_name in reserved_names:
                raise JudgeClientError("invalid file IO configuration")

            user_input_file = os.path.join(case_dir, input_name)
            user_output_file = os.path.join(case_dir, output_name)
            output_sentinel = os.urandom(32)
            _copy_regular_file(runtime_input_path, user_input_file, RUN_GROUP_GID, 0o440)
            _create_regular_file(user_output_file, RUN_GROUP_GID, 0o660,
                                 output_sentinel)

            # The configured output is pre-created and group-writable; the
            # directory itself stays read-only to the runtime so it cannot
            # create scratch files or replace judge-controlled entries.
            os.chmod(case_dir, 0o750)
        else:
            user_output_file = stdio_path
            output_sentinel = None
            os.chmod(case_dir, 0o750)

        return case_dir, runtime_input_path, stdio_path, user_output_file, output_sentinel

    def _seal_case(self, test_case_file_id):
        case_name = _require_filename(str(test_case_file_id), "test case id")
        case_dir = os.path.join(self._submission_dir, case_name)
        try:
            case_fd = os.open(case_dir,
                              os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        except FileNotFoundError:
            return
        try:
            os.fchown(case_fd, 0, 0)
            os.fchmod(case_fd, 0o700)
        finally:
            os.close(case_fd)

    def _judge_one(self, test_case_file_id):
        test_case_info = self._get_test_case_file_info(test_case_file_id)
        input_name = _require_filename(test_case_info["input_name"], "test case input name")
        in_file = os.path.join(self._test_case_dir, input_name)
        case_dir, runtime_input_path, stdio_path, user_output_file, output_sentinel = \
            self._prepare_case(test_case_file_id, in_file)

        command = self._run_config["command"].format(
            exe_path=self._exe_path,
            exe_dir=os.path.dirname(self._exe_path),
            max_memory=int(self._max_memory / 1024),
        )
        command = shlex.split(command)
        command_name = os.path.basename(command[0])
        is_java = command_name == "java"
        is_node = command_name == "node"
        if is_java and "-XX:+PerfDisableSharedMem" not in command:
            command.insert(1, "-XX:+PerfDisableSharedMem")
        if is_node and "--permission" not in command:
            node_permissions = ["--permission", "--allow-fs-read=*", "--allow-worker",
                                "--disable-warning=SecurityWarning"]
            if self._io_mode["io_mode"] == ProblemIOMode.file:
                node_permissions.append("--allow-fs-write=.")
            command[1:1] = node_permissions
        env = ["PATH=" + os.environ.get("PATH", "")] + self._run_config.get("env", [])

        seccomp_rule = self._run_config["seccomp_rule"]
        if is_java and seccomp_rule is None:
            seccomp_rule = "java"
        if isinstance(seccomp_rule, dict):
            seccomp_rule = seccomp_rule[self._io_mode["io_mode"]]
        elif self._io_mode["io_mode"] == ProblemIOMode.file and seccomp_rule in {
                "general", "golang", "node", "java"}:
            seccomp_rule += "_file_io"

        expected_output_size = test_case_info.get("output_size", 0)
        if (not isinstance(expected_output_size, int) or isinstance(expected_output_size, bool) or
                expected_output_size < 0 or expected_output_size > MAX_EXPECTED_OUTPUT_SIZE):
            raise JudgeClientError("invalid expected output size")
        output_limit = min(MAX_RUNTIME_OUTPUT_SIZE,
                           max(expected_output_size * 2, 16 * 1024 * 1024))
        try:
            run_result = _judger.run(
                max_cpu_time=self._max_cpu_time,
                max_real_time=self._max_real_time,
                max_memory=self._max_memory,
                max_stack=128 * 1024 * 1024,
                max_output_size=output_limit,
                max_process_number=MAX_RUNTIME_PROCESS_NUMBER,
                exe_path=command[0],
                input_path=runtime_input_path,
                output_path=stdio_path,
                error_path=stdio_path,
                args=command[1::],
                env=env,
                log_path=JUDGER_RUN_LOG_PATH,
                seccomp_rule_name=seccomp_rule,
                uid=RUN_USER_UID,
                gid=RUN_GROUP_GID,
                memory_limit_check_only=self._run_config.get("memory_limit_check_only", 0),
                cwd=case_dir,
            )
        finally:
            # The runner kills the complete process group before returning.
            # Revoke runtime writes before inspecting any output pathname.
            os.chmod(case_dir, 0o751 if self._test_case_info.get("spj") else 0o750)
            try:
                _chmod_regular_file(user_output_file, 0o440)
            except FileNotFoundError:
                pass

        run_result["test_case"] = test_case_file_id
        run_result["output_md5"] = None
        run_result["output"] = None

        output_content = None
        output_missing = False
        if run_result["result"] == _judger.RESULT_SUCCESS:
            try:
                output_content = _read_regular_file(user_output_file, output_limit)
            except (FileNotFoundError, OSError, JudgeClientError):
                run_result["result"] = _judger.RESULT_WRONG_ANSWER
            else:
                if output_sentinel is not None and output_content == output_sentinel:
                    output_content = None
                    output_missing = True
                    run_result["result"] = _judger.RESULT_WRONG_ANSWER
                elif self._test_case_info.get("spj"):
                    if not self._spj_config or not self._spj_version:
                        raise JudgeClientError("spj_config or spj_version not set")
                    spj_result = self._spj(case_dir, runtime_input_path, user_output_file)
                    if spj_result == SPJ_WA:
                        run_result["result"] = _judger.RESULT_WRONG_ANSWER
                    elif spj_result == SPJ_ERROR:
                        run_result["result"] = _judger.RESULT_SYSTEM_ERROR
                        run_result["error"] = _judger.ERROR_SPJ_ERROR
                else:
                    run_result["output_md5"], is_ac = self._compare_output(test_case_file_id, output_content)
                    if not is_ac:
                        run_result["result"] = _judger.RESULT_WRONG_ANSWER

        if self._output:
            if output_content is None and not output_missing:
                try:
                    output_content = _read_regular_file(user_output_file, output_limit)
                    if output_sentinel is not None and output_content == output_sentinel:
                        output_content = None
                        output_missing = True
                except Exception:
                    output_content = None
            if output_content is not None:
                run_result["output"] = output_content.decode("utf-8", errors="backslashreplace")

        return run_result

    def run(self):
        test_case_ids = list(self._test_case_info["test_cases"])
        if not test_case_ids:
            return []

        try:
            configured_workers = max(1, int(os.environ.get("JUDGER_TESTCASE_WORKERS", "4")))
        except ValueError:
            configured_workers = 4
        worker_count = min(len(test_case_ids), psutil.cpu_count() or 1, configured_workers)

        # File IO needs a writable cwd. All submissions share the fixed runtime
        # UID, so serialize this lane across Gunicorn workers and run testcase
        # directories one at a time. Each worker seals its case before the next
        # starts; Standard IO remains bounded-parallel.
        file_io_lock = None
        if self._io_mode["io_mode"] == ProblemIOMode.file:
            worker_count = 1
            file_io_lock = open_root_lock(FILE_IO_LOCK_PATH)
            fcntl.flock(file_io_lock.fileno(), fcntl.LOCK_EX)

        try:
            with ThreadPoolExecutor(max_workers=worker_count,
                                    thread_name_prefix="judger-case") as executor:
                futures = [executor.submit(_run, self, test_case_file_id)
                           for test_case_file_id in test_case_ids]
                return [future.result() for future in futures]
        finally:
            if file_io_lock is not None:
                file_io_lock.close()
