# sigmadp/views.py
import json
import os
from pathlib import Path
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test as _user_passes_test
from django.contrib.auth import get_user_model
from core.roles import is_dp_tech
from dtf.decorators import dtf_required, dtf_lab_gate
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import DpSample, DpSolicitud, DpMuestraNombre, DpEvento, DpNecesidad, DpMensaje, DpSolicitudTermica, DpResultadoTermico, DpAnalisisDatos, DpIndicadorCalidad
from .forms import DpSampleForm, DpSolicitudForm, DpSolicitudTermicaForm, DpResultadoTermicoForm, DpSolicitudUnificadaForm, DpMuestraForm, DpAnalisisDatosForm
from .utils import enviar_resultados_termicos, enviar_notificacion_aceptacion, enviar_notificacion_rechazo


def login_required_dtf(view):
    return dtf_required(view)


def is_tecnico_responsable(user):
    return user.is_authenticated and (user.is_superuser or is_dp_tech(user))


def _get_selector_datos_solicitudes():
    """Obtiene usuarios con solicitudes termicas y sus solicitudes asociadas."""
    User = get_user_model()
    solicitantes = User.objects.filter(dp_solicitudes_termicas__isnull=False).distinct().order_by(
        'first_name', 'last_name', 'username'
    )
    if not solicitantes:
        return solicitantes, DpSolicitudTermica.objects.none()
    solicitudes = (
        DpSolicitudTermica.objects.filter(solicitante__in=solicitantes)
        .select_related('solicitante')
        .order_by('-creado_en')
    )
    return solicitantes, solicitudes

def _coerce_to_int(value):
    """Convierte el valor recibido en un entero si es posible."""
    if value is None:
        return None
    if hasattr(value, 'pk'):
        return value.pk
    try:
        return int(value)
    except (TypeError, ValueError):
        return None




