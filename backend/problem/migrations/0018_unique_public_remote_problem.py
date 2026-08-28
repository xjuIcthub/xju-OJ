from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problem", "0017_problem_post_contest_publish"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="problem",
            constraint=models.UniqueConstraint(
                fields=("remote_oj", "remote_problem_id"),
                condition=models.Q(
                    contest__isnull=True,
                    judge_mode="REMOTE",
                ),
                name="unique_public_remote_problem",
            ),
        ),
    ]
