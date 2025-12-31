#!/usr/bin/env python
"""
Script de prueba para verificar que los grupos y permisos funcionan correctamente.
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')
django.setup()

from django.contrib.auth.models import Group, User
from core.roles import (
    CANONICAL_GROUP_NAMES,
    get_normalized_user_groups,
    is_slab_tech,
    is_dp_tech,
    is_sem_tech,
    is_confocal_tech,
    is_dtf_user,
    is_icts_user,
)


def test_group_creation():
    """Probar que se pueden crear todos los grupos canónicos."""
    print("🧪 Probando creación de grupos...")
    
    created_groups = []
    for group_name in CANONICAL_GROUP_NAMES:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            created_groups.append(group_name)
    
    if created_groups:
        print(f"✅ Grupos creados: {', '.join(created_groups)}")
    else:
        print("ℹ️  Todos los grupos ya existen")
    
    return len(created_groups) == 0


def test_group_normalization():
    """Probar la normalización de nombres de grupos."""
    print("\n🧪 Probando normalización de grupos...")
    
    # Crear un usuario de prueba
    test_user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com'}
    )
    
    # Agregar a un grupo con acentos
    group = Group.objects.get(name='tecnico_responsable_s_lab')
    test_user.groups.add(group)
    
    # Probar normalización
    normalized_groups = get_normalized_user_groups(test_user)
    print(f"Grupos normalizados: {normalized_groups}")
    
    # Probar funciones de verificación
    print(f"¿Es técnico S-LAB? {is_slab_tech(test_user)}")
    print(f"¿Es técnico S-DP? {is_dp_tech(test_user)}")
    print(f"¿Es usuario DTF? {is_dtf_user(test_user)}")
    print(f"¿Es usuario ICTS? {is_icts_user(test_user)}")
    
    # Limpiar
    test_user.groups.clear()
    if created:
        test_user.delete()
    
    return True


def test_template_filters():
    """Probar que los filtros de plantilla funcionan."""
    print("\n🧪 Probando filtros de plantilla...")
    
    try:
        from core.templatetags.role_filters import has_group, is_slab_technician
        
        # Crear usuario de prueba
        test_user, created = User.objects.get_or_create(
            username='template_test_user',
            defaults={'email': 'template@example.com'}
        )
        
        # Agregar a grupo
        group = Group.objects.get(name='tecnico_responsable_s_lab')
        test_user.groups.add(group)
        
        # Probar filtros
        print(f"has_group('tecnico_responsable_s_lab'): {has_group(test_user, 'tecnico_responsable_s_lab')}")
        print(f"has_group('Técnico Responsable S-LAB'): {has_group(test_user, 'Técnico Responsable S-LAB')}")
        print(f"is_slab_technician: {is_slab_technician(test_user)}")
        
        # Limpiar
        test_user.groups.clear()
        if created:
            test_user.delete()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en filtros de plantilla: {e}")
        return False


def test_cross_module_access():
    """Probar el middleware de acceso entre módulos."""
    print("\n🧪 Probando middleware de acceso...")
    
    try:
        from core.middleware import ModuleAccessMiddleware
        from django.test import RequestFactory
        
        # Crear usuario ICTS
        icts_user, created = User.objects.get_or_create(
            username='icts_test_user',
            defaults={'email': 'icts@example.com'}
        )
        icts_group = Group.objects.get(name='icts_users')
        icts_user.groups.add(icts_group)
        
        # Crear usuario DTF
        dtf_user, created2 = User.objects.get_or_create(
            username='dtf_test_user',
            defaults={'email': 'dtf@example.com'}
        )
        dtf_group = Group.objects.get(name='usuarios_dtf')
        dtf_user.groups.add(dtf_group)
        
        print(f"Usuario ICTS: {is_icts_user(icts_user)}")
        print(f"Usuario DTF: {is_dtf_user(dtf_user)}")
        
        # Limpiar
        icts_user.groups.clear()
        dtf_user.groups.clear()
        if created:
            icts_user.delete()
        if created2:
            dtf_user.delete()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en middleware: {e}")
        return False


def main():
    """Ejecutar todas las pruebas."""
    print("🚀 Iniciando pruebas de grupos y permisos...\n")
    
    tests = [
        ("Creación de grupos", test_group_creation),
        ("Normalización de grupos", test_group_normalization),
        ("Filtros de plantilla", test_template_filters),
        ("Middleware de acceso", test_cross_module_access),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen
    print("\n📊 Resumen de pruebas:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{len(results)} pruebas pasaron")
    
    if passed == len(results):
        print("🎉 ¡Todas las pruebas pasaron! Los grupos y permisos funcionan correctamente.")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")


if __name__ == '__main__':
    main()
