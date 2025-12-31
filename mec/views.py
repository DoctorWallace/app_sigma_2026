# mec/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test as _user_passes_test
from django.shortcuts import get_object_or_404

from .models import MecSample, MecSolicitud, MecMuestraNombre, MecEvento, MecNecesidad, MecMensaje, MecIndicadorCalidad
from .forms import MecSampleForm, MecSolicitudForm, MecSolicitudDurezaForm, MecUsuarioAsociadoForm
from core.roles import is_mec_tech
from dtf.decorators import dtf_required


def login_required_dtf(view):
    return dtf_required(view)


def is_tecnico_responsable(user):
    return user.is_authenticated and (user.is_superuser or is_mec_tech(user))


@login_required_dtf
def panel_usuario(request):
    # Los técnicos no necesitan leer información importante
    if is_tecnico_responsable(request.user):
        return redirect("mec:panel_tecnico")
    
    # Verificar restricciones de acceso
    from dtf.models import DTFUserProfile
    try:
        profile = request.user.dtf_profile
        if profile.acceso_s_mec_restringido:
            messages.error(request, f"Tu acceso a S-MEC ha sido restringido. Motivo: {profile.motivo_restriccion}")
            return redirect("dtf:dashboard")
    except DTFUserProfile.DoesNotExist:
        # Si no tiene perfil DTF, crear uno
        profile = DTFUserProfile.objects.create(user=request.user)
    
    # Verificar si el usuario ha completado la información importante
    if not profile.info_importante_completada:
        messages.info(request, "Debes completar la información importante antes de acceder al panel.")
        return redirect("mec:info_importante")
    
    # Solicitudes de S-MEC
    mec_solicitudes = MecSolicitud.objects.filter(solicitante=request.user).order_by("-creado_en")
    
    # Solicitudes de S-LAB (si el usuario tiene acceso)
    sigmalab_solicitudes = []
    if hasattr(request.user, 'solicitudes'):
        sigmalab_solicitudes = request.user.solicitudes.all().order_by("-creado_en")
    
    # Estadísticas por laboratorio
    stats = {
        'mec': {
            'total': mec_solicitudes.count(),
            'pendientes': mec_solicitudes.filter(estado='pendiente').count(),
            'aceptadas': mec_solicitudes.filter(estado='aceptada').count(),
            'en_curso': mec_solicitudes.filter(estado='en_curso').count(),
            'finalizadas': mec_solicitudes.filter(estado='finalizada').count(),
            'rechazadas': mec_solicitudes.filter(estado='rechazada').count(),
        },
        'sigmalab': {
            'total': len(sigmalab_solicitudes),
            'pendientes': len([s for s in sigmalab_solicitudes if s.estado == 'pendiente']),
            'aceptadas': len([s for s in sigmalab_solicitudes if s.estado == 'aceptada']),
            'en_curso': len([s for s in sigmalab_solicitudes if s.estado == 'en_curso']),
            'finalizadas': len([s for s in sigmalab_solicitudes if s.estado == 'finalizada']),
            'rechazadas': len([s for s in sigmalab_solicitudes if s.estado == 'rechazada']),
        },
    }
    
    return render(request, "mec/panel_usuario.html", {
        "mec_solicitudes": mec_solicitudes[:10],  # Últimas 10
        "sigmalab_solicitudes": sigmalab_solicitudes[:10],
        "stats": stats
    })


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def panel_tecnico_responsable(request):
    qs = MecSolicitud.objects.all()
    pendientes = qs.filter(estado="pendiente").order_by("-creado_en")[:20]
    aceptadas = qs.filter(estado="aceptada").order_by("-creado_en")[:20]
    rechazadas = qs.filter(estado="rechazada").order_by("-creado_en")[:20]
    finalizadas = qs.filter(estado="finalizada").order_by("-creado_en")[:20]

    # KPIs por estado
    stats = {
        "total": qs.count(),
        "pendientes": qs.filter(estado="pendiente").count(),
        "aceptadas": qs.filter(estado="aceptada").count(),
        "rechazadas": qs.filter(estado="rechazada").count(),
        "finalizadas": qs.filter(estado="finalizada").count(),
    }

    # KPIs por técnica y estado
    def tech_counts(flag):
        return {
            "total": qs.filter(**{flag: True}).count(),
            "pendientes": qs.filter(estado="pendiente", **{flag: True}).count(),
            "aceptadas": qs.filter(estado="aceptada", **{flag: True}).count(),
            "rechazadas": qs.filter(estado="rechazada", **{flag: True}).count(),
            "finalizadas": qs.filter(estado="finalizada", **{flag: True}).count(),
        }

    by_tech = {
        "dureza": tech_counts("ensayo_dureza"),
        "traccion": tech_counts("ensayo_traccion"),
        "fatiga": tech_counts("ensayo_fatiga"),
        "creep_fatiga": tech_counts("ensayo_creep_fatiga"),
    }

    return render(request, "mec/panel_tecnico.html", {
        "pendientes": pendientes,
        "aceptadas": aceptadas,
        "rechazadas": rechazadas,
        "finalizadas": finalizadas,
        "stats": stats,
        "by_tech": by_tech,
    })


