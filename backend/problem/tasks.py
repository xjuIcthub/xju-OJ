import dramatiq
from django.utils import timezone

from utils.shortcuts import DRAMATIQ_WORKER_ARGS

from .publication import publish_due_contest_problems


_TEN_YEARS_MS = 10 * 365 * 24 * 60 * 60 * 1000


@dramatiq.actor(**DRAMATIQ_WORKER_ARGS(max_retries=3, max_age=_TEN_YEARS_MS))
def publish_contest_problems(contest_id):
    publish_due_contest_problems([contest_id])


def schedule_contest_problem_publication(contest_id, end_time):
    delay = max(1000, int((end_time - timezone.now()).total_seconds() * 1000) + 1000)
    return publish_contest_problems.send_with_options(args=(contest_id,), delay=delay)


__all__ = ["publish_contest_problems", "schedule_contest_problem_publication"]
