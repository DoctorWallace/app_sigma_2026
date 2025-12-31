"""
Create implant technician groups if they do not exist.
"""
from django.db import migrations


def create_implant_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for group_name in ("implant_technicians", "tecnico_imp"):
        Group.objects.get_or_create(name=group_name)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_create_canonical_groups"),
    ]

    operations = [
        migrations.RunPython(create_implant_groups, migrations.RunPython.noop),
    ]
