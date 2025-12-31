#!/usr/bin/env python
"""
Script de prueba para verificar el formulario de Sigma Optics
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User, Group
from sigmaoptics.models import OpticsSolicitud, OpticsMuestra

def test_optics_form():
    """Probar el formulario de Sigma Optics"""
    client = Client(HTTP_HOST='localhost')
    
    # Crear usuario de prueba
    user, created = User.objects.get_or_create(
        username='test_optics_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Añadir al grupo DTF
    dtf_group, _ = Group.objects.get_or_create(name='usuarios_dtf')
    user.groups.add(dtf_group)
    
    # Verificar que el usuario tiene permisos DTF
    from core.roles import is_dtf_user
    print(f"Usuario es DTF: {is_dtf_user(user)}")
    
    # Login
    login_success = client.login(username='test_optics_user', password='testpass123')
    print(f"Login exitoso: {login_success}")
    
    if not login_success:
        print("Error: No se pudo hacer login")
        return
    
    # Probar acceso al formulario
    response = client.get('/dtf/optics/solicitud/create/')
    print(f"GET formulario - Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Formulario accesible")
    else:
        print("❌ Error al acceder al formulario")
        print(f"Contenido: {response.content[:500]}")
        return
    
    # Probar envío del formulario
    form_data = {
        'material': 'Material de prueba',
        'numero_muestras': 2,
        'referencia_muestras': 'REF-001',
        'tamano': '10x10mm',
        'medidas_realizar': 'uv_vis',
        'elemento': 'Elemento de prueba',
        'otros_datos': 'Datos adicionales de prueba',
        'muestras-TOTAL_FORMS': '2',
        'muestras-INITIAL_FORMS': '0',
        'muestras-MIN_NUM_FORMS': '0',
        'muestras-MAX_NUM_FORMS': '1000',
        'muestras-0-identificacion': 'Muestra 1',
        'muestras-0-descripcion': 'Descripción muestra 1',
        'muestras-1-identificacion': 'Muestra 2',
        'muestras-1-descripcion': 'Descripción muestra 2',
    }
    
    response = client.post('/dtf/optics/solicitud/create/', form_data)
    print(f"POST formulario - Status: {response.status_code}")
    
    if response.status_code == 302:
        print("✅ Formulario enviado correctamente (redirección)")
        # Verificar que se creó la solicitud
        solicitudes = OpticsSolicitud.objects.filter(solicitante=user)
        print(f"Solicitudes creadas: {solicitudes.count()}")
        
        if solicitudes.exists():
            solicitud = solicitudes.first()
            print(f"✅ Solicitud creada: OPT-{solicitud.id}")
            print(f"Material: {solicitud.material}")
            print(f"Estado: {solicitud.estado}")
            
            # Verificar muestras
            muestras = solicitud.muestras.all()
            print(f"Muestras creadas: {muestras.count()}")
            for muestra in muestras:
                print(f"  - {muestra.identificacion}: {muestra.descripcion}")
        else:
            print("❌ No se creó la solicitud")
    else:
        print("❌ Error al enviar el formulario")
        print(f"Contenido: {response.content[:1000]}")
        
        # Verificar si hay errores en el formulario
        if hasattr(response, 'context') and response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                print("Errores en el formulario principal:")
                for field, errors in form.errors.items():
                    print(f"  {field}: {errors}")
        
        if hasattr(response, 'context') and response.context and 'formset' in response.context:
            formset = response.context['formset']
            if not formset.is_valid():
                print("Errores en el formset:")
                for i, form_errors in enumerate(formset.errors):
                    for field, errors in form_errors.items():
                        print(f"  Muestra {i+1}, {field}: {errors}")

if __name__ == '__main__':
    test_optics_form()