@login_required_dtf
def sample_create(request):
    # Los técnicos responsables no pueden crear muestras
    if is_tecnico_responsable(request.user) and not request.user.is_superuser:
        messages.error(request, "Los técnicos responsables no pueden crear muestras en S-MEC.")
        return redirect("mec:panel_tecnico")
    if request.method == "POST":
        form = MecSampleForm(request.POST)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.owner = request.user
            sample.save()
            messages.success(request, "Muestra creada correctamente.")
            return redirect("mec:panel_usuario")
    else:
        form = MecSampleForm()
    return render(request, "mec/sample_form.html", {"form": form})


@login_required_dtf
def solicitud_create(request):
    # Los técnicos responsables no pueden crear solicitudes
    if is_tecnico_responsable(request.user) and not request.user.is_superuser:
        messages.error(request, "Los técnicos responsables no pueden crear solicitudes en S-MEC.")
        return redirect("mec:panel_tecnico")
    if request.method == "POST":
        form = MecSolicitudForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.solicitante = request.user
            obj.save()
            
            # Guardar denominaciones de muestras dinámicas
            for key, value in request.POST.items():
                if key.startswith('muestra_nombre_') and value.strip():
                    MecMuestraNombre.objects.create(solicitud=obj, nombre=value.strip())
            
            messages.success(request, f"Solicitud MEC#{obj.pk} creada correctamente.")
            return redirect("mec:panel_usuario")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = MecSolicitudForm()
    return render(request, "mec/solicitud_form.html", {"form": form})


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def solicitud_detalle(request, pk):
    s = get_object_or_404(MecSolicitud, pk=pk)
    eventos = s.eventos.select_related("autor").all()
    return render(request, "mec/solicitud_detalle.html", {"s": s, "eventos": eventos})


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def evento_crear(request, pk):
    s = get_object_or_404(MecSolicitud, pk=pk)
    if request.method == "POST":
        texto = (request.POST.get("texto") or "").strip()
        if texto:
            MecEvento.objects.create(solicitud=s, autor=request.user, texto=texto)
            messages.success(request, "Entrada añadida al diario.")
        else:
            messages.error(request, "El texto del evento no puede estar vacío.")
    return redirect("mec:solicitud_detalle", pk=s.pk)


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def ficha_equipo(request):
    return render(request, "mec/ficha_equipo.html", {})


@login_required_dtf
def necesidades(request):
    if request.method == "POST":
        titulo = (request.POST.get("titulo") or "").strip()
        descripcion = (request.POST.get("descripcion") or "").strip()
        fecha = (request.POST.get("fecha") or "").strip()
        if titulo and fecha:
            from datetime import datetime
            try:
                f = datetime.strptime(fecha, "%Y-%m-%d").date()
                MecNecesidad.objects.create(titulo=titulo, descripcion=descripcion, fecha=f, creado_por=request.user)
                messages.success(request, "Necesidad registrada.")
            except Exception:
                messages.error(request, "Fecha inválida (use aaaa-mm-dd).")
        else:
            messages.error(request, "Título y fecha son obligatorios.")
    items = MecNecesidad.objects.all()
    return render(request, "mec/necesidades.html", {"items": items})


