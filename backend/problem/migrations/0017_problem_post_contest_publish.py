from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problem", "0016_problem_remote_judge_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="publish_after_contest",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="problem",
            name="post_contest_display_id",
            field=models.TextField(null=True),
        ),
    ]
