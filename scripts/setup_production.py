#!/usr/bin/env python
"""
Script para configurar la aplicación en producción
"""
import os
import sys
import django
from pathlib import Path

# Añadir el directorio del proyecto al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings_production')
django.setup()

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from icts.models import Facility

def create_groups():
    """Crear grupos de usuarios necesarios"""
    groups = [
        'icts_users',
        'revisores', 
        'responsables',
        'managers',
        'usuarios_dtf',
        'tecnico_responsable_s_lab',
        'tecnico_responsable_s_mec',
        'tecnico_responsable_s_dp',
        'usuarios_autonomo_s_lab'
    ]
    
    for group_name in groups:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"✅ Grupo creado: {group_name}")
        else:
            print(f"ℹ️  Grupo ya existe: {group_name}")

def create_facilities():
    """Crear facilidades ICTS"""
    facilities = [
        ("SEM/EDX", "sem"),
        ("FIB", "fib"), 
        ("Ion Implanter", "imp"),
        ("SIMS", "sims"),
        ("Confocal", "confocal"),
        ("VDG", "vdg"),
        ("Profilometer", "profilometer")
    ]
    
    for name, code in facilities:
        facility, created = Facility.objects.get_or_create(
            name=name, 
            code=code
        )
        if created:
            print(f"✅ Facilidad creada: {name}")
        else:
            print(f"ℹ️  Facilidad ya existe: {name}")

def create_superuser():
    """Crear superusuario si no existe"""
    if not User.objects.filter(is_superuser=True).exists():
        print("\n🔐 Creando superusuario...")
        call_command('createsuperuser')
    else:
        print("ℹ️  Superusuario ya existe")

def run_migrations():
    """Ejecutar migraciones"""
    print("\n📊 Aplicando migraciones pendientes...")
    call_command('migrate', interactive=False)
    print("✅ Migraciones completadas")

def collect_static():
    """Recolectar archivos estáticos"""
    print("\n📁 Recolectando archivos estáticos...")
    call_command('collectstatic', '--noinput')
    print("✅ Archivos estáticos recolectados")

def main():
    """Función principal"""
    print("🚀 Configurando SIGMA Portal para producción...")
    
    try:
        run_migrations()
        create_groups()
        create_facilities()
        create_superuser()
        collect_static()
        
        print("\n✅ Configuración completada exitosamente!")
        print("\n📋 Próximos pasos:")
        print("1. Configurar variables de entorno (.env)")
        print("2. Configurar servidor web (Nginx/Apache)")
        print("3. Configurar SSL/HTTPS")
        print("4. Configurar backup de base de datos")
        print("5. Configurar monitoreo y logs")
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