@login_required_dtf
def inbox(request):
    if request.method == "POST":
        asunto = (request.POST.get("asunto") or "").strip()
        mensaje = (request.POST.get("mensaje") or "").strip()
        if asunto and mensaje:
            MecMensaje.objects.create(autor=request.user, asunto=asunto, mensaje=mensaje)
            messages.success(request, "Mensaje enviado a los técnicos responsables.")
        else:
            messages.error(request, "Asunto y mensaje son obligatorios.")
    mensajes = MecMensaje.objects.all().select_related("autor")
    return render(request, "mec/inbox.html", {"mensajes": mensajes})


@login_required_dtf
def solicitud_dureza_create(request):
    """Vista para crear solicitudes de ensayos de dureza"""
    if request.method == "POST":
        form = MecSolicitudDurezaForm(request.POST)
        if form.is_valid():
            # Crear la solicitud
            solicitud = MecSolicitud.objects.create(
                solicitante=request.user,
                material=form.cleaned_data['material'],
                numero_muestras=form.cleaned_data['numero_muestras'],
                ensayo_dureza=form.cleaned_data['ensayo_dureza'],
                dureza_carga=str(form.cleaned_data.get('carga_ensayo', '')),
                dureza_huellas_filas=1,  # Valor por defecto
                dureza_huellas_columnas=form.cleaned_data.get('numero_indentaciones'),
                observaciones=form.cleaned_data.get('observaciones', ''),
                estado='pendiente'
            )
            
            # Procesar muestras individuales si hay más de 1
            numero_muestras = form.cleaned_data['numero_muestras']
            if numero_muestras > 1:
                for i in range(1, numero_muestras + 1):
                    nombre_key = f'muestra_{i}_nombre'
                    descripcion_key = f'muestra_{i}_descripcion'
                    
                    if nombre_key in request.POST:
                        nombre = request.POST.get(nombre_key, '').strip()
                        descripcion = request.POST.get(descripcion_key, '').strip()
                        
                        if nombre:  # Solo crear si hay nombre
                            MecMuestraNombre.objects.create(
                                solicitud=solicitud,
                                nombre=nombre
                            )
            
            messages.success(request, "Solicitud de ensayo de dureza enviada correctamente.")
            return redirect("mec:panel_usuario")
    else:
        form = MecSolicitudDurezaForm()
    
    return render(request, "mec/solicitud_dureza_form.html", {"form": form})


@login_required_dtf
def info_importante(request):
    """Vista para mostrar información importante de S-MEC"""
    return render(request, "mec/info_importante.html")


@login_required_dtf
@_user_passes_test(is_tecnico_responsable)
def crear_usuario(request):
    """Vista para que los técnicos creen un nuevo usuario externo"""
    if request.method == 'POST':
        form = MecUsuarioAsociadoForm(
            request.POST,
            creado_por=request.user,
            es_tecnico=True
        )
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request, 
                f'Usuario externo {usuario.nombre_completo} creado exitosamente y asociado a {usuario.investigador_principal.get_full_name()}.'
            )
            return redirect('mec:panel_usuario')
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = MecUsuarioAsociadoForm(
            creado_por=request.user,
            es_tecnico=True
        )
    
    return render(request, 'mec/crear_usuario.html', {'form': form})


