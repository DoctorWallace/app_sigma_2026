#!/usr/bin/env python
"""
Script para crear el grupo de técnicos de confocal
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')
django.setup()

from django.contrib.auth.models import Group, User
from django.contrib.auth import get_user_model

def create_confocal_technicians_group():
    """Crea el grupo de técnicos de confocal"""
    
    # Crear el grupo si no existe
    group, created = Group.objects.get_or_create(name='Confocal Technicians')
    
    if created:
        print("✅ Grupo 'Confocal Technicians' creado exitosamente")
    else:
        print("ℹ️  El grupo 'Confocal Technicians' ya existe")
    
    # Mostrar usuarios en el grupo
    users_in_group = group.user_set.all()
    print(f"\n👥 Usuarios en el grupo 'Confocal Technicians': {users_in_group.count()}")
    
    for user in users_in_group:
        print(f"   - {user.get_full_name()} ({user.username})")
    
    if users_in_group.count() == 0:
        print("\n💡 Para agregar usuarios al grupo, puedes:")
        print("   1. Usar el admin de Django: /admin/auth/group/")
        print("   2. O ejecutar este script con argumentos: python create_confocal_technicians_group.py add <username>")
    
    return group

def add_user_to_group(username):
    """Agrega un usuario al grupo de técnicos de confocal"""
    try:
        user = User.objects.get(username=username)
        group = Group.objects.get(name='Confocal Technicians')
        
        if user in group.user_set.all():
            print(f"ℹ️  El usuario {username} ya está en el grupo 'Confocal Technicians'")
        else:
            group.user_set.add(user)
            print(f"✅ Usuario {username} agregado al grupo 'Confocal Technicians'")
            
    except User.DoesNotExist:
        print(f"❌ Error: El usuario {username} no existe")
    except Group.DoesNotExist:
        print("❌ Error: El grupo 'Confocal Technicians' no existe")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'add':
        if len(sys.argv) > 2:
            username = sys.argv[2]
            add_user_to_group(username)
        else:
            print("❌ Error: Debe especificar un nombre de usuario")
            print("Uso: python create_confocal_technicians_group.py add <username>")
    else:
        create_confocal_technicians_group()

if __name__ == '__main__':
    main()

