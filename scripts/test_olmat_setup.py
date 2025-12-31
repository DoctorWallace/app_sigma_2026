#!/usr/bin/env python
"""
Script para probar la configuración de OLMAT.
Ejecutar con: python manage.py shell < scripts/test_olmat_setup.py
"""

from django.contrib.auth.models import Group, User
from icts.models import AccessProposal, OLMATRequest
from core.roles import OLMAT_TECH_GROUPS

def test_olmat_setup():
    """Probar la configuración de OLMAT"""
    print("🧪 Probando configuración de OLMAT...")
    
    # 1. Verificar que el grupo de técnicos existe
    try:
        group = Group.objects.get(name="olmat_technicians")
        print("✅ Grupo 'olmat_technicians' existe")
    except Group.DoesNotExist:
        print("❌ Grupo 'olmat_technicians' no existe")
        return False
    
    # 2. Verificar que el modelo OLMATRequest funciona
    try:
        # Crear un usuario de prueba si no existe
        user, created = User.objects.get_or_create(
            username="test_olmat_user",
            defaults={
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User"
            }
        )
        if created:
            print("✅ Usuario de prueba creado")
        else:
            print("ℹ️  Usuario de prueba ya existe")
        
        # Crear una propuesta de prueba
        proposal, created = AccessProposal.objects.get_or_create(
            title="Test OLMAT Proposal",
            applicant=user,
            defaults={
                "scope": "Test scope",
                "facility_olmat": True
            }
        )
        if created:
            print("✅ Propuesta de prueba creada")
        else:
            print("ℹ️  Propuesta de prueba ya existe")
        
        # Crear una solicitud OLMAT de prueba
        olmat_request, created = OLMATRequest.objects.get_or_create(
            proposal=proposal,
            defaults={
                "service_type": "technical",
                "irradiation_requirements": "Test requirements",
                "diagnostics_needed": ["thermocouples", "pyrometry"],
                "sample_preparation": ["liquid_metal_wetting"],
                "beam_usage": ["nbi"],
                "preferred_dates": "2024-06-01",
                "flexibility": "medium",
                "additional_requirements": "Test additional requirements"
            }
        )
        if created:
            print("✅ Solicitud OLMAT de prueba creada")
        else:
            print("ℹ️  Solicitud OLMAT de prueba ya existe")
        
        # Verificar propiedades
        print(f"✅ Coste base: {olmat_request.base_cost} €")
        print(f"✅ Estado: {olmat_request.get_status_display()}")
        print(f"✅ Tipo de servicio: {olmat_request.get_service_type_display()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al probar modelos: {e}")
        return False

if __name__ == "__main__":
    success = test_olmat_setup()
    if success:
        print("\n🎉 ¡Configuración de OLMAT completada exitosamente!")
    else:
        print("\n💥 Hubo errores en la configuración de OLMAT")
