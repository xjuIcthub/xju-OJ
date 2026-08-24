from django.urls import re_path

from ..views.oj import ProblemTagAPI, ProblemAPI, ContestProblemAPI, PickOneAPI

urlpatterns = [
    re_path(r"^problem/tags/?$", ProblemTagAPI.as_view(), name="problem_tag_list_api"),
    re_path(r"^problem/?$", ProblemAPI.as_view(), name="problem_api"),
    re_path(r"^pickone/?$", PickOneAPI.as_view(), name="pick_one_api"),
    re_path(r"^contest/problem/?$", ContestProblemAPI.as_view(), name="contest_problem_api"),
]
