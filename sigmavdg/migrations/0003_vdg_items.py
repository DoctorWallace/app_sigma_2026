from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sigmavdg", "0002_vdg_equipment"),
    ]

    operations = [
        migrations.CreateModel(
            name="VDGItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("description", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["code"],
                "verbose_name": "VDG item",
                "verbose_name_plural": "VDG items",
            },
        ),
        migrations.CreateModel(
            name="VDGItemMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_salida", models.DateField()),
                ("motivo_salida", models.CharField(max_length=200)),
                ("forma_envio", models.CharField(blank=True, max_length=200)),
                ("destino", models.CharField(blank=True, max_length=200)),
                ("responsable_destino", models.CharField(blank=True, max_length=200)),
                ("cumplimentado_por_salida", models.CharField(blank=True, max_length=200)),
                ("fecha_entrada", models.DateField(blank=True, null=True)),
                (
                    "estado_recepcion",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("ok", "Ok"),
                            ("damaged", "Danado"),
                            ("not_received", "No recibido"),
                            ("other", "Otro"),
                        ],
                        max_length=20,
                    ),
                ),
                ("estado_recepcion_detalle", models.CharField(blank=True, max_length=200)),
                ("cumplimentado_por_entrada", models.CharField(blank=True, max_length=200)),
                ("notas", models.TextField(blank=True)),
                (
                    "item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movements",
                        to="sigmavdg.vdgitem",
                    ),
                ),
            ],
            options={
                "ordering": ["-fecha_salida"],
                "verbose_name": "VDG item movement",
                "verbose_name_plural": "VDG item movements",
            },
        ),
    ]
