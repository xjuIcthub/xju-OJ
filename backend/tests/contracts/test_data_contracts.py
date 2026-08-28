from django.conf import settings
from django.test import SimpleTestCase

from account.models import User, UserProfile
from announcement.models import Announcement
from conf.models import JudgeServer
from contest.models import (ACMContestRank, Contest, ContestAnnouncement,
                            ContestParticipation, OIContestRank)
from options.models import SysOptions
from problem.models import Problem, ProblemTag


class DataIdentityContractTests(SimpleTestCase):
    def test_app_and_table_identity(self):
        expected_tables = {
            User: "user",
            UserProfile: "user_profile",
            Announcement: "announcement",
            JudgeServer: "judge_server",
            Problem: "problem",
            ProblemTag: "problem_tag",
            Contest: "contest",
            ACMContestRank: "acm_contest_rank",
            OIContestRank: "oi_contest_rank",
            ContestAnnouncement: "contest_announcement",
            ContestParticipation: "contest_participation",
            SysOptions: "options_sysoptions",
        }

        for model, table in expected_tables.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.db_table, table)

        self.assertEqual(settings.DEFAULT_AUTO_FIELD, "django.db.models.AutoField")

    def test_redis_db_assignments(self):
        self.assertTrue(settings.CACHES["default"]["LOCATION"].endswith("/1"))
        self.assertTrue(settings.DRAMATIQ_BROKER["OPTIONS"]["url"].endswith("/4"))
        self.assertTrue(settings.DRAMATIQ_RESULT_BACKEND["BACKEND_OPTIONS"]["url"].endswith("/4"))
