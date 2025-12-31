from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator

from .models import IncidenciaLaboratorio, RespuestaIncidencia
from .forms import IncidenciaForm, RespuestaIncidenciaForm, GestionarIncidenciaForm
from .utils import is_tecnico
from .views import login_required_dtf, user_passes_test_dtf


# ========= Vistas para Usuarios =========

@login_required_dtf
def reportar_incidencia(request):
    """Vista para que los usuarios reporten incidencias del laboratorio"""
    if request.method == "POST":
        form = IncidenciaForm(request.POST, request.FILES)
        if form.is_valid():
            incidencia = form.save(commit=False)
            incidencia.reportado_por = request.user
            incidencia.save()
            
            messages.success(
                request, 
                f"Incidencia reportada correctamente. Número de incidencia: INC#{incidencia.pk}"
            )
            return redirect("sigmalab:mis-incidencias")
    else:
        form = IncidenciaForm()
    
    return render(request, "sigmalab/incidencias/reportar_incidencia.html", {
        "form": form
    })


@login_required_dtf
def mis_incidencias(request):
    """Vista para que los usuarios vean sus incidencias reportadas"""
    incidencias = IncidenciaLaboratorio.objects.filter(
        reportado_por=request.user
    ).order_by("-fecha_reporte")
    
    # Filtros
    estado = request.GET.get('estado', '')
    categoria = request.GET.get('categoria', '')
    
    if estado:
        incidencias = incidencias.filter(estado=estado)
    if categoria:
        incidencias = incidencias.filter(categoria=categoria)
    
    # Paginación
    paginator = Paginator(incidencias, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "sigmalab/incidencias/mis_incidencias.html", {
        "page_obj": page_obj,
        "selected_estado": estado,
        "selected_categoria": categoria,
    })


@login_required_dtf
def detalle_incidencia(request, pk):
    """Vista para ver el detalle de una incidencia"""
    incidencia = get_object_or_404(
        IncidenciaLaboratorio.objects.prefetch_related('respuestas__autor'),
        pk=pk
    )
    
    # Verificar que el usuario puede ver esta incidencia
    if (incidencia.reportado_por != request.user and 
        not is_tecnico(request.user) and 
        not request.user.is_staff):
        messages.error(request, "No tienes permisos para ver esta incidencia.")
        return redirect("sigmalab:mis-incidencias")
    
    respuestas = incidencia.respuestas.all().order_by('fecha_creacion')
    
    return render(request, "sigmalab/incidencias/detalle_incidencia.html", {
        "incidencia": incidencia,
        "respuestas": respuestas,
    })


# ========= Vistas para Técnicos =========

