# Generated manually for browser-bridged remote submissions.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("submission", "0013_alter_submission_info_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="judge_mode",
            field=models.TextField(default="LOCAL"),
        ),
        migrations.AddField(
            model_name="submission",
            name="remote_oj",
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="remote_submission_id",
            field=models.TextField(db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="remote_status",
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="remote_url",
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="remote_message",
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="remote_data",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="submission",
            name="remote_update_time",
            field=models.DateTimeField(null=True),
        ),
    ]
