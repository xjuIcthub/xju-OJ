import hashlib
import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.Python.client import JudgeServerClient  # noqa: E402


class JudgeProtocolContractTests(unittest.TestCase):
    def setUp(self):
        self.token = os.urandom(16).hex()
        self.base_url = "http://judge-fixture:8080"
        self.client = JudgeServerClient(token=self.token, server_base_url=self.base_url)

    @staticmethod
    def response(payload):
        response = Mock()
        response.json.return_value = payload
        return response

    def test_ping_hashes_token_and_preserves_envelope(self):
        payload = {"err": None, "data": {"action": "pong"}}
        with patch("client.Python.client.requests.post", return_value=self.response(payload)) as post:
            self.assertEqual(self.client.ping(), payload)

        args, kwargs = post.call_args
        self.assertEqual(args[0], self.base_url + "/ping")
        self.assertEqual(
            kwargs["headers"]["X-Judge-Server-Token"],
            hashlib.sha256(self.token.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")

    def test_compile_spj_uses_stable_endpoint_and_json_body(self):
        payload = {"err": None, "data": "success"}
        with patch("client.Python.client.requests.post", return_value=self.response(payload)) as post:
            result = self.client.compile_spj(
                src="int main(void) { return 0; }",
                spj_version="fixture",
                spj_compile_config={"src_name": "spj.c", "exe_name": "spj"},
            )

        self.assertEqual(result, payload)
        args, kwargs = post.call_args
        self.assertEqual(args[0], self.base_url + "/compile_spj")
        self.assertEqual(
            json.loads(kwargs["data"]),
            {
                "src": "int main(void) { return 0; }",
                "spj_version": "fixture",
                "spj_compile_config": {"src_name": "spj.c", "exe_name": "spj"},
            },
        )

    def test_judge_requires_exactly_one_test_case_source(self):
        language_config = {"run": {"exe_name": "main"}}
        with self.assertRaises(ValueError):
            self.client.judge(
                src="pass",
                language_config=language_config,
                max_cpu_time=100,
                max_memory=1024,
            )
        with self.assertRaises(ValueError):
            self.client.judge(
                src="pass",
                language_config=language_config,
                max_cpu_time=100,
                max_memory=1024,
                test_case_id="fixture",
                test_case=[{"input": "", "output": ""}],
            )

    def test_invalid_token_error_is_not_rewritten(self):
        payload = {"err": "TokenVerificationFailed", "data": "invalid token"}
        with patch("client.Python.client.requests.post", return_value=self.response(payload)):
            self.assertEqual(self.client.ping(), payload)


if __name__ == "__main__":
    unittest.main()
