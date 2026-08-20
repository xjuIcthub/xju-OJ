import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account.models import AdminType, ProblemPermission, User, UserProfile


class Command(BaseCommand):
    help = "Create an initial administrator from an external password file, once."

    def handle(self, *args, **options):
        if User.objects.filter(admin_type=AdminType.SUPER_ADMIN).exists():
            self.stdout.write(self.style.SUCCESS("A super administrator already exists; operation ignored"))
            return

        username = os.environ.get("INITIAL_ADMIN_USERNAME", "").strip()
        password_file = os.environ.get("INITIAL_ADMIN_PASSWORD_FILE", "")
        if not username or not password_file:
            raise CommandError("INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD_FILE are required")

        try:
            password = Path(password_file).read_text().rstrip("\r\n")
        except OSError as exc:
            raise CommandError("INITIAL_ADMIN_PASSWORD_FILE cannot be read") from exc

        if len(password) < 12:
            raise CommandError("initial administrator password must be at least 12 characters")
        if User.objects.filter(username=username).exists():
            raise CommandError("initial administrator username already exists")

        with transaction.atomic():
            user = User.objects.create(
                username=username,
                admin_type=AdminType.SUPER_ADMIN,
                problem_permission=ProblemPermission.ALL,
            )
            user.set_password(password)
            user.save(update_fields=["password"])
            UserProfile.objects.create(user=user)

        self.stdout.write(self.style.SUCCESS("Initial administrator created"))
