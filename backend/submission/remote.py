from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from judge.dispatcher import JudgeDispatcher
from problem.models import ProblemJudgeMode, RemoteOJ

from .models import (JudgeStatus, RemoteSubmissionStatus, Submission,
                     SubmissionJudgeMode)


REMOTE_TASK_SCHEMA = "xju-oj.remote-submit.v1"


class RemoteSubmissionError(RuntimeError):
    pass


_PROVIDER_HOSTS = {
    RemoteOJ.CODEFORCES: {"codeforces.com", "www.codeforces.com"},
    RemoteOJ.LUOGU: {"luogu.com.cn", "www.luogu.com.cn"},
    RemoteOJ.NOWCODER: {"ac.nowcoder.com", "www.nowcoder.com", "nowcoder.com"},
}


_ALLOWED_TRANSITIONS = {
    RemoteSubmissionStatus.QUEUED: {
        RemoteSubmissionStatus.OPENING,
        RemoteSubmissionStatus.AUTH_REQUIRED,
        RemoteSubmissionStatus.VERIFICATION_REQUIRED,
        RemoteSubmissionStatus.SUBMITTED,
        RemoteSubmissionStatus.JUDGING,
        RemoteSubmissionStatus.FINISHED,
        RemoteSubmissionStatus.FAILED,
    },
    RemoteSubmissionStatus.OPENING: {
        RemoteSubmissionStatus.AUTH_REQUIRED,
        RemoteSubmissionStatus.VERIFICATION_REQUIRED,
        RemoteSubmissionStatus.SUBMITTED,
        RemoteSubmissionStatus.JUDGING,
        RemoteSubmissionStatus.FINISHED,
        RemoteSubmissionStatus.FAILED,
    },
    RemoteSubmissionStatus.AUTH_REQUIRED: {
        RemoteSubmissionStatus.OPENING,
        RemoteSubmissionStatus.VERIFICATION_REQUIRED,
        RemoteSubmissionStatus.SUBMITTED,
        RemoteSubmissionStatus.JUDGING,
        RemoteSubmissionStatus.FINISHED,
        RemoteSubmissionStatus.FAILED,
    },
    RemoteSubmissionStatus.VERIFICATION_REQUIRED: {
        RemoteSubmissionStatus.OPENING,
        RemoteSubmissionStatus.SUBMITTED,
        RemoteSubmissionStatus.JUDGING,
        RemoteSubmissionStatus.FINISHED,
        RemoteSubmissionStatus.FAILED,
    },
    RemoteSubmissionStatus.SUBMITTED: {
        RemoteSubmissionStatus.JUDGING,
        RemoteSubmissionStatus.FINISHED,
        RemoteSubmissionStatus.FAILED,
    },
    RemoteSubmissionStatus.JUDGING: {
        RemoteSubmissionStatus.FINISHED,
        RemoteSubmissionStatus.FAILED,
    },
}


