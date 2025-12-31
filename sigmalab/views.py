"""Vistas DTF/S-LAB (SIGMALAB).

Unifica autenticación DTF y rol de técnico según nuevos grupos canónicos:
- usuarios_dtf
- tecnico_responsable_s_lab, tecnico_responsable_s_mec, tecnico_responsable_s_dp
- usuarios_autonomo_s_lab
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.utils import timezone
from core.roles import is_slab_tech
from dtf.decorators import dtf_required

from .models import Sample, Solicitud, UsuarioAsociado, LabIndicadorCalidad, EquipoLaboratorio, PrestamoEquipo, NotificacionPrestamo
from .forms import SampleForm, DiarioEntradaForm, UsuarioAsociadoForm, SolicitudConBecarioForm, EquipoLaboratorioForm, PrestamoEquipoForm, DevolucionEquipoForm, BuscarEquipoForm, FiltroPrestamosForm
from django.contrib.auth.decorators import (
    user_passes_test as _user_passes_test,
)


def login_required_dtf(view):
    """Compatibilidad: usar el decorador DTF unificado."""
    return dtf_required(view)


def user_passes_test_dtf(test_func):
    def decorator(view):
        view = dtf_required(view)
        return _user_passes_test(test_func, login_url="/accounts/login/dtf/")(view)
    return decorator


# --- helpers de rol ---
def is_technician_sl(user):
    """Técnico responsable S-LAB (grupo canónico)."""
    return user.is_authenticated and (user.is_superuser or is_slab_tech(user))


def is_tecnico_responsable(user):
    """Alias legacy para compatibilidad con vistas antiguas."""
    return is_technician_sl(user)


def is_technician(user):
    return is_technician_sl(user)


@login_required_dtf
def dashboard(request):
    """Dashboard principal que redirige según el rol del usuario"""
    if is_technician_sl(request.user):
        return redirect("sigmalab:panel-tecnico")
    else:
        return redirect("sigmalab:panel-usuario")


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def panel_tecnico(request):
    # Obtener estadísticas de solicitudes
    contadores = {
        "pendientes": Solicitud.objects.filter(estado=Solicitud.Estado.PENDIENTE).count(),
        "en_curso": Solicitud.objects.filter(estado=Solicitud.Estado.EN_CURSO).count(),
        "aceptadas": Solicitud.objects.filter(estado=Solicitud.Estado.ACEPTADA).count(),
        "rechazadas": Solicitud.objects.filter(estado=Solicitud.Estado.RECHAZADA).count(),
    }
    
    # Obtener solicitudes recientes (últimas 5)
    recientes = (
        Solicitud.objects.select_related("solicitante", "becario_asociado")
        .order_by("-creado_en")[:5]
    )
    
    # Obtener estadísticas de incidencias
    from .models import IncidenciaLaboratorio
    incidencias_stats = IncidenciaLaboratorio.objects.aggregate(
        abiertas=Count('id', filter=Q(estado='abierta')),
        en_proceso=Count('id', filter=Q(estado='en_proceso')),
        resueltas=Count('id', filter=Q(estado='resuelta')),
    )
    
    return render(
        request,
        "sigmalab/panel_tecnico.html",
        {
            "contadores": contadores,
            "recientes": recientes,
            "incidencias_abiertas": incidencias_stats['abiertas'],
            "incidencias_en_proceso": incidencias_stats['en_proceso'],
            "incidencias_resueltas": incidencias_stats['resueltas'],
        },
    )


@login_required_dtf
def panel_usuario(request):
    # Los técnicos de S-LAB no necesitan leer información importante
    if is_technician_sl(request.user):
        return redirect("sigmalab:panel-tecnico")
    
    # Verificar restricciones de acceso
    from dtf.models import DTFUserProfile
    try:
        profile = request.user.dtf_profile
        if profile.acceso_s_lab_restringido:
            messages.error(request, f"Tu acceso a S-LAB ha sido restringido. Motivo: {profile.motivo_restriccion}")
            return redirect("dtf:dashboard")
    except DTFUserProfile.DoesNotExist:
        # Si no tiene perfil DTF, crear uno
        profile = DTFUserProfile.objects.create(user=request.user)
    
    # Verificar si el usuario ha completado la información importante
    if not profile.info_importante_completada:
        messages.info(request, "Debes completar la información importante antes de acceder al panel.")
        return redirect("dtf:info-importante")
    
    mias = (
        Solicitud.objects.filter(solicitante=request.user)
        .select_related("solicitante", "becario_asociado")
        .order_by("-creado_en")[:10]
    )

    estados = (
        Solicitud.objects.filter(solicitante=request.user).values("estado").annotate(n=Count("id"))
    )
    recuento = {"pendiente": 0, "aceptada": 0, "rechazada": 0, "en_curso": 0, "finalizada": 0}
    for e in estados:
        recuento[e["estado"]] = e["n"]
    
    # Obtener solicitudes autónomas aceptadas
    solicitudes_autonomas_aceptadas = Solicitud.objects.filter(
        solicitante=request.user,
        estado='aceptada',
        autonomo=True
    ).select_related('becario_asociado').order_by('-creado_en')

    return render(
        request,
        "sigmalab/panel_usuario.html",
        {
            "mias": mias,
            "recuento": recuento,
            "solicitudes_autonomas_aceptadas": solicitudes_autonomas_aceptadas,
        },
    )


@login_required_dtf
def ficha_equipo(request):
    return render(request, "sigmalab/ficha_equipo.html", {})


@login_required_dtf
def diario_solicitud(request, pk):
    if is_technician(request.user):
        sol = get_object_or_404(Solicitud, pk=pk)
    else:
        sol = get_object_or_404(
            Solicitud,
            pk=pk,
            solicitante=request.user,
            autonomo=True,
        )

    if request.method == "POST":
        form = DiarioEntradaForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.solicitud = sol
            entry.autor = request.user
            entry.save()
            messages.success(request, "Entrada registrada en el diario.")
            return redirect("sigmalab:diario-solicitud", pk=pk)
    else:
        form = DiarioEntradaForm()

    entradas = sol.diario.select_related("autor").all()
    return render(request, "sigmalab/diario.html", {"solicitud": sol, "form": form, "entradas": entradas})

@login_required_dtf
@user_passes_test_dtf(is_technician)
def toggle_autonomia(request, pk):
    sol = Solicitud.objects.filter(pk=pk).first()
    if not sol:
        return redirect("sigmalab:todas-solicitudes")
    sol.autonomo = not sol.autonomo
    sol.save(update_fields=["autonomo"])
    messages.success(
        request, f"Autonomía {'activada' if sol.autonomo else 'desactivada'} para la solicitud {sol.pk}."
    )
    return redirect("sigmalab:detalle-solicitud", pk=pk)


@login_required_dtf
def sample_list(request):
    samples = Sample.objects.all()
    return render(request, "sigmalab/sample_list.html", {"samples": samples})


@login_required_dtf
def sample_create(request):
    if request.method == "POST":
        form = SampleForm(request.POST)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.owner = request.user
            sample.save()
            messages.success(request, "Muestra creada correctamente.")
            return redirect("sigmalab:sample-list")
    else:
        form = SampleForm()
    return render(request, "sigmalab/sample_form.html", {"form": form})


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def usuarios_overview(request):
    User = get_user_model()
    from dtf.models import DTFUserProfile, InfoImportanteAcceso
    
    usuarios = User.objects.annotate(num_solicitudes=Count("solicitudes")).order_by("-date_joined")
    recientes = usuarios[:10]
    
    # Obtener información de acceso a información importante
    usuarios_info = []
    for usuario in usuarios:
        try:
            profile = usuario.dtf_profile
            accesos = InfoImportanteAcceso.objects.filter(user=usuario).order_by('seccion')
            usuarios_info.append({
                'usuario': usuario,
                'profile': profile,
                'accesos': accesos,
                'completado': profile.info_importante_completada,
                'inicio': profile.info_importante_inicio,
                'fin': profile.info_importante_fin,
            })
        except DTFUserProfile.DoesNotExist:
            usuarios_info.append({
                'usuario': usuario,
                'profile': None,
                'accesos': [],
                'completado': False,
                'inicio': None,
                'fin': None,
            })
    
    return render(
        request,
        "sigmalab/usuarios_overview_clean.html",
        {
            "usuarios": usuarios,
            "recientes": recientes,
            "usuarios_info": usuarios_info,
        },
    )


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def gestionar_restriccion(request, user_id, modulo, accion):
    """Gestionar restricciones de acceso para usuarios"""
    from dtf.models import DTFUserProfile
    
    user = get_object_or_404(get_user_model(), id=user_id)
    profile, created = DTFUserProfile.objects.get_or_create(user=user)
    
    if accion == 'aplicar':
        if modulo == 's_lab':
            profile.acceso_s_lab_restringido = True
            messages.warning(request, f"Acceso a S-LAB restringido para {user.first_name} {user.last_name or user.username}")
        elif modulo == 's_mec':
            profile.acceso_s_mec_restringido = True
            messages.warning(request, f"Acceso a S-MEC restringido para {user.first_name} {user.last_name or user.username}")
        
        profile.motivo_restriccion = f"Restricción aplicada por {request.user.first_name} {request.user.last_name or request.user.username}"
        profile.restriccion_fecha = timezone.now()
        profile.restriccion_por = request.user
        
    elif accion == 'quitar':
        if modulo == 's_lab':
            profile.acceso_s_lab_restringido = False
            messages.success(request, f"Restricción de S-LAB eliminada para {user.first_name} {user.last_name or user.username}")
        elif modulo == 's_mec':
            profile.acceso_s_mec_restringido = False
            messages.success(request, f"Restricción de S-MEC eliminada para {user.first_name} {user.last_name or user.username}")
        
        profile.motivo_restriccion = ""
        profile.restriccion_fecha = None
        profile.restriccion_por = None
    
    profile.save()
    return redirect("sigmalab:usuarios-overview")


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def crear_usuario(request):
    """Crear usuarios TFM/TFG sin matrícula CIEMAT"""
    from accounts.forms import DTFRegisterForm
    from dtf.models import DTFUserProfile
    
    if request.method == "POST":
        form = DTFRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # Activar directamente para usuarios creados por técnicos
            user.save()
            
            # Crear perfil DTF
            profile = DTFUserProfile.objects.create(
                user=user,
                is_ciemat=form.cleaned_data.get('is_ciemat', False),
                departamento=form.cleaned_data.get('departamento', ''),
                matricula=form.cleaned_data.get('matricula', ''),
                telefono_interno=form.cleaned_data.get('telefono_interno', ''),
            )
            
            # Asignar grupo de usuarios DTF
            from django.contrib.auth.models import Group
            group, created = Group.objects.get_or_create(name="usuarios_dtf")
            user.groups.add(group)
            
            messages.success(request, f"Usuario {user.first_name} {user.last_name} creado exitosamente.")
            return redirect("sigmalab:usuarios-overview")
    else:
        form = DTFRegisterForm()
    
    return render(request, "sigmalab/crear_usuario.html", {"form": form})


@login_required_dtf
@user_passes_test_dtf(is_technician)
def user_details_ajax(request, user_id):
    """Vista AJAX para cargar detalles completos de un usuario"""
    user = get_object_or_404(User, id=user_id)
    
    # Obtener perfil DTF
    try:
        profile = user.dtf_profile
    except:
        profile = None
    
    # Obtener solicitudes del usuario
    solicitudes = Solicitud.objects.filter(solicitante=user).order_by('-creado_en')[:10]
    
    # Obtener información importante
    try:
        info_importante = InfoImportanteAcceso.objects.filter(user=user).first()
    except:
        info_importante = None
    
    # Obtener accesos a secciones
    accesos = []
    if info_importante:
        accesos = info_importante.accesos.all().order_by('-accedido_en')
    
    # Estadísticas de solicitudes
    stats_solicitudes = {
        'total': Solicitud.objects.filter(solicitante=user).count(),
        'pendientes': Solicitud.objects.filter(solicitante=user, estado='pendiente').count(),
        'aceptadas': Solicitud.objects.filter(solicitante=user, estado='aceptada').count(),
        'en_curso': Solicitud.objects.filter(solicitante=user, estado='en_curso').count(),
        'finalizadas': Solicitud.objects.filter(solicitante=user, estado='finalizada').count(),
        'rechazadas': Solicitud.objects.filter(solicitante=user, estado='rechazada').count(),
        'anuladas': Solicitud.objects.filter(solicitante=user, estado='anulada').count(),
    }
    
    context = {
        'user': user,
        'profile': profile,
        'solicitudes': solicitudes,
        'info_importante': info_importante,
        'accesos': accesos,
        'stats_solicitudes': stats_solicitudes,
    }
    
    html = render_to_string('sigmalab/partials/user_details.html', context)
    return JsonResponse({'html': html})


# ========= VISTAS PARA GESTIÓN DE BECARIOS =========

@login_required_dtf
@user_passes_test_dtf(is_technician)
def gestionar_becarios(request):
    """Vista para que los técnicos gestionen todos los becarios"""
    becarios = UsuarioAsociado.objects.all().order_by('-creado_en')
    
    # Estadísticas
    stats = {
        'total': becarios.count(),
        'activos': becarios.filter(estado='activo').count(),
        'inactivos': becarios.filter(estado='inactivo').count(),
        'suspendidos': becarios.filter(estado='suspendido').count(),
    }
    
    return render(request, 'sigmalab/gestionar_becarios.html', {
        'becarios': becarios,
        'stats': stats,
    })


@login_required_dtf
def mis_becarios(request):
    """Vista para que los investigadores vean sus becarios asociados"""
    becarios = UsuarioAsociado.objects.filter(
        investigador_principal=request.user
    ).order_by('-creado_en')
    
    # Estadísticas
    stats = {
        'total': becarios.count(),
        'activos': becarios.filter(estado='activo').count(),
        'inactivos': becarios.filter(estado='inactivo').count(),
        'suspendidos': becarios.filter(estado='suspendido').count(),
    }
    
    return render(request, 'sigmalab/mis_becarios.html', {
        'becarios': becarios,
        'stats': stats,
    })


@login_required_dtf
@user_passes_test_dtf(is_technician)
def crear_becario(request):
    """Vista para que los técnicos creen un nuevo becario"""
    if request.method == 'POST':
        form = UsuarioAsociadoForm(
            request.POST,
            creado_por=request.user,
            es_tecnico=True
        )
        if form.is_valid():
            becario = form.save()
            messages.success(
                request, 
                f'Becario {becario.nombre_completo} creado exitosamente y asociado a {becario.investigador_principal.get_full_name()}.'
            )
            return redirect('sigmalab:gestionar-becarios')
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = UsuarioAsociadoForm(
            creado_por=request.user,
            es_tecnico=True
        )
    
    return render(request, 'sigmalab/crear_becario.html', {'form': form})


@login_required_dtf
@user_passes_test_dtf(is_technician)
def editar_becario(request, becario_id):
    """Vista para que los técnicos editen un becario existente"""
    becario = get_object_or_404(UsuarioAsociado, id=becario_id)
    
    if request.method == 'POST':
        form = UsuarioAsociadoForm(
            request.POST,
            instance=becario,
            creado_por=request.user,
            es_tecnico=True
        )
        if form.is_valid():
            becario = form.save()
            messages.success(
                request, 
                f'Becario {becario.nombre_completo} actualizado exitosamente.'
            )
            return redirect('sigmalab:gestionar-becarios')
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = UsuarioAsociadoForm(
            instance=becario,
            creado_por=request.user,
            es_tecnico=True
        )
    
    return render(request, 'sigmalab/editar_becario.html', {
        'form': form,
        'becario': becario
    })


@login_required_dtf
def detalle_becario(request, becario_id):
    """Vista para ver detalles de un becario"""
    becario = get_object_or_404(UsuarioAsociado, id=becario_id)
    
    # Verificar permisos: solo el investigador principal o técnicos pueden ver
    if not (becario.investigador_principal == request.user or is_technician(request.user)):
        messages.error(request, 'No tienes permisos para ver este becario.')
        return redirect('sigmalab:panel-usuario')
    
    # Obtener solicitudes realizadas por este becario
    solicitudes = Solicitud.objects.filter(
        becario_asociado=becario
    ).order_by('-creado_en')[:10]
    
    # Estadísticas de solicitudes
    stats_solicitudes = {
        'total': Solicitud.objects.filter(becario_asociado=becario).count(),
        'pendientes': Solicitud.objects.filter(becario_asociado=becario, estado='pendiente').count(),
        'aceptadas': Solicitud.objects.filter(becario_asociado=becario, estado='aceptada').count(),
        'en_curso': Solicitud.objects.filter(becario_asociado=becario, estado='en_curso').count(),
        'finalizadas': Solicitud.objects.filter(becario_asociado=becario, estado='finalizada').count(),
        'rechazadas': Solicitud.objects.filter(becario_asociado=becario, estado='rechazada').count(),
    }
    
    return render(request, 'sigmalab/detalle_becario.html', {
        'becario': becario,
        'solicitudes': solicitudes,
        'stats_solicitudes': stats_solicitudes,
    })


@login_required_dtf
@user_passes_test_dtf(is_technician)
def cambiar_estado_becario(request, becario_id, nuevo_estado):
    """Vista para que los técnicos cambien el estado de un becario"""
    becario = get_object_or_404(UsuarioAsociado, id=becario_id)
    
    if nuevo_estado in ['activo', 'inactivo', 'suspendido']:
        estado_anterior = becario.estado
        becario.estado = nuevo_estado
        becario.save()
        
        messages.success(
            request, 
            f'Estado de {becario.nombre_completo} cambiado de {estado_anterior} a {nuevo_estado}.'
        )
    else:
        messages.error(request, 'Estado no válido.')
    
    return redirect('sigmalab:detalle-becario', becario_id=becario_id)


@login_required_dtf
@user_passes_test_dtf(is_technician)
def eliminar_becario(request, becario_id):
    """Vista para que los técnicos eliminen un becario"""
    becario = get_object_or_404(UsuarioAsociado, id=becario_id)
    
    # Verificar que no tenga solicitudes asociadas
    solicitudes_count = Solicitud.objects.filter(becario_asociado=becario).count()
    
    if solicitudes_count > 0:
        messages.error(
            request, 
            f'No se puede eliminar el becario {becario.nombre_completo} porque tiene {solicitudes_count} solicitud(es) asociada(s). '
            'Primero debes cambiar el estado a "inactivo" o "suspendido".'
        )
        return redirect('sigmalab:detalle-becario', becario_id=becario_id)
    
    if request.method == 'POST':
        nombre_becario = becario.nombre_completo
        becario.delete()
        messages.success(request, f'Becario {nombre_becario} eliminado exitosamente.')
        return redirect('sigmalab:gestionar-becarios')
    
    return render(request, 'sigmalab/confirmar_eliminar_becario.html', {
        'becario': becario
    })


# ========= VISTAS PARA GESTIÓN DE LABORATORIO =========

@login_required_dtf
@user_passes_test_dtf(is_technician)
def solicitudes_aceptadas(request):
    """Vista para que los técnicos vean solicitudes aceptadas listas para iniciar trabajo"""
    solicitudes = Solicitud.objects.filter(
        estado='aceptada'
    ).select_related('solicitante', 'becario_asociado').order_by('-creado_en')
    
    return render(request, 'sigmalab/solicitudes_aceptadas.html', {
        'solicitudes': solicitudes,
    })


@login_required_dtf
def entrar_laboratorio(request, solicitud_id=None):
    """Vista para marcar entrada al laboratorio (inicio de trabajo)"""
    if solicitud_id:
        # Vista específica para una solicitud
        solicitud = get_object_or_404(Solicitud, id=solicitud_id)
        
        # Verificar permisos
        if not (is_technician(request.user) or 
                (solicitud.solicitante == request.user and solicitud.es_autonomo)):
            messages.error(request, 'No tienes permisos para acceder a esta solicitud.')
            return redirect('sigmalab:panel-usuario')
        
        # Verificar que esté aceptada
        if solicitud.estado != 'aceptada':
            messages.error(request, 'Solo se puede marcar entrada al laboratorio en solicitudes aceptadas.')
            return redirect('sigmalab:detalle-solicitud', pk=solicitud.id)
        
        if request.method == 'POST':
            # Marcar como en curso
            solicitud.estado = 'en_curso'
            solicitud.fecha_inicio_trabajo = timezone.now()
            solicitud.save()
            
            # Crear avance automático
            from .models import Avance
            Avance.objects.create(
                solicitud=solicitud,
                tipo='inicio_trabajo',
                contenido=f'Inicio de trabajo en laboratorio - {request.user.get_full_name()}',
                autor=request.user,
                visible_para_usuario=True
            )
            
            messages.success(request, f'Solicitud #{solicitud.id} marcada como "En curso". Trabajo iniciado.')
            return redirect('sigmalab:detalle-solicitud', pk=solicitud.id)
        
        return render(request, 'sigmalab/entrar_laboratorio.html', {
            'solicitud': solicitud,
        })
    
    else:
        # Vista general - diferente para técnicos y usuarios autónomos
        if is_technician(request.user):
            # Vista para técnicos - todas las solicitudes aceptadas
            solicitudes_aceptadas = Solicitud.objects.filter(
                estado='aceptada'
            ).select_related('solicitante', 'becario_asociado').order_by('-creado_en')
            
            return render(request, 'sigmalab/entrar_laboratorio_general.html', {
                'solicitudes': solicitudes_aceptadas,
            })
        else:
            # Vista para usuarios autónomos - solo sus solicitudes autónomas aceptadas
            solicitudes_autonomas = Solicitud.objects.filter(
                solicitante=request.user,
                estado='aceptada',
                es_autonomo=True
            ).select_related('becario_asociado').order_by('-creado_en')
            
            return render(request, 'sigmalab/entrar_laboratorio_usuario.html', {
                'solicitudes': solicitudes_autonomas,
            })


# ========= Vistas de Mensajes Internos =========

@login_required_dtf
def inbox_mensajes(request):
    """Vista para mostrar el inbox de mensajes del usuario"""
    from .models import MensajeInterno
    
    # Obtener mensajes recibidos
    mensajes_recibidos = MensajeInterno.objects.filter(
        destinatario=request.user
    ).select_related('remitente', 'solicitud').order_by('-fecha_envio')
    
    # Obtener mensajes enviados
    mensajes_enviados = MensajeInterno.objects.filter(
        remitente=request.user
    ).select_related('destinatario', 'solicitud').order_by('-fecha_envio')
    
    # Estadísticas
    stats = {
        'total_recibidos': mensajes_recibidos.count(),
        'no_leidos': mensajes_recibidos.filter(leido=False).count(),
        'urgentes': mensajes_recibidos.filter(tipo_mensaje='urgencia', leido=False).count(),
        'total_enviados': mensajes_enviados.count(),
    }
    
    # Filtrar por tipo si se especifica
    tipo_filtro = request.GET.get('tipo', '')
    if tipo_filtro:
        mensajes_recibidos = mensajes_recibidos.filter(tipo_mensaje=tipo_filtro)
    
    # Filtrar por estado de lectura
    estado_filtro = request.GET.get('estado', '')
    if estado_filtro == 'no_leidos':
        mensajes_recibidos = mensajes_recibidos.filter(leido=False)
    elif estado_filtro == 'leidos':
        mensajes_recibidos = mensajes_recibidos.filter(leido=True)
    
    return render(request, 'sigmalab/inbox_mensajes.html', {
        'mensajes_recibidos': mensajes_recibidos[:20],  # Últimos 20
        'mensajes_enviados': mensajes_enviados[:10],    # Últimos 10
        'stats': stats,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
    })


@login_required_dtf
def detalle_mensaje(request, mensaje_id):
    """Vista para mostrar el detalle de un mensaje"""
    from .models import MensajeInterno
    
    mensaje = get_object_or_404(MensajeInterno, id=mensaje_id)
    
    # Verificar que el usuario puede ver este mensaje
    if mensaje.destinatario != request.user and mensaje.remitente != request.user:
        messages.error(request, 'No tienes permisos para ver este mensaje.')
        return redirect('sigmalab:inbox-mensajes')
    
    # Marcar como leído si es el destinatario
    if mensaje.destinatario == request.user and not mensaje.leido:
        mensaje.marcar_como_leido()
    
    return render(request, 'sigmalab/detalle_mensaje.html', {
        'mensaje': mensaje,
    })


@login_required_dtf
def enviar_mensaje(request):
    """Vista para enviar un nuevo mensaje"""
    from .forms import MensajeInternoForm
    
    if request.method == 'POST':
        form = MensajeInternoForm(request.POST, remitente=request.user)
        if form.is_valid():
            mensaje = form.save()
            messages.success(request, f'Mensaje enviado a {mensaje.destinatario.get_full_name()}.')
            return redirect('sigmalab:inbox-mensajes')
    else:
        form = MensajeInternoForm(remitente=request.user)
    
    return render(request, 'sigmalab/enviar_mensaje.html', {
        'form': form,
    })


@login_required_dtf
def responder_mensaje(request, mensaje_id):
    """Vista para responder a un mensaje"""
    from .models import MensajeInterno
    from .forms import MensajeInternoForm
    
    mensaje_original = get_object_or_404(MensajeInterno, id=mensaje_id)
    
    # Verificar que el usuario puede responder a este mensaje
    if mensaje_original.destinatario != request.user and mensaje_original.remitente != request.user:
        messages.error(request, 'No tienes permisos para responder a este mensaje.')
        return redirect('sigmalab:inbox-mensajes')
    
    if request.method == 'POST':
        form = MensajeInternoForm(request.POST, remitente=request.user)
        if form.is_valid():
            mensaje = form.save()
            messages.success(request, f'Respuesta enviada a {mensaje.destinatario.get_full_name()}.')
            return redirect('sigmalab:detalle-mensaje', mensaje_id=mensaje.id)
    else:
        # Pre-llenar el formulario con datos del mensaje original
        initial_data = {
            'destinatario': mensaje_original.remitente,
            'asunto': f'Re: {mensaje_original.asunto}',
            'solicitud': mensaje_original.solicitud,
        }
        form = MensajeInternoForm(initial=initial_data, remitente=request.user)
    
    return render(request, 'sigmalab/responder_mensaje.html', {
        'form': form,
        'mensaje_original': mensaje_original,
    })


@login_required_dtf
def marcar_mensaje_leido(request, mensaje_id):
    """Vista AJAX para marcar un mensaje como leído"""
    from .models import MensajeInterno
    
    mensaje = get_object_or_404(MensajeInterno, id=mensaje_id)
    
    # Verificar que el usuario es el destinatario
    if mensaje.destinatario != request.user:
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    mensaje.marcar_como_leido()
    
    return JsonResponse({'success': True, 'fecha_leido': mensaje.fecha_leido.isoformat()})


@login_required_dtf
def indicadores_calidad(request):
    """Vista para mostrar indicadores de calidad I1 e I2 en Sigma Lab"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmalab:panel_tecnico')
    
    # Obtener todas las solicitudes del técnico
    solicitudes = Solicitud.objects.filter(tecnico_asignado=request.user).order_by('-creado_en')
    
    # Obtener indicadores para cada solicitud
    indicadores_data = []
    for solicitud in solicitudes:
        indicador, created = LabIndicadorCalidad.objects.get_or_create(
            solicitud=solicitud,
            defaults={'fecha_recepcion': solicitud.creado_en}
        )
        
        # Si se creó un nuevo indicador, actualizar las fechas
        if created:
            indicador.fecha_recepcion = solicitud.creado_en
            if solicitud.estado == Solicitud.Estado.FINALIZADA:
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
    promedio_i1 = LabIndicadorCalidad.obtener_promedio_i1()
    promedio_i2 = LabIndicadorCalidad.obtener_promedio_i2()
    
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
    
    return render(request, 'sigmalab/indicadores_calidad.html', context)


