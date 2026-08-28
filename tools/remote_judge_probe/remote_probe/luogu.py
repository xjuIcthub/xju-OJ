from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from .common import (
    AmbiguousSubmission,
    AuthenticationRequired,
    ProbeError,
    RemoteResult,
    RemoteSubmission,
    response_json,
)


BASE_URL = "https://open-v1.lgapi.cn"
TOKEN_ENVIRONMENT_VARIABLE = "LUOGU_OPENAPP_TOKEN"
STATUS_MAP = {
    0: "WAITING",
    1: "JUDGING",
    2: "COMPILATION_ERROR",
    3: "OUTPUT_LIMIT_EXCEEDED",
    4: "MEMORY_LIMIT_EXCEEDED",
    5: "TIME_LIMIT_EXCEEDED",
    6: "WRONG_ANSWER",
    7: "RUNTIME_ERROR",
    11: "SYSTEM_ERROR",
    12: "ACCEPTED",
    14: "UNACCEPTED",
}


class QuotaExceeded(ProbeError):
    exit_code = 6


def parse_problem_id(raw: str) -> str:
    value = raw.strip()
    if "://" in value:
        match = re.search(r"/problem/([A-Za-z0-9_-]+)", urlparse(value).path)
        value = match.group(1) if match else ""
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise ProbeError("洛谷题号格式应类似 P1001 或题目 URL")
    return value.upper()


def parse_openapp_token(raw: str) -> tuple[str, str]:
    token = raw.strip()
    client_id, separator, secret = token.partition(":")
    if not separator or not client_id.strip() or not secret.strip():
        raise AuthenticationRequired("洛谷 OpenApp Token 格式应为 client_id:secret")
    if any(character.isspace() for character in client_id + secret):
        raise AuthenticationRequired("洛谷 OpenApp Token 不能包含空白字符")
    return client_id, secret


def load_openapp_token(token_file: Optional[str] = None) -> str:
    if token_file:
        path = Path(token_file).expanduser()
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            raise AuthenticationRequired(f"无法读取洛谷 OpenApp Token 文件: {exc}") from exc
        if not raw:
            raise AuthenticationRequired("洛谷 OpenApp Token 文件为空")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            token = raw
        else:
            if not isinstance(data, dict):
                raise AuthenticationRequired("洛谷 OpenApp Token JSON 必须是对象")
            token = data.get("token")
            if not token:
                client_id = data.get("client_id")
                secret = data.get("secret")
                token = f"{client_id}:{secret}" if client_id and secret else ""
            if not isinstance(token, str) or not token:
                raise AuthenticationRequired(
                    "洛谷 OpenApp Token JSON 需要 token，或 client_id 与 secret"
                )
    else:
        token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, "").strip()
        if not token:
            raise AuthenticationRequired(
                f"请使用 --token-file，或设置 {TOKEN_ENVIRONMENT_VARIABLE}"
            )
    client_id, secret = parse_openapp_token(token)
    return f"{client_id}:{secret}"


def _error_message(response: requests.Response, fallback: str) -> str:
    try:
        data = response.json()
    except ValueError:
        return f"{fallback}（HTTP {response.status_code}）"
    if not isinstance(data, dict):
        return f"{fallback}（HTTP {response.status_code}）"

    message = data.get("errorMessage") or data.get("message") or data.get("msg")
    error_data = data.get("errorData")
    field_messages = []
    if isinstance(error_data, dict):
        fields = error_data.get("fields")
        if isinstance(fields, list):
            for field in fields:
                if not isinstance(field, dict):
                    continue
                name = field.get("name")
                field_message = field.get("message")
                if field_message:
                    field_messages.append(
                        f"{name}: {field_message}" if name else str(field_message)
                    )
    details = "; ".join(field_messages)
    if message and details:
        return f"{message}: {details}"
    return str(message or details or f"{fallback}（HTTP {response.status_code}）")


