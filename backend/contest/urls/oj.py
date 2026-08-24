from django.urls import re_path

from ..views.oj import ContestAnnouncementListAPI
from ..views.oj import ContestPasswordVerifyAPI, ContestAccessAPI
from ..views.oj import ContestListAPI, ContestAPI
from ..views.oj import ContestRankAPI

urlpatterns = [
    re_path(r"^contests/?$", ContestListAPI.as_view(), name="contest_list_api"),
    re_path(r"^contest/?$", ContestAPI.as_view(), name="contest_api"),
    re_path(r"^contest/password/?$", ContestPasswordVerifyAPI.as_view(), name="contest_password_api"),
    re_path(r"^contest/announcement/?$", ContestAnnouncementListAPI.as_view(), name="contest_announcement_api"),
    re_path(r"^contest/access/?$", ContestAccessAPI.as_view(), name="contest_access_api"),
    re_path(r"^contest_rank/?$", ContestRankAPI.as_view(), name="contest_rank_api"),
]
