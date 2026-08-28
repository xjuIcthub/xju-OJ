from django.db import migrations


def backfill_submission_participation(apps, schema_editor):
    ContestParticipation = apps.get_model("contest", "ContestParticipation")
    Contest = apps.get_model("contest", "Contest")
    ACMContestRank = apps.get_model("contest", "ACMContestRank")
    OIContestRank = apps.get_model("contest", "OIContestRank")
    Submission = apps.get_model("submission", "Submission")
    pairs = list(
        Submission.objects.exclude(contest_id__isnull=True)
        .values_list("contest_id", "user_id")
        .distinct()
    )
    ContestParticipation.objects.bulk_create(
        [
            ContestParticipation(contest_id=contest_id, user_id=user_id)
            for contest_id, user_id in pairs
            if contest_id and user_id
        ],
        ignore_conflicts=True,
    )
    contest_rules = dict(
        Contest.objects.filter(id__in={contest_id for contest_id, _user_id in pairs})
        .values_list("id", "rule_type")
    )
    ACMContestRank.objects.bulk_create(
        [
            ACMContestRank(contest_id=contest_id, user_id=user_id)
            for contest_id, user_id in pairs
            if contest_rules.get(contest_id) == "ACM"
        ],
        ignore_conflicts=True,
    )
    OIContestRank.objects.bulk_create(
        [
            OIContestRank(contest_id=contest_id, user_id=user_id)
            for contest_id, user_id in pairs
            if contest_rules.get(contest_id) == "OI"
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("contest", "0012_contestparticipation"),
        ("submission", "0014_submission_remote_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_submission_participation, migrations.RunPython.noop),
    ]
