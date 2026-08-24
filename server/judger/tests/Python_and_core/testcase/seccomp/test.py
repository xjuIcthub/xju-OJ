# coding=utf-8
from __future__ import print_function
import _judger
import signal
import shutil
import os

from .. import base


class SeccompTest(base.BaseTestCase):
    def setUp(self):
        print("Running", self._testMethodName)
        self.workspace = self.init_workspace("integration")
        os.chmod(self.workspace, 0o777)
        os.chown(self.workspace, 65534, 65534)

    @property
    def base_config(self):
        config = super(SeccompTest, self).base_config
        config["uid"] = 65534
        config["gid"] = 65534
        return config

    def _compile_c(self, src_name, extra_flags=None):
        return super(SeccompTest, self)._compile_c("../../test_src/seccomp/" + src_name, extra_flags)

    def test_fork(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("fork.c")
        config["output_path"] = config["error_path"] = self.output_path()
        result = _judger.run(**config)

        # without seccomp
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)

        # with general seccomp
        config["seccomp_rule_name"] = "general"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

        # with c_cpp seccomp
        config["seccomp_rule_name"] = "c_cpp"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

    def test_execve(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("execve.c")
        config["output_path"] = config["error_path"] = self.output_path()
        result = _judger.run(**config)
        # without seccomp
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        self.assertEqual("Helloworld\n", self.output_content(config["output_path"]))

        # with general seccomp
        config["seccomp_rule_name"] = "general"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

        # with c_cpp seccomp
        config["seccomp_rule_name"] = "c_cpp"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

    def test_write_file_using_open(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("write_file_open.c")
        config["output_path"] = config["error_path"] = self.output_path()
        path = os.path.join(self.workspace, "file1.txt")
        config["args"] = [path, "w"]
        result = _judger.run(**config)
        # without seccomp
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        self.assertEqual(0, os.path.getsize(path))

        # with general seccomp
        config["seccomp_rule_name"] = "general"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

        # with c_cpp seccomp
        config["seccomp_rule_name"] = "c_cpp"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

    def test_read_write_file_using_open(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("write_file_open.c")
        config["output_path"] = config["error_path"] = self.output_path()
        path = os.path.join(self.workspace, "file2.txt")
        config["args"] = [path, "w+"]
        result = _judger.run(**config)
        # without seccomp
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        self.assertEqual(0, os.path.getsize(path))

        # with general seccomp
        config["seccomp_rule_name"] = "general"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

        # with c_cpp seccomp
        config["seccomp_rule_name"] = "c_cpp"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

    def test_write_file_using_openat(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("write_file_openat.c")
        config["output_path"] = config["error_path"] = self.output_path()
        path = os.path.join(self.workspace, "file3.txt")
        config["args"] = [path, "w"]
        result = _judger.run(**config)
        # without seccomp
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        self.assertEqual(0, os.path.getsize(path))

        # with general seccomp
        config["seccomp_rule_name"] = "general"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

        # with c_cpp seccomp
        config["seccomp_rule_name"] = "c_cpp"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

    def test_read_write_file_using_openat(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("write_file_openat.c")
        config["output_path"] = config["error_path"] = self.output_path()
        path = os.path.join(self.workspace, "file4.txt")
        config["args"] = [path, "w+"]
        result = _judger.run(**config)
        # without seccomp
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        self.assertEqual(0, os.path.getsize(path))

        # with general seccomp
        config["seccomp_rule_name"] = "general"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

        # with c_cpp seccomp
        config["seccomp_rule_name"] = "c_cpp"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)

    def test_read_only_create_is_blocked(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("create_read_only.c")
        config["output_path"] = config["error_path"] = self.output_path()
        path = os.path.join(self.workspace, "read_only_create.txt")
        config["args"] = [path]

        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        self.assertTrue(os.path.exists(path))
        os.unlink(path)

        for rule in ("general", "c_cpp"):
            config["seccomp_rule_name"] = rule
            result = _judger.run(**config)
            self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
            self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)
            self.assertFalse(os.path.exists(path))

    def test_file_io_write_scope(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("file_io_scope.c")
        config["output_path"] = config["error_path"] = self.output_path()
        config["cwd"] = self.workspace
        local_path = os.path.join(self.workspace, "local.txt")
        escape_path = "/tmp/judger-file-io-escape.txt"
        try:
            os.unlink(escape_path)
        except OSError:
            pass
        config["args"] = [local_path, escape_path]
        config["seccomp_rule_name"] = "c_cpp_file_io"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        self.assertTrue(os.path.exists(local_path))
        self.assertFalse(os.path.exists(escape_path))

    def test_sysinfo(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("sysinfo.c")
        result = _judger.run(**config)

        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)

    def test_exceveat(self):
        config = self.base_config
        config["exe_path"] = self._compile_c("execveat.c")
        config["output_path"] = config["error_path"] = self.output_path()
        result = _judger.run(**config)
        if "syscall not found" in self.output_content(config["output_path"]):
            print("execveat syscall not found, test ignored")
            return
        self.assertEqual(result["result"], _judger.RESULT_SUCCESS)
        
        # with general seccomp 
        config["seccomp_rule_name"] = "general"
        result = _judger.run(**config)
        self.assertEqual(result["result"], _judger.RESULT_RUNTIME_ERROR)
        self.assertEqual(result["signal"], self.BAD_SYSTEM_CALL)
