from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    ConfocalSolicitud, ConfocalMuestraIndividual, ConfocalAvance, 
    ConfocalDiarioEntrada
)
from .forms import (
    ConfocalSolicitudForm, ConfocalMuestraIndividualForm, ConfocalAvanceForm,
    ConfocalDiarioEntradaForm, ConfocalSolicitudModificacionForm,
    ConfocalSolicitudAnulacionForm, ConfocalIncidenciaForm, ConfocalMensajeInternoForm
)
from sigmalab.models import UsuarioAsociado
from icts.decorators import login_required_icts

from icts.auth_utils import (
    CONF_TECH_GROUPS,
    ICTS_CORE_GROUPS,
    get_normalized_user_groups,
    normalize_group_name,
    user_in_groups,
)


CONF_USER_GROUPS = {normalize_group_name(name) for name in ("usuarios_dtf", "dtf users", "dtf_users")}


def is_confocal_technician(user):
    """Verifica si el usuario es técnico de confocal"""
    groups = get_normalized_user_groups(user)
    return user_in_groups(user, CONF_TECH_GROUPS, groups)


def is_confocal_user(user):
    """Verifica si el usuario puede acceder al laboratorio confocal"""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    groups = get_normalized_user_groups(user)
    if user_in_groups(user, CONF_TECH_GROUPS, groups):
        return True
    if groups & ICTS_CORE_GROUPS:
        return True
    if groups & CONF_USER_GROUPS:
        return True
    return False


@login_required_icts
def confocal_home(request):
    """Página principal del laboratorio confocal"""
    if not is_confocal_user(request.user):
        messages.error(request, "No tienes permisos para acceder al laboratorio confocal.")
        return redirect("portal:home")
    
    # Estadísticas básicas
    total_solicitudes = ConfocalSolicitud.objects.count()
    solicitudes_pendientes = ConfocalSolicitud.objects.filter(estado='pendiente').count()
    solicitudes_en_curso = ConfocalSolicitud.objects.filter(estado='en_curso').count()
    solicitudes_finalizadas = ConfocalSolicitud.objects.filter(estado='finalizada').count()
    
    # Solicitudes recientes
    solicitudes_recientes = ConfocalSolicitud.objects.order_by('-creado_en')[:5]
    
    # Si es técnico, mostrar sus solicitudes asignadas
    solicitudes_asignadas = []
    if is_confocal_technician(request.user):
        solicitudes_asignadas = ConfocalSolicitud.objects.filter(
            tecnico_asignado=request.user,
            estado__in=['aceptada', 'en_curso']
        ).order_by('-creado_en')[:5]
    
    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_en_curso': solicitudes_en_curso,
        'solicitudes_finalizadas': solicitudes_finalizadas,
        'solicitudes_recientes': solicitudes_recientes,
        'solicitudes_asignadas': solicitudes_asignadas,
        'is_technician': is_confocal_technician(request.user),
    }
    
    return render(request, 'sigmaconf/home.html', context)


@login_required_icts
def confocal_dashboard(request):
    """Dashboard para técnicos de confocal"""
    if not is_confocal_technician(request.user):
        messages.error(request, "No tienes permisos para acceder al dashboard de técnicos.")
        return redirect("sigmaconf:home")
    
    # Solicitudes asignadas al técnico
    solicitudes_asignadas = ConfocalSolicitud.objects.filter(
        tecnico_asignado=request.user
    ).order_by('-creado_en')
    
    # Estadísticas del técnico
    total_asignadas = solicitudes_asignadas.count()
    pendientes = solicitudes_asignadas.filter(estado='pendiente').count()
    en_curso = solicitudes_asignadas.filter(estado='en_curso').count()
    finalizadas = solicitudes_asignadas.filter(estado='finalizada').count()
    
    # Solicitudes pendientes sin asignar
    solicitudes_sin_asignar = ConfocalSolicitud.objects.filter(
        estado='pendiente',
        tecnico_asignado__isnull=True
    ).order_by('-creado_en')
    
    context = {
        'solicitudes_asignadas': solicitudes_asignadas,
        'solicitudes_sin_asignar': solicitudes_sin_asignar,
        'total_asignadas': total_asignadas,
        'pendientes': pendientes,
        'en_curso': en_curso,
        'finalizadas': finalizadas,
    }
    
    return render(request, 'sigmaconf/dashboard.html', context)


@login_required_icts
def confocal_estadisticas(request):
    """Estadísticas del laboratorio confocal"""
    if not is_confocal_technician(request.user):
        messages.error(request, "No tienes permisos para ver las estadísticas.")
        return redirect("sigmaconf:home")
    
    # Estadísticas generales
    total_solicitudes = ConfocalSolicitud.objects.count()
    solicitudes_por_estado = {}
    for estado, _ in ConfocalSolicitud.Estado.choices:
        solicitudes_por_estado[estado] = ConfocalSolicitud.objects.filter(estado=estado).count()
    
    # Solicitudes por tipo de microscopía
    solicitudes_por_tipo = {}
    tipos = ['confocal_laser', 'confocal_spinning', 'super_resolucion', 'multifoton', 'otra']
    for tipo in tipos:
        solicitudes_por_tipo[tipo] = ConfocalSolicitud.objects.filter(tipo_microscopia=tipo).count()
    
    # Solicitudes por mes (últimos 12 meses)
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    
    solicitudes_por_mes = ConfocalSolicitud.objects.annotate(
        mes=TruncMonth('creado_en')
    ).values('mes').annotate(
        total=Count('id')
    ).order_by('mes')[:12]
    
    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_por_estado': solicitudes_por_estado,
        'solicitudes_por_tipo': solicitudes_por_tipo,
        'solicitudes_por_mes': solicitudes_por_mes,
    }
    
    return render(request, 'sigmaconf/estadisticas.html', context)

