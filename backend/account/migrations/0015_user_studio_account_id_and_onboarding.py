from django.db import migrations, models
from django.core.validators import RegexValidator


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0014_externalidentity"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="studio_account_id",
            field=models.CharField(
                blank=True,
                help_text="Immutable 8-digit Studio account identifier; null only for pre-migration users.",
                max_length=8,
                null=True,
                unique=True,
                validators=[
                    RegexValidator(
                        "^[1-9][0-9]{7}$",
                        "Studio account ID must be 8 digits and start with 1-9.",
                    )
                ],
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="oj_onboarding_completed",
            field=models.BooleanField(default=True),
        ),
    ]