@login_required_dtf
def indicadores_calidad(request):
    """Vista para mostrar indicadores de calidad I1 e I2 en Sigma MEC"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('mec:panel_usuario')
    
    # Obtener todas las solicitudes del técnico
    solicitudes = MecSolicitud.objects.filter(tecnico_responsable=request.user).order_by('-creado_en')
    
    # Obtener indicadores para cada solicitud
    indicadores_data = []
    for solicitud in solicitudes:
        indicador, created = MecIndicadorCalidad.objects.get_or_create(
            solicitud=solicitud,
            defaults={'fecha_recepcion': solicitud.creado_en}
        )
        
        # Si se creó un nuevo indicador, actualizar las fechas
        if created:
            indicador.fecha_recepcion = solicitud.creado_en
            if solicitud.estado == MecSolicitud.Estado.FINALIZADA:
                indicador.fecha_finalizacion_analisis = solicitud.actualizado_en
            indicador.actualizar_indicadores()
        
        indicadores_data.append({
            'solicitud': solicitud,
            'indicador': indicador,
            'i1_dias': indicador.i1_tiempo_analisis_dias,
            'i2_dias': indicador.i2_tiempo_entrega_dias,
            'i1_cumple': indicador.i1_tiempo_analisis_dias is not None and indicador.i1_tiempo_analisis_dias < 5,
            'i2_cumple': indicador.i2_tiempo_entrega_dias is not None and indicador.i2_tiempo_entrega_dias < 5,
        })
    
    # Calcular promedios
    promedio_i1 = MecIndicadorCalidad.obtener_promedio_i1()
    promedio_i2 = MecIndicadorCalidad.obtener_promedio_i2()
    
    # Estadísticas generales
    total_solicitudes = len(indicadores_data)
    solicitudes_con_i1 = len([d for d in indicadores_data if d['i1_dias'] is not None])
    solicitudes_con_i2 = len([d for d in indicadores_data if d['i2_dias'] is not None])
    solicitudes_cumplen_i1 = len([d for d in indicadores_data if d['i1_cumple']])
    solicitudes_cumplen_i2 = len([d for d in indicadores_data if d['i2_cumple']])
    
    context = {
        'indicadores_data': indicadores_data,
        'promedio_i1': promedio_i1,
        'promedio_i2': promedio_i2,
        'total_solicitudes': total_solicitudes,
        'solicitudes_con_i1': solicitudes_con_i1,
        'solicitudes_con_i2': solicitudes_con_i2,
        'solicitudes_cumplen_i1': solicitudes_cumplen_i1,
        'solicitudes_cumplen_i2': solicitudes_cumplen_i2,
        'porcentaje_cumplimiento_i1': (solicitudes_cumplen_i1 / solicitudes_con_i1 * 100) if solicitudes_con_i1 > 0 else 0,
        'porcentaje_cumplimiento_i2': (solicitudes_cumplen_i2 / solicitudes_con_i2 * 100) if solicitudes_con_i2 > 0 else 0,
    }
    
    return render(request, 'mec/indicadores_calidad.html', context)


@login_required_dtf
def actualizar_indicador_mec(request, solicitud_id):
    """Vista para actualizar fechas de un indicador específico en Sigma MEC"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('mec:panel_usuario')
    
    solicitud = get_object_or_404(MecSolicitud, id=solicitud_id, tecnico_responsable=request.user)
    
    if request.method == 'POST':
        indicador, created = MecIndicadorCalidad.objects.get_or_create(
            solicitud=solicitud,
            defaults={'fecha_recepcion': solicitud.creado_en}
        )
        
        # Actualizar fechas según el formulario
        fecha_finalizacion = request.POST.get('fecha_finalizacion_analisis')
        fecha_entrega = request.POST.get('fecha_entrega_informe')
        
        if fecha_finalizacion:
            from datetime import datetime
            try:
                indicador.fecha_finalizacion_analisis = datetime.fromisoformat(fecha_finalizacion)
            except ValueError:
                messages.error(request, 'Formato de fecha de finalización inválido.')
                return redirect('mec:indicadores_calidad')
        
        if fecha_entrega:
            from datetime import datetime
            try:
                indicador.fecha_entrega_informe = datetime.fromisoformat(fecha_entrega)
            except ValueError:
                messages.error(request, 'Formato de fecha de entrega inválido.')
                return redirect('mec:indicadores_calidad')
        
        # Actualizar indicadores calculados
        indicador.actualizar_indicadores()
        
        messages.success(request, f'Indicadores actualizados para la solicitud {solicitud.material}.')
        return redirect('mec:indicadores_calidad')
    
    return redirect('mec:indicadores_calidad')