def _number(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _case_counts(judge: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    cases = []
    subtasks = judge.get("subtasks")
    if isinstance(subtasks, list):
        for subtask in subtasks:
            if not isinstance(subtask, dict) or not isinstance(subtask.get("cases"), list):
                continue
            cases.extend(case for case in subtask["cases"] if isinstance(case, dict))
    if not cases:
        return None, None
    passed = sum(1 for case in cases if _number(case.get("status")) == 12)
    return passed, len(cases)


class LuoguOpenPlatformProvider:
    """Luogu's official Open Platform remote-judge client."""

    def __init__(
        self,
        openapp_token: str,
        session: Optional[requests.Session] = None,
    ):
        client_id, secret = parse_openapp_token(openapp_token)
        self.session = session or requests.Session()
        self.session.auth = (client_id, secret)
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "xju-OJ/remote-judge-probe",
            }
        )

    @staticmethod
    def _raise_response_error(response: requests.Response, context: str) -> None:
        message = _error_message(response, context)
        if response.status_code in {401, 403}:
            raise AuthenticationRequired(f"洛谷 OpenApp 鉴权失败: {message}")
        if response.status_code == 402:
            raise QuotaExceeded(f"洛谷开放平台评测额度不足: {message}")
        raise ProbeError(message)

    def submit(
        self,
        problem_id: str,
        language: str,
        code: str,
        o2: bool = False,
        track_id: Optional[str] = None,
    ) -> RemoteSubmission:
        problem_id = parse_problem_id(problem_id)
        language = language.strip()
        if not language:
            raise ProbeError("洛谷开放平台语言标识不能为空")
        if track_id is not None and len(track_id.encode("utf-8")) > 64:
            raise ProbeError("洛谷开放平台 trackId 不能超过 64 字节")

        body: dict[str, Any] = {
            "pid": problem_id,
            "lang": language,
            "o2": bool(o2),
            "code": code,
        }
        if track_id:
            body["trackId"] = track_id
        try:
            response = self.session.post(
                f"{BASE_URL}/judge/problem",
                json=body,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise AmbiguousSubmission(
                f"洛谷开放平台提交结果未知，请先按 trackId 或后台记录核查，不要直接重试: {exc}"
            ) from exc
        if response.status_code >= 500:
            raise AmbiguousSubmission(
                _error_message(response, "洛谷开放平台提交时发生服务端错误，结果可能未知")
            )
        if response.status_code != 200:
            self._raise_response_error(response, "洛谷开放平台拒绝了提交")

        data = response_json(response, "洛谷开放平台提交接口")
        request_id = data.get("requestId") or data.get("resultId") or data.get("id")
        if not request_id:
            raise AmbiguousSubmission(
                "洛谷开放平台提交响应缺少 requestId，请核查后台记录后再决定是否重试"
            )
        return RemoteSubmission(
            provider="luogu",
            remote_id=str(request_id),
            problem_id=problem_id,
            submitted_at=int(time.time()),
            query={"track_id": track_id} if track_id else {},
        )

    def query(self, submission: RemoteSubmission) -> RemoteResult:
        try:
            response = self.session.get(
                f"{BASE_URL}/judge/result",
                params={"id": submission.remote_id},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise ProbeError(f"洛谷开放平台结果查询失败: {exc}") from exc
        if response.status_code == 204:
            return RemoteResult(
                provider="luogu",
                remote_id=submission.remote_id,
                stage="judging",
                finished=False,
                message="WAITING",
            )
        if response.status_code != 200:
            self._raise_response_error(response, "洛谷开放平台结果查询失败")

        payload = response_json(response, "洛谷开放平台结果接口")
        data = payload.get("data")
        if data is None:
            return RemoteResult(
                provider="luogu",
                remote_id=submission.remote_id,
                stage="judging",
                finished=False,
                message="WAITING",
            )
        if not isinstance(data, dict):
            raise ProbeError("洛谷开放平台结果接口 data 格式异常")

        compile_result = data.get("compile")
        if isinstance(compile_result, dict) and compile_result.get("success") is False:
            return RemoteResult(
                provider="luogu",
                remote_id=submission.remote_id,
                stage="finished",
                finished=True,
                verdict="COMPILATION_ERROR",
                time_ms=0,
                memory_bytes=0,
                score=0,
                message=str(compile_result.get("message") or "COMPILATION_ERROR"),
            )

        judge = data.get("judge")
        if not isinstance(judge, dict):
            message = "COMPILED" if isinstance(compile_result, dict) else "WAITING"
            return RemoteResult(
                provider="luogu",
                remote_id=submission.remote_id,
                stage="judging",
                finished=False,
                message=message,
            )

        status = _number(judge.get("status"))
        if status is None:
            raise ProbeError("洛谷开放平台评测结果缺少有效 status")
        finished = status not in {0, 1}
        verdict = STATUS_MAP.get(status, f"STATUS_{status}")
        memory_kib = _number(judge.get("memory"))
        passed_tests, total_tests = _case_counts(judge)
        return RemoteResult(
            provider="luogu",
            remote_id=submission.remote_id,
            stage="finished" if finished else "judging",
            finished=finished,
            verdict=verdict if finished else None,
            time_ms=_number(judge.get("time")),
            memory_bytes=memory_kib * 1024 if memory_kib is not None else None,
            passed_tests=passed_tests,
            total_tests=total_tests,
            score=judge.get("score") if isinstance(judge.get("score"), (int, float)) else None,
            message=verdict,
        )

    def quota(self) -> dict[str, Any]:
        try:
            response = self.session.get(
                f"{BASE_URL}/judge/quotaAvailable",
                timeout=20,
            )
        except requests.RequestException as exc:
            raise ProbeError(f"洛谷开放平台额度查询失败: {exc}") from exc
        if response.status_code != 200:
            self._raise_response_error(response, "洛谷开放平台额度查询失败")
        data = response_json(response, "洛谷开放平台额度接口")
        quotas = data.get("quotas")
        if not isinstance(quotas, list):
            raise ProbeError("洛谷开放平台额度接口缺少 quotas 数组")
        return data


# Keep the old import name working while callers migrate to the explicit class name.
LuoguProvider = LuoguOpenPlatformProvider
