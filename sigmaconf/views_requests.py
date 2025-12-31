from django.shortcuts import render, redirect, get_object_or_404
from icts.decorators import login_required_icts
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from .models import ConfocalSolicitud, ConfocalMuestraIndividual, ConfocalAvance, ConfocalDiarioEntrada
from .forms import (
    ConfocalSolicitudForm, ConfocalAvanceForm, ConfocalDiarioEntradaForm
)
from .views import is_confocal_technician, is_confocal_user


@login_required_icts
def confocal_solicitud_create(request):
    """Crear nueva solicitud de confocal"""
    if not is_confocal_user(request.user):
        messages.error(request, "No tienes permisos para crear solicitudes.")
        return redirect("sigmaconf:home")
    
    if request.method == 'POST':
        form = ConfocalSolicitudForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.solicitante = request.user
            solicitud.save()
            
            # Crear muestras individuales si se especificÃ³ nÃºmero de muestras > 1
            if solicitud.numero_muestras > 1:
                for i in range(1, solicitud.numero_muestras + 1):
                    ConfocalMuestraIndividual.objects.create(
                        solicitud=solicitud,
                        numero_secuencia=i,
                        identificacion=f"Muestra {i}",
                        descripcion=""
                    )
            
            messages.success(request, f"Solicitud CONF#{solicitud.pk} creada exitosamente.")
            return redirect("sigmaconf:solicitud_detail", pk=solicitud.pk)
    else:
        form = ConfocalSolicitudForm(user=request.user)
    
    return render(request, 'sigmaconf/solicitud_form.html', {'form': form})


@login_required_icts
def confocal_solicitud_detail(request, pk):
    """Detalle de solicitud confocal"""
    if not is_confocal_user(request.user):
        messages.error(request, "No tienes permisos para ver esta solicitud.")
        return redirect("sigmaconf:home")

    if is_confocal_technician(request.user) or request.user.is_staff:
        solicitud = get_object_or_404(ConfocalSolicitud, pk=pk)
    else:
        solicitud = get_object_or_404(ConfocalSolicitud, pk=pk, solicitante=request.user)

    # Obtener muestras individuales
    muestras = solicitud.muestras.all()

    # Obtener avances
    avances = solicitud.avances.filter(visible_para_usuario=True).order_by('-creado_en')

    # Obtener entradas del diario (solo para técnicos)
    diario_entradas = []
    if is_confocal_technician(request.user):
        diario_entradas = solicitud.diario.all()

    context = {
        'solicitud': solicitud,
        'muestras': muestras,
        'avances': avances,
        'diario_entradas': diario_entradas,
        'is_technician': is_confocal_technician(request.user),
        'can_edit': solicitud.solicitante == request.user and solicitud.estado == 'pendiente',
        'can_manage': is_confocal_technician(request.user) or request.user.is_staff,
    }

    return render(request, 'sigmaconf/solicitud_detail.html', context)