@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def inbox_incidencias(request):
    """Vista para que los técnicos vean el inbox de incidencias"""
    # Filtros
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    categoria = request.GET.get('categoria', '')
    asignado = request.GET.get('asignado', '')
    
    # Base queryset
    incidencias = IncidenciaLaboratorio.objects.select_related(
        'reportado_por', 'asignado_a'
    ).order_by("-fecha_reporte")
    
    # Aplicar filtros
    if estado:
        incidencias = incidencias.filter(estado=estado)
    if prioridad:
        incidencias = incidencias.filter(prioridad=prioridad)
    if categoria:
        incidencias = incidencias.filter(categoria=categoria)
    if asignado == 'me':
        incidencias = incidencias.filter(asignado_a=request.user)
    elif asignado == 'unassigned':
        incidencias = incidencias.filter(asignado_a__isnull=True)
    
    # Paginación
    paginator = Paginator(incidencias, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    stats = {
        'total': IncidenciaLaboratorio.objects.count(),
        'pendientes': IncidenciaLaboratorio.objects.filter(estado='pendiente').count(),
        'en_proceso': IncidenciaLaboratorio.objects.filter(estado='en_proceso').count(),
        'resueltas': IncidenciaLaboratorio.objects.filter(estado='resuelta').count(),
        'criticas': IncidenciaLaboratorio.objects.filter(prioridad='critica').count(),
    }
    
    return render(request, "sigmalab/incidencias/inbox_incidencias.html", {
        "page_obj": page_obj,
        "stats": stats,
        "filters": {
            "estado": estado,
            "prioridad": prioridad,
            "categoria": categoria,
            "asignado": asignado,
        }
    })


@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def gestionar_incidencia(request, pk):
    """Vista para que los técnicos gestionen una incidencia"""
    incidencia = get_object_or_404(IncidenciaLaboratorio, pk=pk)
    
    if request.method == "POST":
        form = GestionarIncidenciaForm(request.POST, instance=incidencia)
        if form.is_valid():
            incidencia = form.save(commit=False)
            
            # Actualizar fechas según el estado
            if incidencia.estado == 'en_proceso' and not incidencia.fecha_asignacion:
                incidencia.fecha_asignacion = timezone.now()
            elif incidencia.estado == 'resuelta' and not incidencia.fecha_resolucion:
                incidencia.fecha_resolucion = timezone.now()
            elif incidencia.estado == 'cerrada' and not incidencia.fecha_cierre:
                incidencia.fecha_cierre = timezone.now()
            
            incidencia.save()
            
            messages.success(request, "Incidencia actualizada correctamente.")
            return redirect("sigmalab:detalle-incidencia", pk=pk)
    else:
        form = GestionarIncidenciaForm(instance=incidencia)
    
    return render(request, "sigmalab/incidencias/gestionar_incidencia.html", {
        "incidencia": incidencia,
        "form": form
    })


@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def responder_incidencia(request, pk):
    """Vista para que los técnicos respondan a una incidencia"""
    incidencia = get_object_or_404(IncidenciaLaboratorio, pk=pk)
    
    if request.method == "POST":
        form = RespuestaIncidenciaForm(request.POST, request.FILES)
        if form.is_valid():
            respuesta = form.save(commit=False)
            respuesta.incidencia = incidencia
            respuesta.autor = request.user
            
            # Si marca como resolución, actualizar estado de la incidencia
            if respuesta.es_resolucion:
                incidencia.estado = 'resuelta'
                incidencia.fecha_resolucion = timezone.now()
                incidencia.save()
            
            respuesta.save()
            
            messages.success(request, "Respuesta enviada correctamente.")
            return redirect("sigmalab:detalle-incidencia", pk=pk)
    else:
        form = RespuestaIncidenciaForm()
    
    return render(request, "sigmalab/incidencias/responder_incidencia.html", {
        "incidencia": incidencia,
        "form": form
    })


# ========= Vistas de Estadísticas =========

@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def estadisticas_incidencias(request):
    """Vista para mostrar estadísticas de incidencias"""
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    
    # Estadísticas generales
    total_incidencias = IncidenciaLaboratorio.objects.count()
    incidencias_resueltas = IncidenciaLaboratorio.objects.filter(estado='resuelta').count()
    incidencias_pendientes = IncidenciaLaboratorio.objects.filter(estado='pendiente').count()
    
    # Tiempo promedio de resolución
    incidencias_con_resolucion = IncidenciaLaboratorio.objects.filter(
        fecha_resolucion__isnull=False
    )
    
    tiempo_promedio = None
    if incidencias_con_resolucion.exists():
        tiempos = []
        for inc in incidencias_con_resolucion:
            if inc.tiempo_resolucion():
                tiempos.append(inc.tiempo_resolucion().total_seconds() / 3600)  # en horas
        if tiempos:
            tiempo_promedio = sum(tiempos) / len(tiempos)
    
    # Incidencias por categoría
    por_categoria = IncidenciaLaboratorio.objects.values('categoria').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Incidencias por prioridad
    por_prioridad = IncidenciaLaboratorio.objects.values('prioridad').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Incidencias recientes (últimos 30 días)
    fecha_limite = timezone.now() - timedelta(days=30)
    incidencias_recientes = IncidenciaLaboratorio.objects.filter(
        fecha_reporte__gte=fecha_limite
    ).count()
    
    return render(request, "sigmalab/incidencias/estadisticas_incidencias.html", {
        "total_incidencias": total_incidencias,
        "incidencias_resueltas": incidencias_resueltas,
        "incidencias_pendientes": incidencias_pendientes,
        "tiempo_promedio": tiempo_promedio,
        "por_categoria": por_categoria,
        "por_prioridad": por_prioridad,
        "incidencias_recientes": incidencias_recientes,
    })
