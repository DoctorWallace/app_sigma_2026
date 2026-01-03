from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .models import Solicitud, MuestraIndividual, SolicitudModificacion, SolicitudAnulacion
from .forms import SolicitudForm, AvanceForm, EstadoForm, MuestraIndividualFormSet, SolicitudModificacionForm, AprobarModificacionForm, SolicitudAnulacionForm, TiempoEstimacionForm, SolicitudConBecarioForm
from .utils import is_tecnico, assign_sample_code, get_sample_code_display, get_solicitud_for_user_or_404
from .views import login_required_dtf, user_passes_test_dtf
from dtf.decorators import dtf_lab_gate


# --- Usuario: crear y ver sus solicitudes

@dtf_lab_gate("s_lab")
def nueva_solicitud(request):
    if request.method == "POST":
        form = SolicitudConBecarioForm(request.POST, request.FILES, solicitante=request.user)
        if form.is_valid():
            sol = form.save(commit=False)
            sol.solicitante = request.user
            sol.save()
            
            # Crear las muestras individuales
            numero_muestras = form.cleaned_data.get('numero_muestras', 1)
            for i in range(1, numero_muestras + 1):
                identificacion = request.POST.get(f'muestra_{i}_identificacion', '')
                descripcion = request.POST.get(f'muestra_{i}_descripcion', '')
                if identificacion:  # Solo crear si tiene identificaciÃ³n
                    MuestraIndividual.objects.create(
                        solicitud=sol,
                        numero_secuencia=i,
                        identificacion=identificacion,
                        descripcion=descripcion
                    )
            
            # Mensaje personalizado segÃºn si hay becario asociado
            if sol.becario_asociado:
                messages.success(
                    request, 
                    f"Solicitud creada correctamente con {numero_muestras} muestra(s) para el becario {sol.becario_asociado.nombre_completo}."
                )
            else:
                messages.success(request, f"Solicitud creada correctamente con {numero_muestras} muestra(s).")
            
            return redirect("sigmalab:mis-solicitudes")
    else:
        form = SolicitudConBecarioForm(solicitante=request.user)
    return render(request, "sigmalab/solicitudes/crear.html", {"form": form})


@dtf_lab_gate("s_lab")
def mis_solicitudes(request):
    qs = Solicitud.objects.filter(solicitante=request.user).order_by("-creado_en")
    return render(request, "sigmalab/solicitudes/mis_solicitudes.html", {"solicitudes": qs})


@dtf_lab_gate("s_lab")
def detalle_solicitud(request, pk):
    base_qs = Solicitud.objects.prefetch_related("avances__autor", "modificaciones", "anulaciones")
    sol = get_solicitud_for_user_or_404(request.user, pk, queryset=base_qs)
    avances = sol.avances.all()
    modificaciones = sol.modificaciones.all().order_by("-fecha_solicitud")
    anulaciones = sol.anulaciones.all().order_by("-fecha_anulacion")
    return render(
        request,
        "sigmalab/solicitudes/detalle.html",
        {"solicitud": sol, "avances": avances, "modificaciones": modificaciones, "anulaciones": anulaciones},
    )

@dtf_lab_gate("s_lab")
def nuevo_avance(request, pk):
    sol = get_solicitud_for_user_or_404(request.user, pk)

    if request.method == "POST":
        form = AvanceForm(request.POST, request.FILES)
        if form.is_valid():
            av = form.save(commit=False)
            av.solicitud = sol
            av.autor = request.user
            # Si no es técnico, fuerza avance visible al usuario
            if not is_tecnico(request.user):
                av.visible_para_usuario = True
            av.save()
            messages.success(request, "Avance añadido.")
            return redirect("sigmalab:detalle-solicitud", pk=sol.pk)
    else:
        form = AvanceForm()
    return render(request, "sigmalab/solicitudes/nuevo_avance.html", {"solicitud": sol, "form": form})

@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def bandeja_tecnico(request):
    estado = (request.GET.get("estado") or "").strip()
    base = Solicitud.objects.select_related("solicitante")
    if estado in dict(Solicitud.Estado.choices):
        qs = base.filter(estado=estado).order_by("-creado_en")
    else:
        qs = base.filter(
            estado__in=[
                Solicitud.Estado.PENDIENTE,
                Solicitud.Estado.ACEPTADA,
                Solicitud.Estado.EN_CURSO,
            ]
        ).order_by("estado", "-creado_en")
        estado = ""
    ctx = {"solicitudes": qs, "selected_estado": estado}
    return render(request, "sigmalab/solicitudes/bandeja_tecnico.html", ctx)


