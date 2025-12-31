"""
Create VDG and IMP technician groups if they do not exist.
"""
from django.db import migrations


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for group_name in ("vdg_technicians", "tecnico_vdg", "imp_technicians"):
        Group.objects.get_or_create(name=group_name)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_add_implant_groups"),
    ]

    operations = [
        migrations.RunPython(create_groups, migrations.RunPython.noop),
    ]
