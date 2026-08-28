# Generated manually for remote judge problem support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problem", "0015_alter_problem_io_mode_alter_problem_languages_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="judge_mode",
            field=models.TextField(default="LOCAL"),
        ),
        migrations.AddField(
            model_name="problem",
            name="remote_oj",
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name="problem",
            name="remote_problem_data",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="problem",
            name="remote_problem_id",
            field=models.TextField(db_index=True, null=True),
        ),
    ]
