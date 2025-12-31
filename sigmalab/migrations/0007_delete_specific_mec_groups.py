from django.db import migrations


def delete_specific(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in [
        'Tecnicos S-MEC',
        'Tecnicos responsables S-MEC',
        'Técnicos S-MEC',
        'Técnicos responsables S-MEC',
    ]:
        Group.objects.filter(name=name).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('sigmalab', '0006_purge_legacy_groups'),
        ('auth', '__latest__'),
    ]

    operations = [
        migrations.RunPython(delete_specific, migrations.RunPython.noop),
    ]

