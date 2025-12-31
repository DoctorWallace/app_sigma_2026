from django.contrib.auth.models import Group

KEEP = {
    'usuarios_dtf', 'tecnico_responsable_s_lab', 'tecnico_responsable_s_mec', 'tecnico_responsable_s_dp', 'usuarios_autonomo_s_lab',
    'icts_users', 'revisores', 'reviewers', 'responsables', 'managers',
}

removed = []
for g in list(Group.objects.all()):
    if g.name not in KEEP:
        removed.append(g.name)
        g.delete()

print('removed:', sorted(removed))

