from utils.constants import Difficulty

from .codeforces import (CodeforcesProblemError,
                         build_codeforces_problem_from_page,
                         fetch_codeforces_problem)
from .common import RemoteProblemError
from .luogu import LuoguProblemError, fetch_luogu_problem
from .nowcoder import NowcoderProblemError, fetch_nowcoder_problem


def fetch_remote_problem(provider, reference, page_html=""):
    if provider == "NOWCODER":
        problem = fetch_nowcoder_problem(reference)
        is_acm_problem = problem.get("kind") == "acm"
        default_display_id = problem["remote_id"] if is_acm_problem else f"NC{problem['question_id']}"
        return {
            **problem,
            "remote_id": problem["remote_id"],
            "default_display_id": default_display_id,
            "tag": "牛客",
            "source": f"牛客 {problem['remote_id']}",
            "difficulty": Difficulty.LOW,
            "metadata": {
                "kind": problem.get("kind"),
                "problem_id": problem.get("problem_id"),
                "question_id": problem["question_id"],
                "uuid": problem.get("uuid"),
                "url": problem["url"],
                "language_ids": problem["language_ids"],
                "support_lang": problem["support_lang"],
                "problem_type": problem["problem_type"],
                "code_judge_type": problem["code_judge_type"],
                "tag_id": problem.get("tag_id"),
            },
        }
    if provider == "LUOGU":
        problem = fetch_luogu_problem(reference)
        difficulty_value = problem.get("difficulty_value")
        difficulty = Difficulty.LOW
        if isinstance(difficulty_value, int) and difficulty_value >= 4:
            difficulty = Difficulty.HIGH
        elif isinstance(difficulty_value, int) and difficulty_value >= 2:
            difficulty = Difficulty.MID
        return {
            **problem,
            "default_display_id": f"LG{problem['remote_id']}",
            "tag": "洛谷",
            "source": f"洛谷 {problem['remote_id']}",
            "difficulty": difficulty,
            "metadata": {
                "problem_id": problem["problem_id"],
                "url": problem["url"],
                "language_ids": problem["language_ids"],
                "accepted_language_ids": problem["accepted_language_ids"],
                "problem_type": problem["problem_type"],
                "difficulty": difficulty_value,
            },
        }
    if provider == "CODEFORCES":
        problem = (
            build_codeforces_problem_from_page(reference, page_html)
            if page_html
            else fetch_codeforces_problem(reference)
        )
        rating = problem.get("rating")
        difficulty = Difficulty.LOW
        if isinstance(rating, int) and rating >= 1900:
            difficulty = Difficulty.HIGH
        elif isinstance(rating, int) and rating >= 1300:
            difficulty = Difficulty.MID
        return {
            **problem,
            "default_display_id": f"CF{problem['remote_id']}",
            "tag": "Codeforces",
            "source": f"Codeforces {problem['remote_id']}",
            "difficulty": difficulty,
            "metadata": {
                "contest_id": problem["contest_id"],
                "index": problem["index"],
                "url": problem["url"],
                "language_ids": problem["language_ids"],
                "rating": rating,
                "tags": problem["tags"],
            },
        }
    raise RemoteProblemError("Unsupported remote OJ")


__all__ = [
    "CodeforcesProblemError",
    "LuoguProblemError",
    "NowcoderProblemError",
    "RemoteProblemError",
    "fetch_codeforces_problem",
    "build_codeforces_problem_from_page",
    "fetch_luogu_problem",
    "fetch_nowcoder_problem",
    "fetch_remote_problem",
]