_VERDICT_ALIASES = {
    "OK": JudgeStatus.ACCEPTED,
    "AC": JudgeStatus.ACCEPTED,
    "ACCEPTED": JudgeStatus.ACCEPTED,
    "答案正确": JudgeStatus.ACCEPTED,
    "WRONG_ANSWER": JudgeStatus.WRONG_ANSWER,
    "WRONG ANSWER": JudgeStatus.WRONG_ANSWER,
    "WA": JudgeStatus.WRONG_ANSWER,
    "答案错误": JudgeStatus.WRONG_ANSWER,
    "TIME_LIMIT_EXCEEDED": JudgeStatus.CPU_TIME_LIMIT_EXCEEDED,
    "TIME LIMIT EXCEEDED": JudgeStatus.CPU_TIME_LIMIT_EXCEEDED,
    "TLE": JudgeStatus.CPU_TIME_LIMIT_EXCEEDED,
    "运行超时": JudgeStatus.CPU_TIME_LIMIT_EXCEEDED,
    "超时": JudgeStatus.CPU_TIME_LIMIT_EXCEEDED,
    "MEMORY_LIMIT_EXCEEDED": JudgeStatus.MEMORY_LIMIT_EXCEEDED,
    "MEMORY LIMIT EXCEEDED": JudgeStatus.MEMORY_LIMIT_EXCEEDED,
    "MLE": JudgeStatus.MEMORY_LIMIT_EXCEEDED,
    "内存超限": JudgeStatus.MEMORY_LIMIT_EXCEEDED,
    "RUNTIME_ERROR": JudgeStatus.RUNTIME_ERROR,
    "RUNTIME ERROR": JudgeStatus.RUNTIME_ERROR,
    "RE": JudgeStatus.RUNTIME_ERROR,
    "运行错误": JudgeStatus.RUNTIME_ERROR,
    "COMPILATION_ERROR": JudgeStatus.COMPILE_ERROR,
    "COMPILE_ERROR": JudgeStatus.COMPILE_ERROR,
    "COMPILE ERROR": JudgeStatus.COMPILE_ERROR,
    "CE": JudgeStatus.COMPILE_ERROR,
    "编译错误": JudgeStatus.COMPILE_ERROR,
    "OUTPUT_LIMIT_EXCEEDED": JudgeStatus.RUNTIME_ERROR,
    "OUTPUT LIMIT EXCEEDED": JudgeStatus.RUNTIME_ERROR,
    "OLE": JudgeStatus.RUNTIME_ERROR,
    "PARTIALLY_ACCEPTED": JudgeStatus.PARTIALLY_ACCEPTED,
    "PARTIAL": JudgeStatus.PARTIALLY_ACCEPTED,
    "UNACCEPTED": JudgeStatus.PARTIALLY_ACCEPTED,
    "OVERALL_UNACCEPTED": JudgeStatus.PARTIALLY_ACCEPTED,
    "部分正确": JudgeStatus.PARTIALLY_ACCEPTED,
    "SYSTEM_ERROR": JudgeStatus.SYSTEM_ERROR,
    "SYSTEM ERROR": JudgeStatus.SYSTEM_ERROR,
    "SE": JudgeStatus.SYSTEM_ERROR,
    "UNKNOWN_ERROR": JudgeStatus.SYSTEM_ERROR,
    "UNKNOWN ERROR": JudgeStatus.SYSTEM_ERROR,
}


def _safe_provider_url(provider, value):
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme != "https" or parsed.hostname not in _PROVIDER_HOSTS.get(provider, set()):
        raise RemoteSubmissionError("Remote problem URL is invalid")
    return parsed.geturl()


def build_remote_task(problem, submission):
    if problem.judge_mode != ProblemJudgeMode.REMOTE or not problem.remote_oj:
        raise RemoteSubmissionError("Problem is not configured for remote judging")
    metadata = problem.remote_problem_data or {}
    language_ids = metadata.get("language_ids") or {}
    language_id = language_ids.get(submission.language)
    if language_id is None:
        raise RemoteSubmissionError(
            f"{submission.language} has no {problem.remote_oj} language mapping"
        )
    target_url = _safe_provider_url(problem.remote_oj, metadata.get("url"))
    provider_data = {}
    if problem.remote_oj == RemoteOJ.CODEFORCES:
        provider_data = {
            "contest_id": metadata.get("contest_id"),
            "index": metadata.get("index"),
        }
    elif problem.remote_oj == RemoteOJ.LUOGU:
        provider_data = {"problem_id": metadata.get("problem_id") or problem.remote_problem_id}
    elif problem.remote_oj == RemoteOJ.NOWCODER:
        provider_data = {
            "question_id": metadata.get("question_id"),
            "problem_id": metadata.get("problem_id") or problem.remote_problem_id,
            "uuid": metadata.get("uuid"),
            "tag_id": metadata.get("tag_id"),
        }
    return {
        "schema": REMOTE_TASK_SCHEMA,
        "submission_id": submission.id,
        "provider": problem.remote_oj,
        "problem_id": problem.remote_problem_id,
        "language": submission.language,
        "language_id": str(language_id),
        "target_url": target_url,
        "provider_data": provider_data,
        "created_at": submission.create_time.isoformat(),
    }


def map_remote_verdict(verdict):
    normalized = str(verdict or "").strip().upper().replace("-", "_")
    if normalized in _VERDICT_ALIASES:
        return _VERDICT_ALIASES[normalized]
    normalized_spaces = normalized.replace("_", " ")
    if normalized_spaces in _VERDICT_ALIASES:
        return _VERDICT_ALIASES[normalized_spaces]
    raise RemoteSubmissionError(f"Unsupported remote verdict: {verdict}")


