import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

from options.models import SysOptions


class Command(BaseCommand):
    help = "Create the JudgeServer token once from an external secret source."

    def handle(self, *args, **options):
        token = os.environ.get("JUDGE_SERVER_TOKEN", "").strip()
        token_file = os.environ.get("JUDGE_SERVER_TOKEN_FILE")
        if not token and token_file:
            try:
                token = Path(token_file).read_text().strip()
            except OSError as exc:
                raise CommandError("JUDGE_SERVER_TOKEN_FILE cannot be read") from exc

        if not token:
            raise CommandError("JUDGE_SERVER_TOKEN or JUDGE_SERVER_TOKEN_FILE is required")

        if SysOptions.objects.filter(key="judge_server_token").exists():
            raise CommandError("JudgeServer token is already configured; refusing to overwrite it")

        try:
            with transaction.atomic():
                SysOptions.objects.create(key="judge_server_token", value=token)
        except IntegrityError as exc:
            raise CommandError("JudgeServer token was configured concurrently; refusing to overwrite it") from exc

        self.stdout.write(self.style.SUCCESS("JudgeServer token configured"))
