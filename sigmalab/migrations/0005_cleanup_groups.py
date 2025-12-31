from django.db import migrations


def cleanup_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    allowed = {
        # DTF
        'usuarios_dtf',
        'tecnico_responsable_s_lab',
        'tecnico_responsable_s_mec',
        'tecnico_responsable_s_dp',
        'usuarios_autonomo_s_lab',
        # ICTS (preservar)
        'icts_users', 'revisores', 'reviewers', 'responsables', 'managers',
    }
    qs = Group.objects.all()
    for g in qs:
        if g.name not in allowed:
            # Eliminar grupos antiguos con nombres ambiguos/acentos
            g.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('sigmalab', '0004_fix_group_names'),
        ('auth', '__latest__'),
    ]

    operations = [
        migrations.RunPython(cleanup_groups, migrations.RunPython.noop),
    ]