def _check_transition(current, target):
    if current == target:
        return
    if current in RemoteSubmissionStatus.TERMINAL:
        raise RemoteSubmissionError("Remote submission has already finished")
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise RemoteSubmissionError(f"Invalid remote submission transition: {current} -> {target}")


def _event_data(data):
    return {
        key: data[key]
        for key in (
            "verdict", "message", "time_ms", "memory_bytes", "passed_tests",
            "total_tests", "score", "verification_source",
        )
        if data.get(key) is not None
    }


@transaction.atomic
def apply_remote_submission_event(user, data):
    try:
        submission = (
            Submission.objects.select_for_update()
            .select_related("problem")
            .get(id=data["submission_id"], user_id=user.id)
        )
    except Submission.DoesNotExist as exc:
        raise RemoteSubmissionError("Remote submission does not exist") from exc

    if submission.judge_mode != SubmissionJudgeMode.REMOTE:
        raise RemoteSubmissionError("Submission is not a remote submission")
    if submission.remote_oj != data["provider"]:
        raise RemoteSubmissionError("Remote provider does not match the submission")

    target = data["status"]
    _check_transition(submission.remote_status, target)
    if submission.remote_status == target and target in RemoteSubmissionStatus.TERMINAL:
        return submission

    remote_submission_id = str(data.get("remote_submission_id") or "").strip()
    if remote_submission_id:
        if submission.remote_submission_id and submission.remote_submission_id != remote_submission_id:
            raise RemoteSubmissionError("Remote submission ID cannot be changed")
        submission.remote_submission_id = remote_submission_id
    if target in {
        RemoteSubmissionStatus.SUBMITTED,
        RemoteSubmissionStatus.JUDGING,
        RemoteSubmissionStatus.FINISHED,
    } and not submission.remote_submission_id:
        raise RemoteSubmissionError("Remote submission ID is required")

    remote_url = data.get("remote_url")
    if remote_url:
        submission.remote_url = _safe_provider_url(submission.remote_oj, remote_url)

    submission.remote_status = target
    submission.remote_message = str(data.get("message") or "")[:2048] or None
    submission.remote_update_time = timezone.now()
    submission.remote_data = {**(submission.remote_data or {}), **_event_data(data)}

    if target in {RemoteSubmissionStatus.SUBMITTED, RemoteSubmissionStatus.JUDGING}:
        submission.result = JudgeStatus.JUDGING
    elif target in {
        RemoteSubmissionStatus.QUEUED,
        RemoteSubmissionStatus.OPENING,
        RemoteSubmissionStatus.AUTH_REQUIRED,
        RemoteSubmissionStatus.VERIFICATION_REQUIRED,
    }:
        submission.result = JudgeStatus.PENDING

    final_result = None
    if target == RemoteSubmissionStatus.FINISHED:
        final_result = map_remote_verdict(data.get("verdict"))
    elif target == RemoteSubmissionStatus.FAILED:
        final_result = JudgeStatus.SYSTEM_ERROR

    dispatcher = None
    if final_result is not None:
        dispatcher = JudgeDispatcher(submission.id, submission.problem_id)
        dispatcher.last_result = None
        submission.result = final_result
        submission.info = {"remote": submission.remote_data}
        statistic_info = dict(submission.statistic_info or {})
        if data.get("time_ms") is not None:
            statistic_info["time_cost"] = data["time_ms"]
        if data.get("memory_bytes") is not None:
            statistic_info["memory_cost"] = data["memory_bytes"]
        if data.get("score") is not None:
            statistic_info["score"] = data["score"]
        if target == RemoteSubmissionStatus.FAILED:
            statistic_info["err_info"] = submission.remote_message or "Remote submission failed"
        submission.statistic_info = statistic_info

    submission.save()
    if dispatcher is not None:
        dispatcher.submission = submission
        dispatcher.problem = submission.problem
        dispatcher.finalize_submission()
    return submission


__all__ = [
    "REMOTE_TASK_SCHEMA",
    "RemoteSubmissionError",
    "apply_remote_submission_event",
    "build_remote_task",
    "map_remote_verdict",
]