@login_required_dtf
def panel_usuario(request):
    # Los tecnicos no necesitan leer informacion importante
    if is_tecnico_responsable(request.user):
        return redirect("sigmadp:panel_tecnico")
    
    # Verificar restricciones de acceso
    from dtf.models import DTFUserProfile
    try:
        profile = request.user.dtf_profile
        if profile.acceso_s_dp_restringido:
            messages.error(request, f"Tu acceso a S-DP ha sido restringido. Motivo: {profile.motivo_restriccion}")
            return redirect("dtf:dashboard")
    except DTFUserProfile.DoesNotExist:
        # Si no tiene perfil DTF, crear uno
        profile = DTFUserProfile.objects.create(user=request.user)
    
    # Verificar si el usuario ha completado la informacion importante
    if not profile.info_importante_completada:
        messages.info(request, "Debes completar la informacion importante antes de acceder al panel.")
        return redirect("dtf:info-importante")
    
    # Solicitudes de S-DP
    dp_solicitudes = DpSolicitud.objects.filter(solicitante=request.user).order_by("-creado_en")
    
    # Solicitudes termicas de S-DP
    dp_solicitudes_termicas = DpSolicitudTermica.objects.filter(solicitante=request.user).order_by("-creado_en")
    
    # Solicitudes de S-LAB (si el usuario tiene acceso)
    sigmalab_solicitudes = []
    if hasattr(request.user, 'solicitudes'):
        sigmalab_solicitudes = request.user.solicitudes.all().order_by("-creado_en")
    
    # Estadisticas por laboratorio
    stats = {
        'dp': {
            'total': dp_solicitudes.count(),
            'pendientes': dp_solicitudes.filter(estado='pendiente').count(),
            'aceptadas': dp_solicitudes.filter(estado='aceptada').count(),
            'en_curso': dp_solicitudes.filter(estado='en_curso').count(),
            'finalizadas': dp_solicitudes.filter(estado='finalizada').count(),
            'rechazadas': dp_solicitudes.filter(estado='rechazada').count(),
        },
        'dp_termicas': {
            'total': dp_solicitudes_termicas.count(),
            'pendientes': dp_solicitudes_termicas.filter(estado='pendiente').count(),
            'aceptadas': dp_solicitudes_termicas.filter(estado='aceptada').count(),
            'en_curso': dp_solicitudes_termicas.filter(estado='en_curso').count(),
            'finalizadas': dp_solicitudes_termicas.filter(estado='finalizada').count(),
            'rechazadas': dp_solicitudes_termicas.filter(estado='rechazada').count(),
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
    
    return render(request, "sigmadp/panel_usuario.html", {
        "dp_solicitudes": dp_solicitudes[:10],  # Ultimas 10
        "dp_solicitudes_termicas": dp_solicitudes_termicas[:10],  # Ultimas 10
        "sigmalab_solicitudes": sigmalab_solicitudes[:10],
        "stats": stats
    })


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def panel_tecnico_responsable(request):
    """Panel tecnico para solicitudes termicas S-DP"""
    qs = DpSolicitudTermica.objects.all()
    pendientes = qs.filter(estado="pendiente").order_by("-creado_en")[:10]
    en_curso = qs.filter(estado="en_curso").order_by("-creado_en")[:10]
    aceptadas = qs.filter(estado="aceptada").order_by("-creado_en")[:10]
    rechazadas = qs.filter(estado="rechazada").order_by("-creado_en")[:10]
    finalizadas = qs.filter(estado="finalizada").order_by("-creado_en")[:10]

    # KPIs por estado
    stats = {
        "total": qs.count(),
        "pendientes": qs.filter(estado="pendiente").count(),
        "aceptadas": qs.filter(estado="aceptada").count(),
        "en_curso": qs.filter(estado="en_curso").count(),
        "rechazadas": qs.filter(estado="rechazada").count(),
        "finalizadas": qs.filter(estado="finalizada").count(),
    }

    return render(request, "sigmadp/panel_tecnico.html", {
        "solicitudes_pendientes": pendientes,
        "solicitudes_en_curso": en_curso,
        "stats": stats,
    })


@login_required_dtf
def sample_create(request):
    # Los tecnicos responsables no pueden crear muestras
    if is_tecnico_responsable(request.user) and not request.user.is_superuser:
        messages.error(request, "Los tecnicos responsables no pueden crear muestras en S-DP.")
        return redirect("sigmadp:panel_tecnico")
    if request.method == "POST":
        form = DpSampleForm(request.POST)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.owner = request.user
            sample.save()
            messages.success(request, "Muestra creada correctamente.")
            return redirect("sigmadp:panel_usuario")
    else:
        form = DpSampleForm()
    return render(request, "sigmadp/sample_form.html", {"form": form})


@login_required_dtf
def solicitud_create(request):
    # Los tecnicos responsables no pueden crear solicitudes
    if is_tecnico_responsable(request.user) and not request.user.is_superuser:
        messages.error(request, "Los tecnicos responsables no pueden crear solicitudes en S-DP.")
        return redirect("sigmadp:panel_tecnico")
    if request.method == "POST":
        form = DpSolicitudForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.solicitante = request.user
            obj.save()
            
            # Guardar denominaciones de muestras dinamicas
            for key, value in request.POST.items():
                if key.startswith('muestra_nombre_') and value.strip():
                    DpMuestraNombre.objects.create(solicitud=obj, nombre=value.strip())
            
            messages.success(request, f"Solicitud DP#{obj.pk} creada correctamente.")
            return redirect("sigmadp:panel_usuario")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DpSolicitudForm()
    return render(request, "sigmadp/solicitud_form.html", {"form": form})


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def solicitud_detalle(request, pk):
    s = get_object_or_404(DpSolicitud, pk=pk)
    eventos = s.eventos.select_related("autor").all()
    return render(request, "sigmadp/solicitud_detalle.html", {"s": s, "eventos": eventos})


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def evento_crear(request, pk):
    s = get_object_or_404(DpSolicitud, pk=pk)
    if request.method == "POST":
        texto = (request.POST.get("texto") or "").strip()
        if texto:
            DpEvento.objects.create(solicitud=s, autor=request.user, texto=texto)
            messages.success(request, "Entrada anadida al diario.")
        else:
            messages.error(request, "El texto del evento no puede estar vacio.")
    return redirect("sigmadp:solicitud_detalle", pk=s.pk)


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def ficha_equipo(request):
    return render(request, "sigmadp/ficha_equipo.html", {})


@dtf_lab_gate("s_dp")
def necesidades(request):
    if request.method == "POST":
        titulo = (request.POST.get("titulo") or "").strip()
        descripcion = (request.POST.get("descripcion") or "").strip()
        fecha = (request.POST.get("fecha") or "").strip()
        if titulo and fecha:
            from datetime import datetime
            try:
                f = datetime.strptime(fecha, "%Y-%m-%d").date()
                DpNecesidad.objects.create(titulo=titulo, descripcion=descripcion, fecha=f, creado_por=request.user)
                messages.success(request, "Necesidad registrada.")
            except Exception:
                messages.error(request, "Fecha invalida (use aaaa-mm-dd).")
        else:
            messages.error(request, "Titulo y fecha son obligatorios.")
    if is_tecnico_responsable(request.user):
        items = DpNecesidad.objects.all()
    else:
        items = DpNecesidad.objects.filter(creado_por=request.user)
    return render(request, "sigmadp/necesidades.html", {"items": items})


@dtf_lab_gate("s_dp")
def inbox(request):
    if request.method == "POST":
        asunto = (request.POST.get("asunto") or "").strip()
        mensaje = (request.POST.get("mensaje") or "").strip()
        if asunto and mensaje:
            DpMensaje.objects.create(autor=request.user, asunto=asunto, mensaje=mensaje)
            messages.success(request, "Mensaje enviado a los tecnicos responsables.")
        else:
            messages.error(request, "Asunto y mensaje son obligatorios.")
    if is_tecnico_responsable(request.user):
        mensajes = DpMensaje.objects.all().select_related("autor")
    else:
        mensajes = DpMensaje.objects.filter(autor=request.user).select_related("autor")
    return render(request, "sigmadp/inbox.html", {"mensajes": mensajes})


# ===== NUEVAS VISTAS PARA SOLICITUDES TERMICAS =====

@login_required_dtf
def solicitud_unificada_create(request):
    """Crear solicitudes S-DP permitiendo multiples muestras con condiciones compartidas."""

    def clamp_num_muestras(payload) -> int:
        raw_value = payload.get("numero_muestras") if hasattr(payload, "get") else None
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 1
        return max(1, min(10, value))

    def build_empty_samples(total: int):
        return [
            {
                "nombre": "",
                "material": "",
                "procedencia": "",
                "geometria": "",
                "temperatura_maxima": "",
                "tasa_calentamiento": "",
                "tasa_enfriamiento": "",
                "tiempo_permanencia": "",
                "masa_registrar": "",
                "espesor": "",
                "tamano": "",
                "observaciones": "",
            }
            for _ in range(total)
        ]

    def extract_samples(payload, total: int):
        samples = build_empty_samples(total)
        if not hasattr(payload, "get"):
            return samples
        field_map = [
            ("nombre", "nombre"),
            ("material", "material"),
            ("procedencia", "procedencia"),
            ("geometria", "geometria"),
            ("temperatura_maxima", "temperatura_maxima"),
            ("tasa_calentamiento", "tasa_calentamiento"),
            ("tasa_enfriamiento", "tasa_enfriamiento"),
            ("tiempo_permanencia", "tiempo_permanencia"),
            ("masa_registrar", "masa_registrar"),
            ("espesor", "espesor"),
            ("tamano", "tamano"),
            ("observaciones", "observaciones"),
        ]
        for index in range(total):
            prefix = f"muestra_{index + 1}_"
            for key, field in field_map:
                value = payload.get(prefix + field, "")
                if isinstance(value, str):
                    samples[index][key] = value.strip()
        return samples

    if request.method == "POST":
        form = DpSolicitudUnificadaForm(request.POST)
        numero_muestras = clamp_num_muestras(request.POST)
        muestras_raw = extract_samples(request.POST, numero_muestras)

        if form.is_valid():
            data = form.cleaned_data
            errors = []
            samples_payload = []

            if data.get("tipo_solicitud") != "termica":
                form.add_error(
                    "tipo_solicitud",
                    "Por ahora solo esta disponible la solicitud de desorcion termica (TDS).",
                )

            global_defaults = {
                "material": (data.get("material") or "").strip(),
                "procedencia": (data.get("procedencia") or "").strip(),
                "temperatura_maxima": data.get("temperatura_maxima"),
                "tasa_calentamiento": data.get("tasa_calentamiento"),
                "tasa_enfriamiento": data.get("tasa_enfriamiento"),
                "tiempo_permanencia": data.get("tiempo_permanencia"),
                "masa_registrar": data.get("masa_registrar") or "",
                "espesor_muestra": data.get("espesor_muestra"),
                "tamano_muestra": data.get("tamano_muestra"),
                "geometria_muestra": (data.get("geometria_muestra") or "").strip(),
                "observaciones": (data.get("observaciones") or "").strip(),
                "condiciones_globales": data.get("condiciones_globales", False),
            }

            def resolve_float(raw_value, fallback_value, label, sample_index):
                if raw_value:
                    try:
                        return float(str(raw_value).replace(",", "."))
                    except ValueError:
                        errors.append(f"Introduce un valor numerico valido para {label} en la muestra {sample_index}.")
                        return None
                if fallback_value not in (None, ""):
                    return fallback_value
                errors.append(f"Indica {label} para la muestra {sample_index}.")
                return None

            def resolve_choice(raw_value, fallback_value, label, sample_index):
                if raw_value:
                    return raw_value
                if fallback_value:
                    return fallback_value
                errors.append(f"Selecciona {label} para la muestra {sample_index}.")
                return None

            def resolve_text(raw_value, fallback_value, label, sample_index):
                value = raw_value or fallback_value
                if value:
                    return value.strip()
                errors.append(f"Indica {label} para la muestra {sample_index}.")
                return ""

            for idx, sample in enumerate(muestras_raw, start=1):
                nombre = sample["nombre"]
                if not nombre:
                    errors.append(f"La muestra {idx} necesita un nombre.")
                    continue

                material = sample["material"] or global_defaults["material"]
                if not material:
                    errors.append(f"La muestra {idx} necesita indicar el material.")
                    continue

                geometria = resolve_text(
                    sample["geometria"],
                    global_defaults["geometria_muestra"],
                    "la geometria",
                    idx,
                )

                temperatura = resolve_float(
                    sample["temperatura_maxima"],
                    global_defaults["temperatura_maxima"],
                    "la temperatura maxima",
                    idx,
                )
                tasa_calentamiento = resolve_float(
                    sample["tasa_calentamiento"],
                    global_defaults["tasa_calentamiento"],
                    "la tasa de calentamiento",
                    idx,
                )
                tasa_enfriamiento = resolve_float(
                    sample["tasa_enfriamiento"],
                    global_defaults["tasa_enfriamiento"],
                    "la tasa de enfriamiento",
                    idx,
                )
                tiempo_permanencia = resolve_float(
                    sample["tiempo_permanencia"],
                    global_defaults["tiempo_permanencia"],
                    "el tiempo de permanencia",
                    idx,
                )
                masa = resolve_choice(
                    sample["masa_registrar"],
                    global_defaults["masa_registrar"],
                    "la masa a registrar",
                    idx,
                )
                espesor = resolve_float(
                    sample["espesor"],
                    global_defaults["espesor_muestra"],
                    "el espesor",
                    idx,
                )
                tamano = resolve_float(
                    sample["tamano"],
                    global_defaults["tamano_muestra"],
                    "el tamano",
                    idx,
                )

                if any(value is None for value in (
                    temperatura,
                    tasa_calentamiento,
                    tasa_enfriamiento,
                    tiempo_permanencia,
                    espesor,
                    tamano,
                )) or not masa or not geometria:
                    continue

                observaciones_parts = []
                if global_defaults["observaciones"]:
                    observaciones_parts.append(global_defaults["observaciones"])
                if sample["observaciones"]:
                    observaciones_parts.append(sample["observaciones"])
                procedencia_val = sample["procedencia"] or global_defaults["procedencia"]
                if procedencia_val:
                    observaciones_parts.append(f"Procedencia: {procedencia_val}")
                observaciones = "\n\n".join(observaciones_parts)

                samples_payload.append(
                    {
                        "solicitante": request.user,
                        "nombre_muestra": nombre,
                        "material": material,
                        "temperatura_maxima": temperatura,
                        "tasa_calentamiento": tasa_calentamiento,
                        "tasa_enfriamiento": tasa_enfriamiento,
                        "tiempo_permanencia": tiempo_permanencia,
                        "masa_registrar": masa,
                        "espesor_muestra": espesor,
                        "tamano_muestra": tamano,
                        "geometria_muestra": geometria,
                        "observaciones": observaciones,
                    }
                )

            if errors:
                for message in errors:
                    form.add_error(None, message)
                context = {
                    "form": form,
                    "samples_json": json.dumps(muestras_raw, ensure_ascii=False),
                }
                return render(request, "sigmadp/solicitud_unificada_form.html", context)

            if not samples_payload:
                form.add_error(None, "No se han podido preparar muestras validas para crear solicitudes.")
                context = {
                    "form": form,
                    "samples_json": json.dumps(muestras_raw, ensure_ascii=False),
                }
                return render(request, "sigmadp/solicitud_unificada_form.html", context)

            with transaction.atomic():
                for payload in samples_payload:
                    DpSolicitudTermica.objects.create(**payload)

            messages.success(
                request,
                f"Se han creado {len(samples_payload)} solicitudes termicas correctamente.",
            )
            return redirect("sigmadp:panel_usuario")

        context = {
            "form": form,
            "samples_json": json.dumps(muestras_raw, ensure_ascii=False),
        }
        return render(request, "sigmadp/solicitud_unificada_form.html", context)

    form = DpSolicitudUnificadaForm(initial={"tipo_solicitud": "termica", "condiciones_globales": True})
    numero_muestras = clamp_num_muestras({"numero_muestras": form.initial.get("numero_muestras", form.fields["numero_muestras"].initial)})
    muestras_raw = build_empty_samples(numero_muestras)
    context = {
        "form": form,
        "samples_json": json.dumps(muestras_raw, ensure_ascii=False),
    }
    return render(request, "sigmadp/solicitud_unificada_form.html", context)


@login_required_dtf
def solicitud_termica_create(request):
    """Crear nueva solicitud de analisis termico"""
    # Los tecnicos responsables no pueden crear solicitudes
    if is_tecnico_responsable(request.user) and not request.user.is_superuser:
        messages.error(request, "Los tecnicos responsables no pueden crear solicitudes en S-DP.")
        return redirect("sigmadp:panel_tecnico")
    
    if request.method == "POST":
        form = DpSolicitudTermicaForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.solicitante = request.user
            solicitud.save()
            
            messages.success(request, f"Solicitud termica DP-T#{solicitud.pk} creada correctamente.")
            return redirect("sigmadp:panel_usuario")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DpSolicitudTermicaForm()
    
    return render(request, "sigmadp/solicitud_termica_form.html", {"form": form})


@login_required_dtf
def solicitud_termica_detalle(request, pk):
    """Detalle de solicitud termica"""
    solicitud = get_object_or_404(DpSolicitudTermica, pk=pk)
    
    # Solo el solicitante o tecnicos pueden ver el detalle
    if not (solicitud.solicitante == request.user or is_tecnico_responsable(request.user)):
        messages.error(request, "No tienes permisos para ver esta solicitud.")
        return redirect("sigmadp:panel_usuario")
    
    analisis_datos = solicitud.analisis_datos.all().order_by('-creado_en')

    return render(
        request,
        'sigmadp/solicitud_termica_detalle.html',
        {
            'solicitud': solicitud,
            'analisis_datos': analisis_datos,
        },
    )


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def bandeja_entrada_termica(request):
    """Bandeja de entrada para tecnicos - solicitudes termicas"""
    qs = DpSolicitudTermica.objects.all()
    
    # Filtrar por estado
    estado = request.GET.get('estado', 'pendientes')
    if estado == 'pendientes':
        solicitudes = qs.filter(estado='pendiente').order_by('-creado_en')
    elif estado == 'aceptadas':
        solicitudes = qs.filter(estado='aceptada').order_by('-creado_en')
    elif estado == 'en_curso':
        solicitudes = qs.filter(estado='en_curso').order_by('-creado_en')
    elif estado == 'finalizadas':
        solicitudes = qs.filter(estado='finalizada').order_by('-creado_en')
    elif estado == 'rechazadas':
        solicitudes = qs.filter(estado='rechazada').order_by('-creado_en')
    else:
        solicitudes = qs.order_by('-creado_en')
    
    # Estadisticas
    stats = {
        'total': qs.count(),
        'pendientes': qs.filter(estado='pendiente').count(),
        'aceptadas': qs.filter(estado='aceptada').count(),
        'en_curso': qs.filter(estado='en_curso').count(),
        'finalizadas': qs.filter(estado='finalizada').count(),
        'rechazadas': qs.filter(estado='rechazada').count(),
    }
    
    return render(request, "sigmadp/bandeja_entrada_termica.html", {
        "solicitudes": solicitudes,
        "stats": stats,
        "estado_actual": estado
    })


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def aceptar_solicitud_termica(request, pk):
    """Aceptar una solicitud termica"""
    solicitud = get_object_or_404(DpSolicitudTermica, pk=pk)
    
    if not solicitud.puede_ser_aceptada():
        messages.error(request, "Esta solicitud no puede ser aceptada en su estado actual.")
        return redirect("sigmadp:bandeja_entrada_termica")
    
    if request.method == "POST":
        from django.utils import timezone
        solicitud.estado = DpSolicitudTermica.Estado.ACEPTADA
        solicitud.tecnico_responsable = request.user
        solicitud.fecha_aceptacion = timezone.now()
        solicitud.save()
        
        # Enviar notificacion por email
        if enviar_notificacion_aceptacion(solicitud):
            messages.success(request, f"Solicitud DP-T#{solicitud.pk} aceptada correctamente y notificacion enviada.")
        else:
            messages.warning(request, f"Solicitud DP-T#{solicitud.pk} aceptada, pero hubo un problema enviando la notificacion.")
        
        return redirect("sigmadp:bandeja_entrada_termica")
    
    return render(request, "sigmadp/aceptar_solicitud_termica.html", {"solicitud": solicitud})


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def rechazar_solicitud_termica(request, pk):
    """Rechazar una solicitud termica"""
    solicitud = get_object_or_404(DpSolicitudTermica, pk=pk)
    
    if not solicitud.puede_ser_aceptada():
        messages.error(request, "Esta solicitud no puede ser rechazada en su estado actual.")
        return redirect("sigmadp:bandeja_entrada_termica")
    
    if request.method == "POST":
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, "Debes proporcionar un motivo para el rechazo.")
            return render(request, "sigmadp/rechazar_solicitud_termica.html", {"solicitud": solicitud})
        
        solicitud.estado = DpSolicitudTermica.Estado.RECHAZADA
        solicitud.tecnico_responsable = request.user
        solicitud.observaciones = f"RECHAZADA: {motivo}"
        solicitud.save()
        
        # Enviar notificacion por email
        if enviar_notificacion_rechazo(solicitud):
            messages.success(request, f"Solicitud DP-T#{solicitud.pk} rechazada correctamente y notificacion enviada.")
        else:
            messages.warning(request, f"Solicitud DP-T#{solicitud.pk} rechazada, pero hubo un problema enviando la notificacion.")
        
        return redirect("sigmadp:bandeja_entrada_termica")
    
    return render(request, "sigmadp/rechazar_solicitud_termica.html", {"solicitud": solicitud})


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def iniciar_ensayo_termico(request, pk):
    """Iniciar ensayo termico (cambiar estado a EN_CURSO)"""
    solicitud = get_object_or_404(DpSolicitudTermica, pk=pk)
    
    if solicitud.estado != DpSolicitudTermica.Estado.ACEPTADA:
        messages.error(request, "Solo se pueden iniciar ensayos de solicitudes aceptadas.")
        return redirect("sigmadp:bandeja_entrada_termica")
    
    if request.method == "POST":
        solicitud.estado = DpSolicitudTermica.Estado.EN_CURSO
        solicitud.save()
        
        messages.success(request, f"Ensayo termico DP-T#{solicitud.pk} iniciado correctamente.")
        return redirect("sigmadp:bandeja_entrada_termica")
    
    return render(request, "sigmadp/iniciar_ensayo_termico.html", {"solicitud": solicitud})


@login_required_dtf
@_user_passes_test(is_tecnico_responsable, login_url="/accounts/login/dtf/")
def finalizar_ensayo_termico(request, pk):
    """Finalizar ensayo termico y subir resultados"""
    solicitud = get_object_or_404(DpSolicitudTermica, pk=pk)
    
    if not solicitud.puede_ser_finalizada():
        messages.error(request, "Solo se pueden finalizar ensayos en curso.")
        return redirect("sigmadp:bandeja_entrada_termica")
    
    if request.method == "POST":
        form = DpResultadoTermicoForm(request.POST, request.FILES)
        if form.is_valid():
            resultado = form.save(commit=False)
            resultado.solicitud = solicitud
            resultado.tecnico = request.user
            resultado.save()
            
            # Cambiar estado de la solicitud
            from django.utils import timezone
            solicitud.estado = DpSolicitudTermica.Estado.FINALIZADA
            solicitud.fecha_finalizacion = timezone.now()
            solicitud.save()
            
            # Enviar email con resultados
            if enviar_resultados_termicos(solicitud, resultado):
                messages.success(request, f"Ensayo termico DP-T#{solicitud.pk} finalizado y resultados enviados por email correctamente.")
            else:
                messages.warning(request, f"Ensayo termico DP-T#{solicitud.pk} finalizado, pero hubo un problema enviando los resultados por email.")
            
            return redirect("sigmadp:bandeja_entrada_termica")
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DpResultadoTermicoForm()
    
    return render(request, "sigmadp/finalizar_ensayo_termico.html", {
        "solicitud": solicitud,
        "form": form
    })


@login_required_dtf
def info_importante(request):
    return render(request, "sigmadp/info_importante.html")


# ============ VISTAS PARA ANALISIS DE DATOS ============

@login_required_dtf
def representacion_resultados(request):
    """Vista principal para representacion de resultados"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmadp:panel_usuario')
    
    solicitantes, solicitudes = _get_selector_datos_solicitudes()
    # Obtener analisis recientes del tecnico
    analisis_recientes = DpAnalisisDatos.objects.filter(tecnico=request.user).order_by('-creado_en')[:10]
    
    context = {
        'analisis_recientes': analisis_recientes,
    }
    return render(request, 'sigmadp/representacion_resultados.html', context)


@login_required_dtf
def crear_analisis_datos(request):
    """Crear nuevo analisis de datos"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmadp:panel_usuario')
    
    solicitantes, solicitudes = _get_selector_datos_solicitudes()
    if request.method == 'POST':
        form = DpAnalisisDatosForm(request.POST, request.FILES)
        if form.is_valid():
            # Crear el analisis
            analisis = form.save(commit=False)
            if not analisis.nombre:
                archivo_form = form.cleaned_data.get('archivo_datos')
                if archivo_form:
                    analisis.nombre = Path(archivo_form.name).stem or archivo_form.name
            analisis.tecnico = request.user
            analisis.estado = DpAnalisisDatos.Estado.PROCESANDO
            
            # Detectar automaticamente tipo de archivo y propiedades
            archivo = request.FILES.get('archivo_datos')
            if archivo:
                # Detectar tipo de archivo basado en la extension
                nombre_archivo = archivo.name.lower()
                if nombre_archivo.endswith('.csv'):
                    analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.CSV
                elif nombre_archivo.endswith('.tsv'):
                    analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.TSV
                elif nombre_archivo.endswith('.dat'):
                    analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.DAT
                else:
                    analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.TXT
                
                # Detectar automaticamente propiedades del archivo si estan vacias
                if not analisis.separador or not analisis.decimal or not analisis.codificacion:
                    try:
                        from .utils_detect import detect_and_preview
                        props = detect_and_preview(archivo)
                        if not analisis.separador:
                            analisis.separador = props['separator']
                        if not analisis.decimal:
                            analisis.decimal = props['decimal']
                        if not analisis.codificacion:
                            analisis.codificacion = props['encoding']
                    except Exception as e:
                        # Si falla la deteccion, usar valores por defecto
                        if not analisis.separador:
                            analisis.separador = '\t'
                        if not analisis.decimal:
                            analisis.decimal = ','
                        if not analisis.codificacion:
                            analisis.codificacion = 'cp1252'
            
            analisis.save()
            
            # Procesar el archivo en segundo plano
            try:
                from .scripts.dp_processor import (
    procesar_archivo_datos,
    format_separator_for_storage,
    separator_human_label,
)
                
                resultado = procesar_archivo_datos(
                    archivo_path=analisis.archivo_datos.path,
                    nombre=analisis.nombre,
                    separador=analisis.separador,
                    decimal=analisis.decimal,
                    codificacion=analisis.codificacion,
                    mostrar_temperatura=analisis.mostrar_temperatura,
                    mostrar_leak=analisis.mostrar_leak,
                    mostrar_heater=analisis.mostrar_heater,
                    mostrar_overview=analisis.mostrar_overview
                )
                
                formato_detectado = resultado.get('formato_detectado')
                if formato_detectado:
                    sep_storage = formato_detectado.get('separador')
                    dec_storage = formato_detectado.get('decimal')
                    if sep_storage:
                        analisis.separador = sep_storage
                    if dec_storage:
                        analisis.decimal = dec_storage
                    if formato_detectado.get('automatico'):
                        descripcion = formato_detectado.get('descripcion')
                        if not descripcion:
                            if sep_storage == '\\t':
                                descripcion = 'tabulador (\t)'
                            elif sep_storage == ';':
                                descripcion = 'punto y coma (;)'
                            elif sep_storage == ',':
                                descripcion = 'coma (,)'
                            elif sep_storage == '|':
                                descripcion = 'barra vertical (|)'
                            elif sep_storage:
                                descripcion = f"separador '{sep_storage}'"
                            else:
                                descripcion = 'formato especificado'
                        messages.info(
                            request,
                            f"Formato detectado automaticamente: {descripcion} y decimal '{formato_detectado.get('decimal', analisis.decimal)}'."
                        )

                if resultado.get('exito'):
                    # Guardar archivos generados
                    archivos = resultado.get('archivos_generados', {})
                    
                    if 'csv' in archivos:
                        analisis.archivo_csv_limpio.save(
                            f"{analisis.nombre}__clean.csv",
                            archivos['csv']
                        )
                    
                    if 'temperatura' in archivos:
                        analisis.archivo_temperatura.save(
                            f"{analisis.nombre}__temperatura.png",
                            archivos['temperatura']
                        )
                    
                    if 'leak' in archivos:
                        analisis.archivo_leak.save(
                            f"{analisis.nombre}__leak.png",
                            archivos['leak']
                        )
                    
                    if 'heater' in archivos:
                        analisis.archivo_heater.save(
                            f"{analisis.nombre}__heater.png",
                            archivos['heater']
                        )
                    
                    if 'overview' in archivos:
                        analisis.archivo_overview.save(
                            f"{analisis.nombre}__overview.png",
                            archivos['overview']
                        )
                    
                    # Actualizar estadisticas
                    analisis.duracion_minutos = resultado.get('duracion_minutos')
                    analisis.num_muestras = resultado.get('num_muestras')
                    analisis.columnas_detectadas = ', '.join(resultado.get('columnas_detectadas', []))
                    analisis.estado = DpAnalisisDatos.Estado.COMPLETADO
                    analisis.procesado_en = timezone.now()
                    
                    messages.success(request, f'Analisis "{analisis.nombre}" procesado correctamente.')
                else:
                    analisis.estado = DpAnalisisDatos.Estado.ERROR
                    analisis.mensaje_error = resultado.get('error', 'Error desconocido')
                    messages.error(request, f'Error procesando el analisis: {analisis.mensaje_error}')
                
                analisis.save()
                
            except Exception as e:
                analisis.estado = DpAnalisisDatos.Estado.ERROR
                analisis.mensaje_error = str(e)
                analisis.save()
                messages.error(request, f'Error procesando el analisis: {str(e)}')
            
            return redirect('sigmadp:detalle_analisis', pk=analisis.pk)
    else:
        form = DpAnalisisDatosForm()

    selected_solicitante = ''
    selected_solicitud = ''
    if form.is_bound:
        selected_solicitante = form.data.get('solicitante', '') or ''
        selected_solicitud = form.data.get('solicitud_termica', '') or ''
    else:
        initial_data = getattr(form, 'initial', {})
        initial_user = _coerce_to_int(initial_data.get('solicitante'))
        initial_solicitud = _coerce_to_int(initial_data.get('solicitud_termica'))
        if initial_user is None and getattr(form.instance, 'solicitud_termica_id', None):
            initial_user = form.instance.solicitud_termica.solicitante_id
        if initial_solicitud is None and getattr(form.instance, 'solicitud_termica_id', None):
            initial_solicitud = form.instance.solicitud_termica_id
        if initial_user is not None:
            selected_solicitante = str(initial_user)
        if initial_solicitud is not None:
            selected_solicitud = str(initial_solicitud)

    context = {
        'form': form,
        'solicitantes': solicitantes,
        'solicitudes': solicitudes,
        'selected_solicitante': selected_solicitante,
        'selected_solicitud': selected_solicitud,
        'selector_disponible': solicitantes.exists() if hasattr(solicitantes, 'exists') else bool(solicitantes),
    }
    return render(request, 'sigmadp/crear_analisis_datos.html', context)


@login_required_dtf
def previsualizar_archivo(request):
    """Previsualizar archivo de datos y permitir guardar como analisis"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmadp:panel_usuario')

    solicitantes, solicitudes = _get_selector_datos_solicitudes()
    if hasattr(solicitantes, 'exists'):
        selector_disponible = solicitantes.exists()
    else:
        selector_disponible = bool(solicitantes)

    selected_solicitante = request.POST.get('solicitante', '') if request.method == 'POST' else ''
    selected_solicitud = request.POST.get('solicitud_termica', '') if request.method == 'POST' else ''

    base_context = {
        'solicitantes': solicitantes,
        'solicitudes': solicitudes,
        'selector_disponible': selector_disponible,
        'selected_solicitante': selected_solicitante,
        'selected_solicitud': selected_solicitud,
        'nombre_sugerido': '',
    }

    if request.method == 'GET':
        return render(request, 'sigmadp/previsualizar_archivo_correcto.html', base_context)

    if 'guardar_analisis' in request.POST:
        return _guardar_analisis_desde_preview(request)

    archivo = request.FILES.get('archivo_datos')
    if not archivo:
        context = dict(base_context)
        context['error'] = 'No se recibi archivo'
        return render(request, 'sigmadp/previsualizar_archivo_correcto.html', context)

    try:
        from .utils_detect import detect_and_preview

        props = detect_and_preview(archivo)
        info_archivo = {
            'nombre': getattr(archivo, 'name', 'archivo'),
            'tamao': getattr(archivo, 'size', 0),
            'filas_totales': props['rows'],
            'columnas': props['ncols'],
            'separador_detectado': props['separator'],
            'decimal_detectado': props['decimal'],
            'auto_detectado': True,
        }

        import tempfile

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{archivo.name}")
        for chunk in archivo.chunks():
            temp_file.write(chunk)
        temp_file.close()

        request.session['archivo_temporal'] = temp_file.name
        request.session['props_detectadas'] = props
        request.session['archivo_nombre_original'] = info_archivo['nombre']

        context = dict(base_context)
        context.update({
            'info_archivo': info_archivo,
            'columnas': props['columns'],
            'datos_tabla': props['preview_rows'],
            'props_detectadas': props,
            'nombre_sugerido': Path(info_archivo['nombre']).stem or info_archivo['nombre'],
        })

        return render(request, 'sigmadp/previsualizar_archivo_correcto.html', context)

    except Exception as exc:
        context = dict(base_context)
        context['error'] = f'Error leyendo el archivo: {str(exc)}'
        return render(request, 'sigmadp/previsualizar_archivo_correcto.html', context)


def _guardar_analisis_desde_preview(request):
    """Guardar analisis desde la previsualizacin"""
    try:
        archivo_temporal_path = request.session.get('archivo_temporal')
        props_detectadas = request.session.get('props_detectadas', {})
        original_name = request.session.get('archivo_nombre_original')

        solicitante_id = _coerce_to_int(request.POST.get('solicitante'))
        solicitud_id = _coerce_to_int(request.POST.get('solicitud_termica'))

        if not solicitud_id:
            messages.error(request, 'Selecciona la solicitud asociada antes de guardar el analisis.')
            return redirect('sigmadp:previsualizar_archivo')

        solicitud = (
            DpSolicitudTermica.objects.select_related('solicitante')
            .filter(pk=solicitud_id)
            .first()
        )
        if not solicitud:
            messages.error(request, 'No se encontr la solicitud seleccionada. Intntalo de nuevo.')
            return redirect('sigmadp:previsualizar_archivo')

        if solicitante_id and solicitud.solicitante_id != solicitante_id:
            messages.error(request, 'La solicitud elegida no pertenece al usuario seleccionado.')
            return redirect('sigmadp:previsualizar_archivo')

        if not archivo_temporal_path or not os.path.exists(archivo_temporal_path):
            messages.error(request, 'No se encontr el archivo de datos. Por favor, vuelve a cargar el archivo.')
            return redirect('sigmadp:previsualizar_archivo')

        nombre = (request.POST.get('nombre_analisis', '') or '').strip()
        descripcion = (request.POST.get('descripcion_analisis', '') or '').strip()

        base_name = original_name or os.path.basename(archivo_temporal_path)
        if original_name is None and '_' in base_name:
            base_name = base_name.split('_', 1)[-1]
        sugerido = Path(base_name).stem or base_name or f'Analisis DP-T{solicitud.pk}'
        if not nombre:
            nombre = sugerido

        analisis = DpAnalisisDatos(
            nombre=nombre,
            descripcion=descripcion,
            tecnico=request.user,
            solicitud_termica=solicitud,
            estado=DpAnalisisDatos.Estado.PROCESANDO,
            separador=props_detectadas.get('separator', '	'),
            decimal=props_detectadas.get('decimal', ','),
            codificacion=props_detectadas.get('encoding', 'cp1252'),
            mostrar_temperatura=True,
            mostrar_leak=True,
            mostrar_heater=True,
            mostrar_overview=True,
        )

        nombre_archivo = base_name.lower()
        extension = Path(nombre_archivo).suffix.lower()
        if extension == '.csv':
            analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.CSV
        elif extension == '.tsv':
            analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.TSV
        elif extension == '.dat':
            analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.DAT
        else:
            analisis.tipo_archivo = DpAnalisisDatos.TipoArchivo.TXT

        from django.core.files import File

        with open(archivo_temporal_path, 'rb') as temp_file:
            analisis.archivo_datos.save(base_name, File(temp_file), save=True)

        try:
            from .scripts.dp_processor import procesar_archivo_datos

            resultado = procesar_archivo_datos(
                archivo_path=analisis.archivo_datos.path,
                nombre=analisis.nombre,
                separador=analisis.separador,
                decimal=analisis.decimal,
                codificacion=analisis.codificacion,
                mostrar_temperatura=analisis.mostrar_temperatura,
                mostrar_leak=analisis.mostrar_leak,
                mostrar_heater=analisis.mostrar_heater,
                mostrar_overview=analisis.mostrar_overview,
            )

            if resultado.get('exito'):
                formato_detectado = resultado.get('formato_detectado', {})
                if formato_detectado:
                    analisis.separador = formato_detectado.get('separador', analisis.separador)
                    analisis.decimal = formato_detectado.get('decimal', analisis.decimal)

                archivos_generados = resultado.get('archivos_generados', {})
                if 'csv' in archivos_generados:
                    analisis.archivo_csv_limpio.save(
                        f"{analisis.nombre}_clean.csv",
                        archivos_generados['csv'],
                    )
                if 'temperatura' in archivos_generados:
                    analisis.archivo_temperatura.save(
                        f"{analisis.nombre}_temperatura.png",
                        archivos_generados['temperatura'],
                    )
                if 'leak' in archivos_generados:
                    analisis.archivo_leak.save(
                        f"{analisis.nombre}_leak.png",
                        archivos_generados['leak'],
                    )
                if 'heater' in archivos_generados:
                    analisis.archivo_heater.save(
                        f"{analisis.nombre}_heater.png",
                        archivos_generados['heater'],
                    )
                if 'overview' in archivos_generados:
                    analisis.archivo_overview.save(
                        f"{analisis.nombre}_overview.png",
                        archivos_generados['overview'],
                    )

                analisis.duracion_minutos = resultado.get('duracion_minutos')
                analisis.num_muestras = resultado.get('num_muestras')
                analisis.columnas_detectadas = ', '.join(resultado.get('columnas_detectadas', []))
                analisis.estado = DpAnalisisDatos.Estado.COMPLETADO
                analisis.procesado_en = timezone.now()

                descripcion_formato = formato_detectado.get('descripcion', analisis.separador)
                mensaje = (
                    f'Analisis "{analisis.nombre}" procesado correctamente '
                    f'y asociado a DP-T#{solicitud.pk}. '
                    f'Separador detectado: {descripcion_formato}, '
                    f'Decimal: {analisis.decimal}, '
                )
                if analisis.duracion_minutos is not None:
                    mensaje += f'Duracion: {analisis.duracion_minutos:.1f} min, '
                mensaje += f'Muestras: {analisis.num_muestras or "-"}'
                messages.success(request, mensaje)
            else:
                analisis.estado = DpAnalisisDatos.Estado.ERROR
                analisis.mensaje_error = resultado.get('error', 'Error desconocido')
                messages.error(request, f'Error procesando el analisis: {analisis.mensaje_error}')

            analisis.save()

        except Exception as exc:
            analisis.estado = DpAnalisisDatos.Estado.ERROR
            analisis.mensaje_error = str(exc)
            analisis.save()
            messages.error(request, f'Error procesando el analisis: {str(exc)}')

        try:
            if archivo_temporal_path and os.path.exists(archivo_temporal_path):
                os.unlink(archivo_temporal_path)
        finally:
            request.session.pop('archivo_temporal', None)
            request.session.pop('props_detectadas', None)
            request.session.pop('archivo_nombre_original', None)

        return redirect('sigmadp:detalle_analisis', pk=analisis.pk)

    except Exception as exc:
        try:
            temp_path = request.session.pop('archivo_temporal', None)
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            request.session.pop('props_detectadas', None)
            request.session.pop('archivo_nombre_original', None)
        except Exception:
            pass

        messages.error(request, f'Error guardando el analisis: {str(exc)}')
        return redirect('sigmadp:previsualizar_archivo')


@login_required_dtf
def detalle_analisis(request, pk):
    """Detalle de un analisis de datos"""
    analisis = get_object_or_404(
        DpAnalisisDatos.objects.select_related('solicitud_termica__solicitante'),
        pk=pk,
    )

    es_solicitante = (
        analisis.solicitud_termica
        and analisis.solicitud_termica.solicitante_id == request.user.id
    )
    es_tecnico_propietario = analisis.tecnico_id == request.user.id or request.user.is_superuser

    if not es_solicitante and not es_tecnico_propietario:
        messages.error(request, "No tienes permisos para acceder a este analisis.")
        if is_tecnico_responsable(request.user):
            return redirect('sigmadp:panel_tecnico')
        return redirect('sigmadp:panel_usuario')

    context = {
        'analisis': analisis,
        'graficas_disponibles': analisis.get_graficas_disponibles(),
        'es_solicitante': es_solicitante,
    }
    return render(request, 'sigmadp/detalle_analisis.html', context)


@login_required_dtf
def lista_analisis(request):
    """Lista de analisis de datos del tecnico"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmadp:panel_usuario')
    
    solicitantes, solicitudes = _get_selector_datos_solicitudes()
    analisis_list = DpAnalisisDatos.objects.filter(tecnico=request.user).order_by('-creado_en')
    
    context = {
        'analisis_list': analisis_list,
    }
    return render(request, 'sigmadp/lista_analisis.html', context)


@login_required_dtf
def indicadores_calidad(request):
    """Vista para mostrar indicadores de calidad I1 e I2"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmadp:panel_usuario')
    
    solicitantes, solicitudes = _get_selector_datos_solicitudes()
    # Obtener todas las solicitudes del tecnico
    solicitudes = DpSolicitud.objects.filter(tecnico_responsable=request.user).order_by('-creado_en')
    
    # Obtener indicadores para cada solicitud
    indicadores_data = []
    for solicitud in solicitudes:
        indicador, created = DpIndicadorCalidad.objects.get_or_create(
            solicitud=solicitud,
            defaults={'fecha_recepcion': solicitud.creado_en}
        )
        
        # Si se creo un nuevo indicador, actualizar las fechas
        if created:
            indicador.fecha_recepcion = solicitud.creado_en
            if solicitud.estado == DpSolicitud.Estado.FINALIZADA:
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
    promedio_i1 = DpIndicadorCalidad.obtener_promedio_i1()
    promedio_i2 = DpIndicadorCalidad.obtener_promedio_i2()
    
    # Estadisticas generales
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
    
    return render(request, 'sigmadp/indicadores_calidad.html', context)


@login_required_dtf
def actualizar_indicador(request, solicitud_id):
    """Vista para actualizar fechas de un indicador especifico"""
    if not is_tecnico_responsable(request.user):
        messages.error(request, "No tienes permisos para acceder a esta funcionalidad.")
        return redirect('sigmadp:panel_usuario')
    
    solicitantes, solicitudes = _get_selector_datos_solicitudes()
    solicitud = get_object_or_404(DpSolicitud, id=solicitud_id, tecnico_responsable=request.user)
    
    if request.method == 'POST':
        indicador, created = DpIndicadorCalidad.objects.get_or_create(
            solicitud=solicitud,
            defaults={'fecha_recepcion': solicitud.creado_en}
        )
        
        # Actualizar fechas segun el formulario
        fecha_finalizacion = request.POST.get('fecha_finalizacion_analisis')
        fecha_entrega = request.POST.get('fecha_entrega_informe')
        
        if fecha_finalizacion:
            from datetime import datetime
            try:
                indicador.fecha_finalizacion_analisis = datetime.fromisoformat(fecha_finalizacion)
            except ValueError:
                messages.error(request, 'Formato de fecha de finalizacion invalido.')
                return redirect('sigmadp:indicadores_calidad')
        
        if fecha_entrega:
            from datetime import datetime
            try:
                indicador.fecha_entrega_informe = datetime.fromisoformat(fecha_entrega)
            except ValueError:
                messages.error(request, 'Formato de fecha de entrega invalido.')
                return redirect('sigmadp:indicadores_calidad')
        
        # Actualizar indicadores calculados
        indicador.actualizar_indicadores()
        
        messages.success(request, f'Indicadores actualizados para la solicitud {solicitud.material}.')
        return redirect('sigmadp:indicadores_calidad')
    
    return redirect('sigmadp:indicadores_calidad')


