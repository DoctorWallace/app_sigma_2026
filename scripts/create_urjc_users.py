"""Crear usuarios URJC"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.conf import settings
if not settings.configured:
    django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from icts.models import ICTSUserProfile

User = get_user_model()
icts_group, _ = Group.objects.get_or_create(name='icts_users')

# Usuario 1: Belen Arredondo
user1, created1 = User.objects.get_or_create(
    username='belen.arredondo',
    defaults={
        'email': 'belen.arredondo@urjc.es',
        'first_name': 'Belen',
        'last_name': 'Arredondo Conchillo',
        'is_active': True,
    }
)
if created1:
    user1.set_password('urjc2025')
    user1.save()
profile1, _ = ICTSUserProfile.objects.get_or_create(
    user=user1, 
    defaults={'center': 'URJC', 'validated': True}
)
user1.groups.add(icts_group)
status1 = "CREADO" if created1 else "ya existia"
print(f"Usuario 1: {user1.username} ({user1.email}) - {status1}")

# Usuario 2: Diego Martin
user2, created2 = User.objects.get_or_create(
    username='diego.martin',
    defaults={
        'email': 'diego.martin.martin@urjc.es',
        'first_name': 'Diego',
        'last_name': 'Martin Martin',
        'is_active': True,
    }
)
if created2:
    user2.set_password('urjc2025')
    user2.save()
profile2, _ = ICTSUserProfile.objects.get_or_create(
    user=user2, 
    defaults={'center': 'URJC', 'validated': True}
)
user2.groups.add(icts_group)
status2 = "CREADO" if created2 else "ya existia"
print(f"Usuario 2: {user2.username} ({user2.email}) - {status2}")

print(f"\nAmbos usuarios en grupo icts_users: OK")
print(f"Total usuarios en icts_users: {icts_group.user_set.count()}")
