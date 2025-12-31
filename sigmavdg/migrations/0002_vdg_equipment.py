from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sigmavdg", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VDGEquipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_reference", models.BooleanField(default=False)),
                ("responsible", models.CharField(blank=True, max_length=200)),
                ("location", models.CharField(blank=True, max_length=200)),
                ("received_date", models.DateField(blank=True, null=True)),
                ("decommission_date", models.DateField(blank=True, null=True)),
                ("observations", models.TextField(blank=True)),
                ("brand", models.CharField(blank=True, max_length=200)),
                ("model", models.CharField(blank=True, max_length=200)),
                ("serial_number", models.CharField(blank=True, max_length=200)),
                ("range", models.CharField(blank=True, max_length=200)),
                ("resolution", models.CharField(blank=True, max_length=200)),
                ("tolerance", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["code"],
                "verbose_name": "VDG equipment",
                "verbose_name_plural": "VDG equipment",
            },
        ),
        migrations.CreateModel(
            name="VDGEquipmentDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "doc_type",
                    models.CharField(
                        choices=[
                            ("certificate", "Certificado"),
                            ("calibration", "Calibracion"),
                            ("maintenance", "Mantenimiento"),
                            ("other", "Otro"),
                        ],
                        default="other",
                        max_length=20,
                    ),
                ),
                ("file", models.FileField(upload_to="vdg/equipment/")),
                ("date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="sigmavdg.vdgequipment",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vdg_equipment_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "VDG equipment document",
                "verbose_name_plural": "VDG equipment documents",
            },
        ),
        migrations.CreateModel(
            name="VDGEquipmentIncident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                (
                    "severity",
                    models.CharField(
                        choices=[("low", "Baja"), ("medium", "Media"), ("high", "Alta")],
                        default="low",
                        max_length=10,
                    ),
                ),
                ("description", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Abierta"),
                            ("in_progress", "En curso"),
                            ("closed", "Cerrada"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("attachment", models.FileField(blank=True, null=True, upload_to="vdg/incidents/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incidents",
                        to="sigmavdg.vdgequipment",
                    ),
                ),
            ],
            options={
                "ordering": ["-date", "-created_at"],
                "verbose_name": "VDG equipment incident",
                "verbose_name_plural": "VDG equipment incidents",
            },
        ),
    ]
