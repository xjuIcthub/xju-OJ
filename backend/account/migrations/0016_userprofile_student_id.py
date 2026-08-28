from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0015_user_studio_account_id_and_onboarding"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="student_id",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]
