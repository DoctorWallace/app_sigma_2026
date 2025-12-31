from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import DTFUserProfile, InfoImportanteAcceso
from .services.dashboard import build_dashboard_data
from .decorators import dtf_required


@dtf_required
def dashboard(request):
    """DTF Dashboard Principal - Resumen unificado de todos los laboratorios DTF"""

    # Verificar que el usuario pertenece al grupo usuarios_dtf
    if (
        not request.user.groups.filter(name="usuarios_dtf").exists()
        and not request.user.is_superuser
    ):
        messages.error(request, "No tienes permisos para acceder al dashboard DTF.")
        return redirect("accounts:login_dtf")

    # Verificar si el usuario ha completado la informacion importante
    try:
        profile = request.user.dtf_profile
        if not profile.info_importante_completada:
            messages.info(
                request,
                "Debes completar la informacion importante antes de acceder al dashboard.",
            )
            return redirect("dtf:info-importante")
    except DTFUserProfile.DoesNotExist:
        # Si no tiene perfil DTF, crear uno y redirigir
        DTFUserProfile.objects.create(user=request.user)
        messages.info(
            request,
            "Debes completar la informacion importante antes de acceder al dashboard.",
        )
        return redirect("dtf:info-importante")

    dashboard_data = build_dashboard_data(request.user)
    labs = dashboard_data["labs"]
    totals = dashboard_data["totals"]

    sigmalab = labs["sigmalab"]
    mec = labs["mec"]
    sigmadp = labs["sigmadp"]
    sigmaoptics = labs["sigmaoptics"]

    context = {
        "total_solicitudes": totals["total_solicitudes"],
        "total_pendientes": totals["pendientes"],
        "total_en_curso": totals["en_curso"],
        "total_finalizadas": totals["finalizadas"],
        "slab_recuento": sigmalab.counts,
        "smec_recuento": mec.counts,
        "sigmadp_recuento": sigmadp.counts,
        "sigmaoptics_recuento": sigmaoptics.counts,
        "ultimas_slab": sigmalab.latest,
        "ultimas_smec": mec.latest,
        "ultimas_sigmadp": sigmadp.latest,
        "ultimas_sigmaoptics": sigmaoptics.latest,
        "slab_total": sigmalab.total,
        "smec_total": mec.total,
        "stats": dashboard_data["stats"],
        "mec_solicitudes": mec.queryset[:10],  # Últimas 10 para el dashboard
        "slab_solicitudes": sigmalab.queryset[:10],  # Últimas 10 para el dashboard
        "sigmadp_solicitudes": sigmadp.queryset[:10],  # Últimas 10 para el dashboard
        "sigmaoptics_solicitudes": sigmaoptics.queryset[:10],  # Últimas 10 para el dashboard
    }

    return render(request, 'dtf/dashboard.html', context)


@dtf_required
def info_importante(request):
    """Panel de información importante para usuarios DTF"""
    profile, created = DTFUserProfile.objects.get_or_create(user=request.user)
    
    # Si es la primera vez que accede, registrar el inicio
    if not profile.info_importante_inicio:
        profile.info_importante_inicio = timezone.now()
        profile.save()
    
    # Obtener las secciones ya accedidas por el usuario
    secciones_accedidas = InfoImportanteAcceso.objects.filter(user=request.user).values_list('seccion', flat=True)
    
    # Definir todas las secciones disponibles
    todas_las_secciones = [choice[0] for choice in InfoImportanteAcceso.SECCIONES]
    
    # Verificar si ha completado todas las secciones
    secciones_completadas = len(secciones_accedidas)
    total_secciones = len(todas_las_secciones)
    completado = secciones_completadas == total_secciones
    
    # Calcular el porcentaje de progreso
    if total_secciones > 0:
        porcentaje_progreso = int((secciones_completadas / total_secciones) * 100)
    else:
        porcentaje_progreso = 0
    
    context = {
        'profile': profile,
        'secciones_accedidas': secciones_accedidas,
        'secciones_completadas': secciones_completadas,
        'total_secciones': total_secciones,
        'completado': completado,
        'todas_las_secciones': todas_las_secciones,
        'porcentaje_progreso': porcentaje_progreso,
    }
    
    return render(request, 'dtf/info_importante.html', context)


@require_http_methods(["POST"])
@dtf_required
def marcar_seccion_accedida(request):
    """Marca una sección como accedida por el usuario"""
    try:
        data = json.loads(request.body)
        seccion = data.get('seccion')
        
        if not seccion or seccion not in [choice[0] for choice in InfoImportanteAcceso.SECCIONES]:
            return JsonResponse({'error': 'Sección no válida'}, status=400)
        
        # Crear o actualizar el acceso
        acceso, created = InfoImportanteAcceso.objects.get_or_create(
            user=request.user,
            seccion=seccion,
            defaults={'accedido_en': timezone.now()}
        )
        
        # Si ya existía, actualizar la fecha
        if not created:
            acceso.accedido_en = timezone.now()
            acceso.save()
        
        # Verificar si ha completado todas las secciones
        profile, _ = DTFUserProfile.objects.get_or_create(user=request.user)
        secciones_accedidas = InfoImportanteAcceso.objects.filter(user=request.user).count()
        total_secciones = len(InfoImportanteAcceso.SECCIONES)
        
        if secciones_accedidas == total_secciones and not profile.info_importante_completada:
            profile.info_importante_completada = True
            profile.info_importante_fin = timezone.now()
            profile.save()
        
        return JsonResponse({
            'success': True,
            'secciones_completadas': secciones_accedidas,
            'total_secciones': total_secciones,
            'completado': secciones_accedidas == total_secciones
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@dtf_required
def info_importante_seccion(request, seccion):
    """Muestra el contenido de una sección específica de información importante"""
    if seccion not in [choice[0] for choice in InfoImportanteAcceso.SECCIONES]:
        messages.error(request, "Sección no encontrada")
        return redirect("dtf:info-importante")
    
    # Marcar como accedida
    acceso, created = InfoImportanteAcceso.objects.get_or_create(
        user=request.user,
        seccion=seccion,
        defaults={'accedido_en': timezone.now()}
    )
    
    if not created:
        acceso.accedido_en = timezone.now()
        acceso.save()
    
    # Verificar si ha completado todas las secciones
    profile, _ = DTFUserProfile.objects.get_or_create(user=request.user)
    secciones_accedidas = InfoImportanteAcceso.objects.filter(user=request.user).count()
    total_secciones = len(InfoImportanteAcceso.SECCIONES)
    
    if secciones_accedidas == total_secciones and not profile.info_importante_completada:
        profile.info_importante_completada = True
        profile.info_importante_fin = timezone.now()
        profile.save()
    
    # Calcular el porcentaje de progreso
    if total_secciones > 0:
        porcentaje_progreso = int((secciones_accedidas / total_secciones) * 100)
    else:
        porcentaje_progreso = 0
    
    context = {
        'seccion': seccion,
        'seccion_display': dict(InfoImportanteAcceso.SECCIONES)[seccion],
        'secciones_completadas': secciones_accedidas,
        'total_secciones': total_secciones,
        'completado': secciones_accedidas == total_secciones,
        'porcentaje_progreso': porcentaje_progreso,
    }
    
    return render(request, f'dtf/info_importante_{seccion}.html', context)
