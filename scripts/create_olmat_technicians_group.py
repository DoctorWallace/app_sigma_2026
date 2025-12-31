#!/usr/bin/env python
"""
Script para crear el grupo de técnicos de OLMAT.
Ejecutar con: python manage.py shell < scripts/create_olmat_technicians_group.py
"""

from django.contrib.auth.models import Group

def create_olmat_technicians_group():
    """Crear el grupo de técnicos de OLMAT"""
    group_name = "olmat_technicians"
    
    # Crear el grupo si no existe
    group, created = Group.objects.get_or_create(name=group_name)
    
    if created:
        print(f"✅ Grupo '{group_name}' creado exitosamente")
    else:
        print(f"ℹ️  El grupo '{group_name}' ya existe")
    
    return group

if __name__ == "__main__":
    create_olmat_technicians_group()
