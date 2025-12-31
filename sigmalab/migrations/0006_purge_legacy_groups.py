from django.db import migrations


def purge_legacy(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    keep = {
        'usuarios_dtf',
        'tecnico_responsable_s_lab',
        'tecnico_responsable_s_mec',
        'tecnico_responsable_s_dp',
        'usuarios_autonomo_s_lab',
        'icts_users', 'revisores', 'reviewers', 'responsables', 'managers',
    }
    for g in list(Group.objects.all()):
        name = g.name
        if name in keep:
            continue
        low = name.lower()
        if ('s-mec' in low) or ('s-lab' in low) or ('tecnicos' in low) or ('técnicos' in low) or ('usuarios s-lab' in low):
            g.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('sigmalab', '0005_cleanup_groups'),
        ('auth', '__latest__'),
    ]

    operations = [
        migrations.RunPython(purge_legacy, migrations.RunPython.noop),
    ]

