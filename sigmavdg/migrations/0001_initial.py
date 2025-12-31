from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("icts", "0014_alter_accessproposal_access_code_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="VDGYearCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveSmallIntegerField(unique=True)),
                ("counter", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["year"],
                "verbose_name": "VDG year counter",
                "verbose_name_plural": "VDG year counters",
            },
        ),
        migrations.CreateModel(
            name="VDGSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lot_code", models.CharField(max_length=20, unique=True)),
                ("report_code", models.CharField(max_length=40, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("in_progress", "In progress"), ("completed", "Completed")],
                        default="in_progress",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("received_date", models.DateField(blank=True, null=True)),
                ("irradiation_start_date", models.DateField(blank=True, null=True)),
                ("irradiation_end_date", models.DateField(blank=True, null=True)),
                ("report_issue_date", models.DateField(blank=True, null=True)),
                ("report_delivery_date", models.DateField(blank=True, null=True)),
                ("notice_pdf", models.FileField(blank=True, null=True, upload_to="vdg/notices/")),
                ("report_pdf", models.FileField(blank=True, null=True, upload_to="vdg/reports/")),
                ("request_snapshot", models.JSONField(blank=True, default=dict)),
                ("observations", models.TextField(blank=True)),
                (
                    "access_proposal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vdg_sessions",
                        to="icts.accessproposal",
                    ),
                ),
                (
                    "technician",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="vdg_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "VDG session",
                "verbose_name_plural": "VDG sessions",
            },
        ),
        migrations.CreateModel(
            name="VDGSampleRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveIntegerField()),
                (
                    "source",
                    models.CharField(
                        choices=[("proposal", "Proposal"), ("session", "Session")],
                        default="proposal",
                        max_length=20,
                    ),
                ),
                ("code", models.CharField(blank=True, max_length=200)),
                ("material", models.CharField(blank=True, max_length=200)),
                ("electron_fluence", models.CharField(blank=True, max_length=200)),
                ("temperature", models.CharField(blank=True, max_length=200)),
                ("atmosphere", models.CharField(blank=True, max_length=200)),
                ("sample_size", models.CharField(blank=True, max_length=200)),
                ("sample_geometry", models.CharField(blank=True, max_length=200)),
                ("fluence_result", models.CharField(blank=True, max_length=200)),
                ("current_na", models.CharField(blank=True, max_length=100)),
                ("time_minutes", models.CharField(blank=True, max_length=100)),
                ("notes", models.TextField(blank=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="samples",
                        to="sigmavdg.vdgsession",
                    ),
                ),
            ],
            options={
                "ordering": ["sequence"],
                "verbose_name": "VDG sample record",
                "verbose_name_plural": "VDG sample records",
                "unique_together": {("session", "sequence")},
            },
        ),
    ]
