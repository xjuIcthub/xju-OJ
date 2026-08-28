from copy import deepcopy
from unittest import mock

from problem.models import (Problem, ProblemJudgeMode, ProblemTag, RemoteOJ)
from utils.api.tests import APITestCase
from .models import (JudgeStatus, RemoteSubmissionStatus, Submission,
                     SubmissionJudgeMode)
from .remote import map_remote_verdict

DEFAULT_PROBLEM_DATA = {"_id": "A-110", "title": "test", "description": "<p>test</p>", "input_description": "test",
                        "output_description": "test", "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
                        "visible": True, "tags": ["test"], "languages": ["C", "C++", "Java", "Python3"], "template": {},
                        "samples": [{"input": "test", "output": "test"}], "spj": False, "spj_language": "C",
                        "spj_code": "", "test_case_id": "499b26290cc7994e0b497212e842ea85",
                        "test_case_score": [{"output_name": "1.out", "input_name": "1.in", "output_size": 0,
                                             "stripped_output_md5": "d41d8cd98f00b204e9800998ecf8427e",
                                             "input_size": 0, "score": 0}],
                        "rule_type": "ACM", "hint": "<p>test</p>", "source": "test"}

DEFAULT_SUBMISSION_DATA = {
    "problem_id": "1",
    "user_id": 1,
    "username": "test",
    "code": "xxxxxxxxxxxxxx",
    "result": -2,
    "info": {},
    "language": "C",
    "statistic_info": {}
}


# todo contest submission


class SubmissionPrepare(APITestCase):
    def _create_problem_and_submission(self):
        user = self.create_admin("test", "test123", login=False)
        problem_data = deepcopy(DEFAULT_PROBLEM_DATA)
        tags = problem_data.pop("tags")
        problem_data["created_by"] = user
        self.problem = Problem.objects.create(**problem_data)
        for tag in tags:
            tag = ProblemTag.objects.create(name=tag)
            self.problem.tags.add(tag)
        self.problem.save()
        self.submission_data = deepcopy(DEFAULT_SUBMISSION_DATA)
        self.submission_data["problem_id"] = self.problem.id
        self.submission = Submission.objects.create(**self.submission_data)


class SubmissionListTest(SubmissionPrepare):
    def setUp(self):
        self._create_problem_and_submission()
        self.create_user("123", "345")
        self.url = self.reverse("submission_list_api")

    def test_get_submission_list(self):
        resp = self.client.get(self.url, data={"limit": "10"})
        self.assertSuccess(resp)


@mock.patch("submission.views.oj.judge_task.send")
class SubmissionAPITest(SubmissionPrepare):
    def setUp(self):
        self._create_problem_and_submission()
        self.user = self.create_user("123", "test123")
        self.url = self.reverse("submission_api")

    def test_create_submission(self, judge_task):
        resp = self.client.post(self.url, self.submission_data)
        self.assertSuccess(resp)
        judge_task.assert_called()

    def test_create_submission_with_wrong_language(self, judge_task):
        self.submission_data.update({"language": "Python2"})
        resp = self.client.post(self.url, self.submission_data)
        self.assertFailed(resp)
        self.assertDictEqual(resp.data, {"error": "invalid-language",
                                         "data": "language: Python2 is not a valid language"})
        judge_task.assert_not_called()

    def _configure_remote_problem(self):
        self.problem.judge_mode = ProblemJudgeMode.REMOTE
        self.problem.remote_oj = RemoteOJ.CODEFORCES
        self.problem.remote_problem_id = "4A"
        self.problem.remote_problem_data = {
            "contest_id": 4,
            "index": "A",
            "url": "https://codeforces.com/problemset/problem/4/A",
            "language_ids": {"C": "43", "C++": "54"},
        }
        self.problem.test_case_id = ""
        self.problem.save()

    def test_create_remote_submission_returns_browser_task(self, judge_task):
        self._configure_remote_problem()
        resp = self.client.post(self.url, self.submission_data)
        self.assertSuccess(resp)
        judge_task.assert_not_called()

        response_data = resp.data["data"]
        task = response_data["remote_task"]
        submission = Submission.objects.get(id=response_data["submission_id"])
        self.assertEqual(task["provider"], RemoteOJ.CODEFORCES)
        self.assertEqual(task["problem_id"], "4A")
        self.assertEqual(task["language_id"], "43")
        self.assertEqual(submission.judge_mode, SubmissionJudgeMode.REMOTE)
        self.assertEqual(submission.remote_status, RemoteSubmissionStatus.QUEUED)

    def test_remote_submission_event_lifecycle(self, judge_task):
        self._configure_remote_problem()
        create = self.client.post(self.url, self.submission_data)
        self.assertSuccess(create)
        submission_id = create.data["data"]["submission_id"]
        event_url = self.reverse("remote_submission_event_api")

        for status, extra in (
                (RemoteSubmissionStatus.OPENING, {}),
                (RemoteSubmissionStatus.SUBMITTED, {"remote_submission_id": "10001"}),
                (RemoteSubmissionStatus.JUDGING, {"remote_submission_id": "10001"})):
            response = self.client.post(event_url, {
                "submission_id": submission_id,
                "provider": RemoteOJ.CODEFORCES,
                "status": status,
                **extra,
            })
            self.assertSuccess(response)

        finished = self.client.post(event_url, {
            "submission_id": submission_id,
            "provider": RemoteOJ.CODEFORCES,
            "status": RemoteSubmissionStatus.FINISHED,
            "remote_submission_id": "10001",
            "remote_url": "https://codeforces.com/contest/4/submission/10001",
            "verdict": "OK",
            "time_ms": 31,
            "memory_bytes": 4096,
            "verification_source": "codeforces-api",
        })
        self.assertSuccess(finished)

        submission = Submission.objects.get(id=submission_id)
        self.problem.refresh_from_db()
        self.user.userprofile.refresh_from_db()
        self.assertEqual(submission.result, JudgeStatus.ACCEPTED)
        self.assertEqual(submission.remote_status, RemoteSubmissionStatus.FINISHED)
        self.assertEqual(submission.remote_submission_id, "10001")
        self.assertEqual(submission.statistic_info["time_cost"], 31)
        self.assertEqual(self.problem.submission_number, 1)
        self.assertEqual(self.problem.accepted_number, 1)
        self.assertEqual(self.user.userprofile.submission_number, 1)


class RemoteVerdictMappingTest(APITestCase):
    def test_common_remote_verdicts(self):
        self.assertEqual(map_remote_verdict("OK"), JudgeStatus.ACCEPTED)
        self.assertEqual(map_remote_verdict("COMPILATION_ERROR"), JudgeStatus.COMPILE_ERROR)
        self.assertEqual(map_remote_verdict("答案错误"), JudgeStatus.WRONG_ANSWER)
