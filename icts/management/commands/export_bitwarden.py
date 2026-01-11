from __future__ import annotations

import csv
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Export users to Bitwarden CSV (prints to stdout)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--login-uri",
            default="http://127.0.0.1:8006/accounts/login/icts/?next=/icts/dashboard/",
            help="Value for login_uri column.",
        )
        parser.add_argument(
            "--folder",
            default="ICTS",
            help="Value for folder column.",
        )
        parser.add_argument(
            "--password-default",
            default="u1627729",
            help="Password to put for non-superusers.",
        )
        parser.add_argument(
            "--password-admin",
            default="1234",
            help="Password to put for superusers.",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Include inactive users too.",
        )
        parser.add_argument(
            "--exclude-group",
            default=None,
            help="Exclude users belonging to this Django auth group (e.g. icts_users).",
        )

    def handle(self, *args, **options):
        login_uri: str = options["login_uri"]
        folder: str = options["folder"]
        password_default: str = options["password_default"]
        password_admin: str = options["password_admin"]
        include_inactive: bool = options["include_inactive"]
        exclude_group: str | None = options["exclude_group"]

        User = get_user_model()
        qs = User.objects.all().order_by("username")
        if not include_inactive:
            qs = qs.filter(is_active=True)
        if exclude_group:
            try:
                group = Group.objects.get(name=exclude_group)
                qs = qs.exclude(groups=group)
            except Group.DoesNotExist:
                # If group doesn't exist, nothing to exclude.
                pass

        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(
            [
                "folder",
                "favorite",
                "type",
                "name",
                "notes",
                "fields",
                "reprompt",
                "login_uri",
                "login_username",
                "login_password",
                "login_totp",
            ]
        )

        for user in qs.iterator():
            login_username = user.get_username()
            login_password = password_admin if user.is_superuser else password_default
            name = login_username
            writer.writerow(
                [
                    folder,
                    "",
                    "login",
                    name,
                    "",
                    "",
                    "0",
                    login_uri,
                    login_username,
                    login_password,
                    "",
                ]
            )