@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def todas_solicitudes(request):
    estado = (request.GET.get("estado") or "").strip()
    base = Solicitud.objects.select_related("solicitante").prefetch_related("muestras")
    if estado in dict(Solicitud.Estado.choices):
        qs = base.filter(estado=estado).order_by("-creado_en")
    else:
        qs = base.order_by("-creado_en")
        estado = ""
    return render(request, "sigmalab/solicitudes/todas.html", {"solicitudes": qs, "selected_estado": estado})


@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def cambiar_estado(request, pk):
    sol = get_object_or_404(Solicitud, pk=pk)
    if request.method == "POST":
        form = EstadoForm(request.POST)
        if form.is_valid():
            accion = form.cleaned_data["accion"]
            codigo = form.cleaned_data.get("codigo_muestra") or ""
            if accion == "aceptar":
                sol.estado = Solicitud.Estado.ACEPTADA
                sol.aceptado_en = timezone.now()
                # Asignar cÃ³digo automÃ¡ticamente si no se proporciona uno
                if codigo:
                    sol.codigo_muestra = codigo
                else:
                    # Generar cÃ³digo automÃ¡ticamente
                    sol.codigo_muestra = assign_sample_code(sol)
                messages.success(request, f"Solicitud aceptada. CÃ³digo asignado: {sol.codigo_muestra}")
            elif accion == "rechazar":
                sol.estado = Solicitud.Estado.RECHAZADA
                messages.warning(request, "Solicitud rechazada.")
            elif accion == "finalizar":
                sol.estado = Solicitud.Estado.FINALIZADA
                sol.finalizado_en = timezone.now()
                messages.success(request, "Solicitud finalizada.")
            sol.save()
            return redirect("sigmalab:detalle-solicitud", pk=sol.pk)
    else:
        form = EstadoForm()
    return render(request, "sigmalab/solicitudes/cambiar_estado.html", {"solicitud": sol, "form": form})


# --- Solicitudes de ModificaciÃ³n

@dtf_lab_gate("s_lab")
def solicitar_modificacion(request, pk):
    """Vista para que el usuario solicite modificaciones a una solicitud aceptada"""
    solicitud = get_solicitud_for_user_or_404(request.user, pk, allow_tecnico=False)

    if solicitud.estado not in ['aceptada', 'en_curso']:
        messages.error(request, "Solo se pueden solicitar modificaciones en solicitudes aceptadas o en curso.")
        return redirect("sigmalab:detalle-solicitud", pk=pk)

    if request.method == "POST":
        form = SolicitudModificacionForm(request.POST, solicitud=solicitud)
        if form.is_valid():
            modificacion = form.save(commit=False)
            modificacion.solicitante = request.user
            modificacion.save()

            messages.success(request, "Solicitud de modificación enviada correctamente. El técnico la revisará pronto.")
            return redirect("sigmalab:detalle-solicitud", pk=pk)
    else:
        form = SolicitudModificacionForm(solicitud=solicitud)

    return render(request, "sigmalab/solicitudes/solicitar_modificacion.html", {
        "solicitud": solicitud,
        "form": form
    })

@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def revisar_modificacion(request, pk):
    """Vista para que el tÃ©cnico revise y apruebe/rechace modificaciones"""
    modificacion = get_object_or_404(SolicitudModificacion, pk=pk)
    
    if request.method == "POST":
        form = AprobarModificacionForm(request.POST, instance=modificacion)
        if form.is_valid():
            modificacion = form.save(commit=False)
            modificacion.tecnico_responsable = request.user
            modificacion.fecha_resolucion = timezone.now()
            
            # Si se aprueba, aplicar los cambios
            if modificacion.estado == 'aprobada':
                if modificacion.aplicar_cambios():
                    messages.success(request, "ModificaciÃ³n aprobada y aplicada correctamente.")
                else:
                    messages.error(request, "Error al aplicar la modificaciÃ³n.")
            else:
                messages.info(request, "ModificaciÃ³n rechazada.")
            
            modificacion.save()
            return redirect("sigmalab:detalle-solicitud", pk=modificacion.solicitud_original.pk)
    else:
        form = AprobarModificacionForm(instance=modificacion)
    
    return render(request, "sigmalab/solicitudes/revisar_modificacion.html", {
        "modificacion": modificacion,
        "form": form
    })


@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def bandeja_modificaciones(request):
    """Vista para que el tÃ©cnico vea todas las modificaciones pendientes"""
    modificaciones = SolicitudModificacion.objects.filter(
        estado='pendiente'
    ).select_related('solicitud_original', 'solicitante').order_by('-fecha_solicitud')
    
    return render(request, "sigmalab/solicitudes/bandeja_modificaciones.html", {
        "modificaciones": modificaciones
    })