@login_required_dtf
def actualizar_indicador_lab(request, solicitud_id):
    """Vista para actualizar fechas de un indicador específico en Sigma Lab"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmalab:panel_tecnico')
    
    solicitud = get_object_or_404(Solicitud, id=solicitud_id, tecnico_asignado=request.user)
    
    if request.method == 'POST':
        indicador, created = LabIndicadorCalidad.objects.get_or_create(
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
                return redirect('sigmalab:indicadores_calidad')
        
        if fecha_entrega:
            from datetime import datetime
            try:
                indicador.fecha_entrega_informe = datetime.fromisoformat(fecha_entrega)
            except ValueError:
                messages.error(request, 'Formato de fecha de entrega inválido.')
                return redirect('sigmalab:indicadores_calidad')
        
        # Actualizar indicadores calculados
        indicador.actualizar_indicadores()
        
        messages.success(request, f'Indicadores actualizados para la solicitud {solicitud.material}.')
        return redirect('sigmalab:indicadores_calidad')
    
    return redirect('sigmalab:indicadores_calidad')


# ========= VISTAS PARA SISTEMA DE EQUIPOS =========

@login_required_dtf
def equipos_lista(request):
    """Lista de equipos disponibles para préstamo"""
    if not is_technician_sl(request.user) and not is_user_dtf(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmalab:panel_tecnico')
    
    # Formulario de búsqueda
    buscar_form = BuscarEquipoForm(request.GET)
    equipos = EquipoLaboratorio.objects.all()
    
    if buscar_form.is_valid():
        buscar_por = buscar_form.cleaned_data.get('buscar_por')
        termino = buscar_form.cleaned_data.get('termino_busqueda')
        solo_disponibles = buscar_form.cleaned_data.get('solo_disponibles', False)
        
        if termino:
            if buscar_por == 'nombre':
                equipos = equipos.filter(nombre__icontains=termino)
            elif buscar_por == 'codigo':
                equipos = equipos.filter(codigo__icontains=termino)
            elif buscar_por == 'categoria':
                equipos = equipos.filter(categoria__icontains=termino)
        
        if solo_disponibles:
            equipos = equipos.filter(estado='disponible', disponible_para_prestamo=True)
    
    # Si es usuario DTF, solo mostrar equipos disponibles
    if is_user_dtf(request.user) and not is_technician_sl(request.user):
        equipos = equipos.filter(estado='disponible', disponible_para_prestamo=True)
    
    context = {
        'equipos': equipos,
        'buscar_form': buscar_form,
        'es_tecnico': is_technician_sl(request.user),
    }
    
    return render(request, 'sigmalab/equipos/lista.html', context)


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def equipos_crear(request):
    """Crear nuevo equipo"""
    if request.method == 'POST':
        form = EquipoLaboratorioForm(request.POST, creado_por=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipo creado exitosamente.')
            return redirect('sigmalab:equipos_lista')
    else:
        form = EquipoLaboratorioForm(creado_por=request.user)
    
    context = {
        'form': form,
        'titulo': 'Crear Nuevo Equipo',
    }
    
    return render(request, 'sigmalab/equipos/crear_editar.html', context)


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def equipos_editar(request, equipo_id):
    """Editar equipo existente"""
    equipo = get_object_or_404(EquipoLaboratorio, id=equipo_id)
    
    if request.method == 'POST':
        form = EquipoLaboratorioForm(request.POST, instance=equipo, creado_por=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipo actualizado exitosamente.')
            return redirect('sigmalab:equipos_lista')
    else:
        form = EquipoLaboratorioForm(instance=equipo, creado_por=request.user)
    
    context = {
        'form': form,
        'equipo': equipo,
        'titulo': f'Editar {equipo.nombre}',
    }
    
    return render(request, 'sigmalab/equipos/crear_editar.html', context)


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def equipos_eliminar(request, equipo_id):
    """Eliminar equipo"""
    equipo = get_object_or_404(EquipoLaboratorio, id=equipo_id)
    
    # Verificar que no tenga préstamos activos
    if equipo.prestamos_activos.exists():
        messages.error(request, 'No se puede eliminar un equipo que tiene préstamos activos.')
        return redirect('sigmalab:equipos_lista')
    
    if request.method == 'POST':
        equipo.delete()
        messages.success(request, 'Equipo eliminado exitosamente.')
        return redirect('sigmalab:equipos_lista')
    
    context = {
        'equipo': equipo,
    }
    
    return render(request, 'sigmalab/equipos/eliminar.html', context)


@login_required_dtf
def prestamo_solicitar(request):
    """Solicitar préstamo de equipo"""
    if not is_user_dtf(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmalab:panel_tecnico')
    
    # Obtener técnico responsable
    tecnico_responsable = User.objects.filter(
        groups__name='tecnico_responsable_s_lab'
    ).first()
    
    if not tecnico_responsable:
        messages.error(request, "No hay técnico responsable asignado.")
        return redirect('sigmalab:equipos_lista')
    
    if request.method == 'POST':
        form = PrestamoEquipoForm(
            request.POST, 
            usuario=request.user, 
            tecnico_responsable=tecnico_responsable
        )
        if form.is_valid():
            prestamo = form.save()
            
            # Crear notificación para el técnico
            NotificacionPrestamo.objects.create(
                prestamo=prestamo,
                destinatario=tecnico_responsable,
                tipo='prestamo_realizado',
                mensaje=f'El usuario {request.user.get_full_name()} ha solicitado el préstamo del equipo {prestamo.equipo.nombre} por {prestamo.dias_prestamo} días.'
            )
            
            messages.success(request, f'Préstamo solicitado exitosamente. Se ha notificado al técnico responsable.')
            return redirect('sigmalab:mis_prestamos')
    else:
        form = PrestamoEquipoForm(
            usuario=request.user, 
            tecnico_responsable=tecnico_responsable
        )
    
    context = {
        'form': form,
        'titulo': 'Solicitar Préstamo de Equipo',
    }
    
    return render(request, 'sigmalab/equipos/prestamo_solicitar.html', context)


@login_required_dtf
def mis_prestamos(request):
    """Lista de préstamos del usuario actual"""
    if not is_user_dtf(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmalab:panel_tecnico')
    
    prestamos = PrestamoEquipo.objects.filter(usuario=request.user).order_by('-fecha_prestamo')
    
    context = {
        'prestamos': prestamos,
    }
    
    return render(request, 'sigmalab/equipos/mis_prestamos.html', context)


@login_required_dtf
def prestamo_devolver(request, prestamo_id):
    """Devolver equipo prestado"""
    prestamo = get_object_or_404(PrestamoEquipo, id=prestamo_id, usuario=request.user)
    
    if prestamo.estado != 'activo':
        messages.error(request, 'Este préstamo no está activo.')
        return redirect('sigmalab:mis_prestamos')
    
    if request.method == 'POST':
        form = DevolucionEquipoForm(request.POST, instance=prestamo)
        if form.is_valid():
            form.save()
            
            # Crear notificación para el técnico
            NotificacionPrestamo.objects.create(
                prestamo=prestamo,
                destinatario=prestamo.tecnico_responsable,
                tipo='equipo_devuelto',
                mensaje=f'El usuario {request.user.get_full_name()} ha devuelto el equipo {prestamo.equipo.nombre}.'
            )
            
            messages.success(request, 'Equipo devuelto exitosamente.')
            return redirect('sigmalab:mis_prestamos')
    else:
        form = DevolucionEquipoForm(instance=prestamo)
    
    context = {
        'form': form,
        'prestamo': prestamo,
        'titulo': f'Devolver {prestamo.equipo.nombre}',
    }
    
    return render(request, 'sigmalab/equipos/prestamo_devolver.html', context)


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def prestamos_gestionar(request):
    """Gestión de préstamos para técnicos"""
    # Formulario de filtros
    filtro_form = FiltroPrestamosForm(request.GET)
    prestamos = PrestamoEquipo.objects.all()
    
    if filtro_form.is_valid():
        estado = filtro_form.cleaned_data.get('estado')
        usuario = filtro_form.cleaned_data.get('usuario')
        equipo = filtro_form.cleaned_data.get('equipo')
        fecha_desde = filtro_form.cleaned_data.get('fecha_desde')
        fecha_hasta = filtro_form.cleaned_data.get('fecha_hasta')
        
        if estado:
            prestamos = prestamos.filter(estado=estado)
        if usuario:
            prestamos = prestamos.filter(usuario=usuario)
        if equipo:
            prestamos = prestamos.filter(equipo=equipo)
        if fecha_desde:
            prestamos = prestamos.filter(fecha_prestamo__date__gte=fecha_desde)
        if fecha_hasta:
            prestamos = prestamos.filter(fecha_prestamo__date__lte=fecha_hasta)
    
    # Estadísticas
    prestamos_activos = prestamos.filter(estado='activo').count()
    prestamos_vencidos = prestamos.filter(estado='vencido').count()
    prestamos_devueltos = prestamos.filter(estado='devuelto').count()
    
    context = {
        'prestamos': prestamos,
        'filtro_form': filtro_form,
        'prestamos_activos': prestamos_activos,
        'prestamos_vencidos': prestamos_vencidos,
        'prestamos_devueltos': prestamos_devueltos,
    }
    
    return render(request, 'sigmalab/equipos/prestamos_gestionar.html', context)


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def prestamos_vencidos(request):
    """Lista de préstamos vencidos"""
    prestamos_vencidos = PrestamoEquipo.objects.filter(
        estado='activo',
        fecha_devolucion_estimada__lt=timezone.now()
    ).order_by('fecha_devolucion_estimada')
    
    context = {
        'prestamos_vencidos': prestamos_vencidos,
    }
    
    return render(request, 'sigmalab/equipos/prestamos_vencidos.html', context)


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def notificaciones_prestamos(request):
    """Lista de notificaciones de préstamos"""
    notificaciones = NotificacionPrestamo.objects.filter(
        destinatario=request.user
    ).order_by('-fecha_creacion')
    
    context = {
        'notificaciones': notificaciones,
    }
    
    return render(request, 'sigmalab/equipos/notificaciones.html', context)


@login_required_dtf
@user_passes_test_dtf(is_technician_sl)
def notificacion_marcar_leida(request, notificacion_id):
    """Marcar notificación como leída"""
    notificacion = get_object_or_404(NotificacionPrestamo, id=notificacion_id, destinatario=request.user)
    notificacion.marcar_como_enviada()
    messages.success(request, 'Notificación marcada como leída.')
    return redirect('sigmalab:notificaciones_prestamos')
