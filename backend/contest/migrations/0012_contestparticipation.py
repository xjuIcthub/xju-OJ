from django.db import migrations, models
import django.db.models.deletion


def backfill_contest_participation(apps, schema_editor):
    ContestParticipation = apps.get_model("contest", "ContestParticipation")
    ACMContestRank = apps.get_model("contest", "ACMContestRank")
    OIContestRank = apps.get_model("contest", "OIContestRank")

    pairs = set(ACMContestRank.objects.values_list("contest_id", "user_id"))
    pairs.update(OIContestRank.objects.values_list("contest_id", "user_id"))
    ContestParticipation.objects.bulk_create(
        [
            ContestParticipation(contest_id=contest_id, user_id=user_id)
            for contest_id, user_id in pairs
            if contest_id and user_id
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0016_userprofile_student_id"),
        ("contest", "0011_alter_acmcontestrank_submission_info_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContestParticipation",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("join_time", models.DateTimeField(auto_now_add=True)),
                (
                    "contest",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contest.contest"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="account.user"),
                ),
            ],
            options={
                "db_table": "contest_participation",
                "ordering": ("join_time",),
                "unique_together": {("contest", "user")},
            },
        ),
        migrations.RunPython(backfill_contest_participation, migrations.RunPython.noop),
    ]
