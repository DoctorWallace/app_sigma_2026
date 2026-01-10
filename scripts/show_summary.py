"""Mostrar resumen de importación"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')

import django
django.setup()

from icts.models import AccessProposal, Participant
from django.contrib.auth import get_user_model
from django.db.models import Count

User = get_user_model()

print('RESUMEN FINAL DE IMPORTACION')
print('='*50)
print(f'Total propuestas: {AccessProposal.objects.count()}')
print(f'Total participantes: {Participant.objects.count()}')
print(f'Total usuarios: {User.objects.count()}')

print('\nPROPUESTAS POR STATUS:')
for item in AccessProposal.objects.values('status').annotate(c=Count('id')).order_by('-c'):
    print(f"  {item['status']:<20} {item['c']:>5}")

print('\nPROPUESTAS POR TECNICA:')
tecnicas = [
    ('SEM', 'facility_sem'),
    ('SEM-FIB', 'facility_sem_fib'),
    ('SIMS', 'facility_sims'),
    ('Implantador', 'facility_imp'),
    ('VdG', 'facility_vdg'),
    ('Confocal', 'facility_confocal'),
    ('Optics', 'facility_optics'),
    ('Profilometer', 'facility_profilometer'),
]
for name, field in tecnicas:
    count = AccessProposal.objects.filter(**{field: True}).count()
    if count > 0:
        print(f"  {name:<15} {count:>5}")