# --- AnulaciÃ³n de Solicitudes

@dtf_lab_gate("s_lab")
def anular_solicitud(request, pk):
    """Vista para que el usuario anule una solicitud con justificación"""
    solicitud = get_solicitud_for_user_or_404(request.user, pk, allow_tecnico=False)

    # Verificar que la solicitud se puede anular
    if solicitud.estado in ['finalizada', 'anulada']:
        messages.error(request, "Esta solicitud no se puede anular.")
        return redirect("sigmalab:detalle-solicitud", pk=pk)

    if request.method == "POST":
        form = SolicitudAnulacionForm(request.POST, solicitud=solicitud, user=request.user)
        if form.is_valid():
            anulacion = form.save()

            # Mensaje según el tipo de anulación
            if solicitud.estado == 'pendiente':
                messages.success(request, "Solicitud anulada correctamente. La solicitud ha sido retirada del sistema.")
            else:
                messages.success(request, "Solicitud anulada correctamente. El código de muestra se mantiene en el sistema de calidad.")

            return redirect("sigmalab:mis-solicitudes")
    else:
        form = SolicitudAnulacionForm(solicitud=solicitud, user=request.user)

    return render(request, "sigmalab/solicitudes/anular_solicitud.html", {
        "solicitud": solicitud,
        "form": form
    })

@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def anular_solicitud_tecnico(request, pk):
    """Vista para que el tÃ©cnico anule una solicitud"""
    solicitud = get_object_or_404(Solicitud, pk=pk)
    
    # Verificar que la solicitud se puede anular
    if solicitud.estado in ['finalizada', 'anulada']:
        messages.error(request, "Esta solicitud no se puede anular.")
        return redirect("sigmalab:detalle-solicitud", pk=pk)
    
    if request.method == "POST":
        form = SolicitudAnulacionForm(request.POST, solicitud=solicitud, user=request.user)
        if form.is_valid():
            anulacion = form.save()
            anulacion.tipo_anulacion = 'tecnico'
            anulacion.save()
            
            messages.success(request, "Solicitud anulada por el tÃ©cnico.")
            return redirect("sigmalab:detalle-solicitud", pk=pk)
    else:
        form = SolicitudAnulacionForm(solicitud=solicitud, user=request.user)
    
    return render(request, "sigmalab/solicitudes/anular_solicitud_tecnico.html", {
        "solicitud": solicitud,
        "form": form
    })


# --- EstimaciÃ³n de Tiempo

@login_required_dtf
@user_passes_test_dtf(is_tecnico)
def aceptar_con_tiempo_estimado(request, pk):
    """Vista para aceptar una solicitud con estimaciÃ³n de tiempo"""
    solicitud = get_object_or_404(Solicitud, pk=pk)
    
    if solicitud.estado != 'pendiente':
        messages.error(request, "Solo se pueden aceptar solicitudes pendientes.")
        return redirect("sigmalab:detalle-solicitud", pk=pk)
    
    if request.method == "POST":
        form = TiempoEstimacionForm(request.POST)
        if form.is_valid():
            # Guardar la estimaciÃ³n de tiempo
            solicitud.tiempo_estimado_numero = form.cleaned_data.get('tiempo_estimado_numero')
            solicitud.tiempo_estimado_unidad = form.cleaned_data.get('tiempo_estimado_unidad')
            solicitud.tiempo_estimado_indeterminado = form.cleaned_data.get('tiempo_estimado_indeterminado', False)
            
            # Cambiar estado a aceptada
            solicitud.estado = Solicitud.Estado.ACEPTADA
            solicitud.tecnico_asignado = request.user
            solicitud.aceptado_en = timezone.now()
            
            # Calcular fecha estimada de finalizaciÃ³n
            if not solicitud.tiempo_estimado_indeterminado:
                solicitud.fecha_estimada_finalizacion = solicitud.calcular_fecha_estimada_finalizacion()
            
            solicitud.save()
            
            # Asignar cÃ³digo de muestra
            assign_sample_code(solicitud)
            solicitud.save()
            
            tiempo_display = form.get_tiempo_display()
            messages.success(request, f"Solicitud aceptada. Tiempo estimado: {tiempo_display}")
            return redirect("sigmalab:detalle-solicitud", pk=pk)
    else:
        form = TiempoEstimacionForm()
    
    return render(request, "sigmalab/solicitudes/aceptar_con_tiempo.html", {
        "solicitud": solicitud,
        "form": form
    })
