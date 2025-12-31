#!/usr/bin/env python
"""
Script para crear el grupo de técnicos SEM/FIB
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')
django.setup()

from django.contrib.auth.models import Group, User

def create_sem_technicians_group():
    """Crear el grupo de técnicos SEM/FIB"""
    
    # Crear el grupo
    group, created = Group.objects.get_or_create(name='tecnicos_SEM_FIB')
    
    if created:
        print("✅ Grupo 'tecnicos_SEM_FIB' creado exitosamente.")
    else:
        print("ℹ️  El grupo 'tecnicos_SEM_FIB' ya existe.")
    
    # Mostrar usuarios en el grupo
    users_in_group = group.user_set.all()
    print(f"\n👥 Usuarios en el grupo 'tecnicos_SEM_FIB': {users_in_group.count()}")
    
    for user in users_in_group:
        print(f"  - {user.username} ({user.get_full_name() or 'Sin nombre'})")
    
    if users_in_group.count() == 0:
        print("\n💡 Para agregar usuarios al grupo, puedes:")
        print("   1. Usar el admin de Django: /admin/auth/group/")
        print("   2. O ejecutar: python manage.py shell")
        print("      >>> from django.contrib.auth.models import Group, User")
        print("      >>> group = Group.objects.get(name='tecnicos_SEM_FIB')")
        print("      >>> user = User.objects.get(username='nombre_usuario')")
        print("      >>> group.user_set.add(user)")
    
    return group

if __name__ == "__main__":
    create_sem_technicians_group()