@login_required_icts
def confocal_solicitud_list(request):
    """Lista de solicitudes confocal"""
    if not is_confocal_user(request.user):
        messages.error(request, "No tienes permisos para ver las solicitudes.")
        return redirect("sigmaconf:home")
    
    # Filtrar solicitudes segÃºn el usuario
    if is_confocal_technician(request.user) or request.user.is_staff:
        # TÃ©cnicos y staff ven todas las solicitudes
        solicitudes = ConfocalSolicitud.objects.all()
    else:
        # Usuarios normales solo ven sus propias solicitudes
        solicitudes = ConfocalSolicitud.objects.filter(solicitante=request.user)
    
    # Filtros
    estado_filter = request.GET.get('estado')
    if estado_filter:
        solicitudes = solicitudes.filter(estado=estado_filter)
    
    tipo_filter = request.GET.get('tipo_microscopia')
    if tipo_filter:
        solicitudes = solicitudes.filter(tipo_microscopia=tipo_filter)
    
    # BÃºsqueda
    search = request.GET.get('search')
    if search:
        solicitudes = solicitudes.filter(
            Q(material__icontains=search) |
            Q(procedencia__icontains=search) |
            Q(solicitante__first_name__icontains=search) |
            Q(solicitante__last_name__icontains=search)
        )
    
    # PaginaciÃ³n
    paginator = Paginator(solicitudes.order_by('-creado_en'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estado_filter': estado_filter,
        'tipo_filter': tipo_filter,
        'search': search,
        'is_technician': is_confocal_technician(request.user),
    }
    
    return render(request, 'sigmaconf/solicitud_list.html', context)


@login_required_icts
@require_POST
def confocal_solicitud_accept(request, pk):
    """Aceptar solicitud confocal"""
    if not is_confocal_technician(request.user):
        messages.error(request, "No tienes permisos para aceptar solicitudes.")
        return redirect("sigmaconf:home")
    
    solicitud = get_object_or_404(ConfocalSolicitud, pk=pk)
    
    if solicitud.estado != 'pendiente':
        messages.error(request, "Solo se pueden aceptar solicitudes pendientes.")
        return redirect("sigmaconf:solicitud_detail", pk=pk)
    
    solicitud.estado = 'aceptada'
    solicitud.tecnico_asignado = request.user
    solicitud.aceptado_en = timezone.now()
    solicitud.save()
    
    messages.success(request, f"Solicitud CONF#{solicitud.pk} aceptada exitosamente.")
    return redirect("sigmaconf:solicitud_detail", pk=pk)


@login_required_icts
@require_POST
def confocal_solicitud_reject(request, pk):
    """Rechazar solicitud confocal"""
    if not is_confocal_technician(request.user):
        messages.error(request, "No tienes permisos para rechazar solicitudes.")
        return redirect("sigmaconf:home")
    
    solicitud = get_object_or_404(ConfocalSolicitud, pk=pk)
    
    if solicitud.estado != 'pendiente':
        messages.error(request, "Solo se pueden rechazar solicitudes pendientes.")
        return redirect("sigmaconf:solicitud_detail", pk=pk)
    
    justificacion = request.POST.get('justificacion', '')
    if not justificacion:
        messages.error(request, "Debe proporcionar una justificaciÃ³n para el rechazo.")
        return redirect("sigmaconf:solicitud_detail", pk=pk)
    
    solicitud.estado = 'rechazada'
    solicitud.tecnico_asignado = request.user
    solicitud.observaciones += f"\n\nRECHAZADO: {justificacion}"
    solicitud.save()
    
    messages.success(request, f"Solicitud CONF#{solicitud.pk} rechazada.")
    return redirect("sigmaconf:solicitud_detail", pk=pk)


@login_required_icts
@require_POST
def confocal_solicitud_start(request, pk):
    """Iniciar trabajo en solicitud confocal"""
    if not is_confocal_technician(request.user):
        messages.error(request, "No tienes permisos para iniciar trabajos.")
        return redirect("sigmaconf:home")
    
    solicitud = get_object_or_404(ConfocalSolicitud, pk=pk)
    
    if solicitud.estado != 'aceptada':
        messages.error(request, "Solo se pueden iniciar solicitudes aceptadas.")
        return redirect("sigmaconf:solicitud_detail", pk=pk)
    
    solicitud.estado = 'en_curso'
    solicitud.fecha_inicio_trabajo = timezone.now()
    solicitud.save()
    
    messages.success(request, f"Trabajo iniciado en solicitud CONF#{solicitud.pk}.")
    return redirect("sigmaconf:solicitud_detail", pk=pk)


@login_required_icts
@require_POST
def confocal_solicitud_finish(request, pk):
    """Finalizar solicitud confocal"""
    if not is_confocal_technician(request.user):
        messages.error(request, "No tienes permisos para finalizar solicitudes.")
        return redirect("sigmaconf:home")
    
    solicitud = get_object_or_404(ConfocalSolicitud, pk=pk)
    
    if solicitud.estado != 'en_curso':
        messages.error(request, "Solo se pueden finalizar solicitudes en curso.")
        return redirect("sigmaconf:solicitud_detail", pk=pk)
    
    solicitud.estado = 'finalizada'
    solicitud.finalizado_en = timezone.now()
    solicitud.save()
    
    messages.success(request, f"Solicitud CONF#{solicitud.pk} finalizada exitosamente.")
    return redirect("sigmaconf:solicitud_detail", pk=pk)


