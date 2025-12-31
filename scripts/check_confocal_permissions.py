#!/usr/bin/env python
"""
Script para verificar y corregir permisos de SIGMACONF
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

def check_confocal_permissions():
    """Verifica la configuración de permisos de SIGMACONF"""
    
    print("🔍 Verificando configuración de SIGMACONF...")
    print("=" * 50)
    
    # Verificar grupo
    try:
        group = Group.objects.get(name='Confocal Technicians')
        print(f"✅ Grupo 'Confocal Technicians' existe")
        
        users_in_group = group.user_set.all()
        print(f"👥 Usuarios en el grupo: {users_in_group.count()}")
        
        for user in users_in_group:
            print(f"   - {user.get_full_name()} ({user.username}) - {user.email}")
            
    except Group.DoesNotExist:
        print("❌ Grupo 'Confocal Technicians' NO existe")
        return False
    
    # Verificar usuarios DTF
    print(f"\n🔍 Verificando usuarios DTF...")
    try:
        dtf_group = Group.objects.get(name='DTF Users')
        dtf_users = dtf_group.user_set.all()
        print(f"👥 Usuarios DTF: {dtf_users.count()}")
        
        for user in dtf_users:
            print(f"   - {user.get_full_name()} ({user.username}) - {user.email}")
            
    except Group.DoesNotExist:
        print("❌ Grupo 'DTF Users' NO existe")
    
    # Verificar usuarios staff
    staff_users = User.objects.filter(is_staff=True)
    print(f"\n👑 Usuarios staff: {staff_users.count()}")
    
    for user in staff_users:
        print(f"   - {user.get_full_name()} ({user.username}) - {user.email}")
    
    return True

def test_user_permissions(username):
    """Prueba los permisos de un usuario específico"""
    
    try:
        user = User.objects.get(username=username)
        print(f"\n🧪 Probando permisos para: {user.get_full_name()} ({user.username})")
        print("-" * 40)
        
        # Verificar grupos
        groups = user.groups.all()
        print(f"📋 Grupos del usuario: {groups.count()}")
        for group in groups:
            print(f"   - {group.name}")
        
        # Verificar permisos específicos
        is_confocal_tech = user.groups.filter(name='Confocal Technicians').exists()
        is_dtf_user = user.groups.filter(name='DTF Users').exists()
        is_staff = user.is_staff
        
        print(f"\n🔐 Permisos:")
        print(f"   - Es técnico confocal: {'✅' if is_confocal_tech else '❌'}")
        print(f"   - Es usuario DTF: {'✅' if is_dtf_user else '❌'}")
        print(f"   - Es staff: {'✅' if is_staff else '❌'}")
        
        # Verificar acceso a SIGMACONF
        can_access_confocal = is_dtf_user or is_confocal_tech or is_staff
        print(f"   - Puede acceder a SIGMACONF: {'✅' if can_access_confocal else '❌'}")
        
        return {
            'is_confocal_tech': is_confocal_tech,
            'is_dtf_user': is_dtf_user,
            'is_staff': is_staff,
            'can_access_confocal': can_access_confocal
        }
        
    except User.DoesNotExist:
        print(f"❌ Usuario {username} no existe")
        return None

def add_user_to_confocal_technicians(username):
    """Agrega un usuario al grupo de técnicos de confocal"""
    
    try:
        user = User.objects.get(username=username)
        group = Group.objects.get(name='Confocal Technicians')
        
        if user in group.user_set.all():
            print(f"ℹ️  El usuario {username} ya está en el grupo 'Confocal Technicians'")
        else:
            group.user_set.add(user)
            print(f"✅ Usuario {username} agregado al grupo 'Confocal Technicians'")
            
        # Verificar después de agregar
        test_user_permissions(username)
            
    except User.DoesNotExist:
        print(f"❌ Error: El usuario {username} no existe")
    except Group.DoesNotExist:
        print("❌ Error: El grupo 'Confocal Technicians' no existe")

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'test' and len(sys.argv) > 2:
            username = sys.argv[2]
            test_user_permissions(username)
        elif command == 'add' and len(sys.argv) > 2:
            username = sys.argv[2]
            add_user_to_confocal_technicians(username)
        else:
            print("❌ Comandos disponibles:")
            print("   python check_confocal_permissions.py test <username>")
            print("   python check_confocal_permissions.py add <username>")
    else:
        check_confocal_permissions()

if __name__ == '__main__':
    main()

