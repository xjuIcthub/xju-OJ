from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0013_alter_user_session_keys_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExternalIdentity",
            fields=[
                (
                    "id",
                    models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("provider", models.CharField(default="authentik", max_length=64)),
                ("issuer", models.URLField(max_length=512)),
                ("subject", models.CharField(max_length=255)),
                ("email", models.TextField(blank=True, null=True)),
                ("email_verified", models.BooleanField(default=False)),
                ("claims", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_login_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_identities",
                        to="account.user",
                    ),
                ),
            ],
            options={
                "db_table": "external_identity",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("issuer", "subject"),
                        name="external_identity_issuer_subject_uniq",
                    ),
                ],
            },
        ),
    ]
