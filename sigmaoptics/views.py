from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import OpticsSolicitud, OpticsMuestra, OpticsResultado, OpticsAnalisisDatos
from .forms import (
    OpticsSolicitudForm, OpticsMuestraFormSet, 
    OpticsResultadoForm, OpticsSolicitudTecnicoForm, OpticsAnalisisDatosForm
)
from core.roles import is_optics_tech, user_can_access_dtf
from dtf.decorators import dtf_required


def is_optics_technician(user):
    """Verifica si el usuario es técnico de óptica"""
    return user.is_authenticated and (user.is_superuser or is_optics_tech(user))


@dtf_required
def solicitud_create(request):
    """Crear nueva solicitud de análisis óptico"""
    if not user_can_access_dtf(request.user):
        messages.error(request, "No tienes permisos para crear solicitudes.")
        return redirect("dtf:dashboard")
    
    if request.method == 'POST':
        form = OpticsSolicitudForm(request.POST)
        formset = OpticsMuestraFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                solicitud = form.save(commit=False)
                solicitud.solicitante = request.user
                solicitud.save()
                
                # Guardar muestras
                formset.instance = solicitud
                formset.save()
                
                messages.success(request, f"Solicitud OPT-{solicitud.id} creada exitosamente.")
                return redirect("sigmaoptics:solicitud_detail", pk=solicitud.pk)
            except Exception as e:
                messages.error(request, f"Error al crear la solicitud: {str(e)}")
        else:
            # Mostrar errores específicos
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"Error en {field}: {error}")
            
            if not formset.is_valid():
                for i, form_errors in enumerate(formset.errors):
                    for field, errors in form_errors.items():
                        for error in errors:
                            messages.error(request, f"Error en muestra {i+1}, {field}: {error}")
    else:
        form = OpticsSolicitudForm()
        formset = OpticsMuestraFormSet()
    
    return render(request, 'sigmaoptics/solicitud_form.html', {
        'form': form,
        'formset': formset
    })


@dtf_required
def solicitud_detail(request, pk):
    """Detalle de solicitud óptica"""
    solicitud = get_object_or_404(OpticsSolicitud, pk=pk)
    
    # Verificar permisos
    if not (solicitud.solicitante == request.user or is_optics_technician(request.user) or request.user.is_staff):
        messages.error(request, "No tienes permisos para ver esta solicitud.")
        return redirect("sigmaoptics:solicitud_list")
    
    muestras = solicitud.muestras.all()
    resultados = solicitud.resultados.all()
    
    context = {
        'solicitud': solicitud,
        'muestras': muestras,
        'resultados': resultados,
        'is_technician': is_optics_technician(request.user),
        'can_edit': solicitud.solicitante == request.user and solicitud.estado == OpticsSolicitud.Estado.PENDIENTE,
        'can_manage': is_optics_technician(request.user) or request.user.is_staff,
    }
    
    return render(request, 'sigmaoptics/solicitud_detail.html', context)


@dtf_required
def solicitud_list(request):
    """Lista de solicitudes ópticas"""
    if not user_can_access_dtf(request.user):
        messages.error(request, "No tienes permisos para ver las solicitudes.")
        return redirect("dtf:dashboard")
    
    # Filtrar solicitudes según el usuario
    if is_optics_technician(request.user) or request.user.is_staff:
        # Técnicos y staff ven todas las solicitudes
        solicitudes = OpticsSolicitud.objects.all()
    else:
        # Usuarios normales solo ven sus propias solicitudes
        solicitudes = OpticsSolicitud.objects.filter(solicitante=request.user)
    
    # Filtros
    estado_filter = request.GET.get('estado')
    if estado_filter:
        solicitudes = solicitudes.filter(estado=estado_filter)
    
    tipo_filter = request.GET.get('medidas_realizar')
    if tipo_filter:
        solicitudes = solicitudes.filter(medidas_realizar=tipo_filter)
    
    # Búsqueda
    search = request.GET.get('search')
    if search:
        solicitudes = solicitudes.filter(
            Q(material__icontains=search) |
            Q(solicitante__first_name__icontains=search) |
            Q(solicitante__last_name__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(solicitudes.order_by('-creado_en'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'estado_filter': estado_filter,
        'tipo_filter': tipo_filter,
        'search': search,
        'is_technician': is_optics_technician(request.user),
    }
    
    return render(request, 'sigmaoptics/solicitud_list.html', context)


@dtf_required
@require_POST
def solicitud_accept(request, pk):
    """Aceptar solicitud óptica"""
    if not is_optics_technician(request.user):
        messages.error(request, "No tienes permisos para aceptar solicitudes.")
        return redirect("sigmaoptics:solicitud_list")
    
    solicitud = get_object_or_404(OpticsSolicitud, pk=pk)
    
    if solicitud.estado != OpticsSolicitud.Estado.PENDIENTE:
        messages.error(request, "Solo se pueden aceptar solicitudes pendientes.")
        return redirect("sigmaoptics:solicitud_detail", pk=pk)
    
    solicitud.estado = OpticsSolicitud.Estado.ACEPTADA
    solicitud.tecnico_responsable = request.user
    solicitud.aceptado_en = timezone.now()
    solicitud.save()
    
    messages.success(request, f"Solicitud OPT-{solicitud.id} aceptada exitosamente.")
    return redirect("sigmaoptics:solicitud_detail", pk=pk)


@dtf_required
@require_POST
def solicitud_reject(request, pk):
    """Rechazar solicitud óptica"""
    if not is_optics_technician(request.user):
        messages.error(request, "No tienes permisos para rechazar solicitudes.")
        return redirect("sigmaoptics:solicitud_list")
    
    solicitud = get_object_or_404(OpticsSolicitud, pk=pk)
    
    if solicitud.estado != OpticsSolicitud.Estado.PENDIENTE:
        messages.error(request, "Solo se pueden rechazar solicitudes pendientes.")
        return redirect("sigmaoptics:solicitud_detail", pk=pk)
    
    solicitud.estado = OpticsSolicitud.Estado.RECHAZADA
    solicitud.tecnico_responsable = request.user
    solicitud.save()
    
    messages.success(request, f"Solicitud OPT-{solicitud.id} rechazada.")
    return redirect("sigmaoptics:solicitud_detail", pk=pk)


@dtf_required
@require_POST
def solicitud_start(request, pk):
    """Iniciar trabajo en solicitud óptica"""
    if not is_optics_technician(request.user):
        messages.error(request, "No tienes permisos para iniciar trabajos.")
        return redirect("sigmaoptics:solicitud_list")
    
    solicitud = get_object_or_404(OpticsSolicitud, pk=pk)
    
    if solicitud.estado != OpticsSolicitud.Estado.ACEPTADA:
        messages.error(request, "Solo se pueden iniciar solicitudes aceptadas.")
        return redirect("sigmaoptics:solicitud_detail", pk=pk)
    
    solicitud.estado = OpticsSolicitud.Estado.EN_CURSO
    solicitud.save()
    
    messages.success(request, f"Trabajo iniciado en solicitud OPT-{solicitud.id}.")
    return redirect("sigmaoptics:solicitud_detail", pk=pk)


@dtf_required
@require_POST
def solicitud_finish(request, pk):
    """Finalizar solicitud óptica"""
    if not is_optics_technician(request.user):
        messages.error(request, "No tienes permisos para finalizar trabajos.")
        return redirect("sigmaoptics:solicitud_list")
    
    solicitud = get_object_or_404(OpticsSolicitud, pk=pk)
    
    if solicitud.estado != OpticsSolicitud.Estado.EN_CURSO:
        messages.error(request, "Solo se pueden finalizar solicitudes en curso.")
        return redirect("sigmaoptics:solicitud_detail", pk=pk)
    
    solicitud.estado = OpticsSolicitud.Estado.FINALIZADA
    solicitud.finalizado_en = timezone.now()
    solicitud.save()
    
    messages.success(request, f"Solicitud OPT-{solicitud.id} finalizada.")
    return redirect("sigmaoptics:solicitud_detail", pk=pk)


@dtf_required
def resultado_upload(request, pk):
    """Subir resultado de análisis óptico"""
    if not is_optics_technician(request.user):
        messages.error(request, "No tienes permisos para subir resultados.")
        return redirect("sigmaoptics:solicitud_list")
    
    solicitud = get_object_or_404(OpticsSolicitud, pk=pk)
    
    if request.method == 'POST':
        form = OpticsResultadoForm(request.POST, request.FILES)
        if form.is_valid():
            resultado = form.save(commit=False)
            resultado.solicitud = solicitud
            resultado.creado_por = request.user
            resultado.save()
            
            messages.success(request, f"Resultado {resultado.codigo_informe} subido exitosamente.")
            return redirect("sigmaoptics:solicitud_detail", pk=pk)
    else:
        form = OpticsResultadoForm()
    
    return render(request, 'sigmaoptics/resultado_form.html', {
        'form': form,
        'solicitud': solicitud
    })


@dtf_required
def panel_tecnico(request):
    """Panel del técnico de óptica"""
    if not is_optics_technician(request.user):
        messages.error(request, "No tienes permisos para acceder al panel técnico.")
        return redirect("dtf:dashboard")
    
    # Estadísticas
    total_solicitudes = OpticsSolicitud.objects.count()
    solicitudes_pendientes = OpticsSolicitud.objects.filter(estado=OpticsSolicitud.Estado.PENDIENTE).count()
    solicitudes_en_curso = OpticsSolicitud.objects.filter(estado=OpticsSolicitud.Estado.EN_CURSO).count()
    solicitudes_finalizadas = OpticsSolicitud.objects.filter(estado=OpticsSolicitud.Estado.FINALIZADA).count()
    
    # Solicitudes recientes
    solicitudes_recientes = OpticsSolicitud.objects.order_by('-creado_en')[:10]
    
    context = {
        'total_solicitudes': total_solicitudes,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_en_curso': solicitudes_en_curso,
        'solicitudes_finalizadas': solicitudes_finalizadas,
        'solicitudes_recientes': solicitudes_recientes,
    }
    
    return render(request, 'sigmaoptics/panel_tecnico.html', context)


@dtf_required
def get_muestras_form(request):
    """AJAX: Obtener formulario de muestras dinámicamente"""
    if request.method == 'POST':
        numero_muestras = int(request.POST.get('numero_muestras', 1))
        
        # Crear formset con el número de muestras especificado
        formset = OpticsMuestraFormSet(queryset=OpticsMuestra.objects.none())
        formset.extra = numero_muestras
        
        # Renderizar el formset
        from django.template.loader import render_to_string
        html = render_to_string('sigmaoptics/partials/muestras_formset.html', {
            'formset': formset
        })
        
        return JsonResponse({'html': html})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@dtf_required
@user_passes_test(is_optics_technician)
def crear_analisis_datos(request):
    """Crear nuevo análisis de datos ópticos"""
    if request.method == 'POST':
        form = OpticsAnalisisDatosForm(request.POST, request.FILES)
        if form.is_valid():
            analisis = form.save(commit=False)
            analisis.tecnico = request.user
            
            # Detectar tipo de archivo basado en la extensión
            archivo = request.FILES.get('archivo_datos')
            if archivo:
                nombre_archivo = archivo.name.lower()
                if nombre_archivo.endswith('.csv'):
                    analisis.tipo_archivo = OpticsAnalisisDatos.TipoArchivo.CSV
                elif nombre_archivo.endswith('.tsv'):
                    analisis.tipo_archivo = OpticsAnalisisDatos.TipoArchivo.TSV
                elif nombre_archivo.endswith('.dat'):
                    analisis.tipo_archivo = OpticsAnalisisDatos.TipoArchivo.DAT
                else:
                    analisis.tipo_archivo = OpticsAnalisisDatos.TipoArchivo.TXT
            
            analisis.save()
            
            # Procesar el archivo en segundo plano
            try:
                from .scripts.optics_processor import procesar_archivo_optics
                
                resultado = procesar_archivo_optics(
                    archivo_path=analisis.archivo_datos.path,
                    nombre=analisis.nombre,
                    separador=analisis.separador,
                    decimal=analisis.decimal,
                    codificacion=analisis.codificacion,
                    mostrar_espectro=analisis.mostrar_espectro,
                    mostrar_transmitancia=analisis.mostrar_transmitancia,
                    mostrar_absorbancia=analisis.mostrar_absorbancia,
                    mostrar_overview=analisis.mostrar_overview,
                )
                
                if resultado.get('exito'):
                    # Guardar archivos generados
                    archivos = resultado.get('archivos_generados', {})
                    
                    if 'csv' in archivos:
                        analisis.archivo_csv_limpio.save(
                            f"{analisis.nombre}__clean.csv",
                            archivos['csv']
                        )
                    
                    if 'espectro' in archivos:
                        analisis.archivo_espectro.save(
                            f"{analisis.nombre}__espectro.png",
                            archivos['espectro']
                        )
                    
                    if 'transmitancia' in archivos:
                        analisis.archivo_transmitancia.save(
                            f"{analisis.nombre}__transmitancia.png",
                            archivos['transmitancia']
                        )
                    
                    if 'absorbancia' in archivos:
                        analisis.archivo_absorbancia.save(
                            f"{analisis.nombre}__absorbancia.png",
                            archivos['absorbancia']
                        )
                    
                    if 'overview' in archivos:
                        analisis.archivo_overview.save(
                            f"{analisis.nombre}__overview.png",
                            archivos['overview']
                        )
                    
                    # Actualizar estadísticas
                    analisis.duracion_minutos = resultado.get('duracion_minutos')
                    analisis.num_muestras = resultado.get('num_muestras')
                    analisis.columnas_detectadas = ', '.join(resultado.get('columnas_detectadas', []))
                    analisis.estado = OpticsAnalisisDatos.Estado.COMPLETADO
                    analisis.procesado_en = timezone.now()
                    
                    analisis.save()
                    messages.success(request, f"Análisis '{analisis.nombre}' procesado exitosamente.")
                    return redirect('sigmaoptics:analisis_detail', pk=analisis.pk)
                else:
                    analisis.estado = OpticsAnalisisDatos.Estado.ERROR
                    analisis.save()
                    messages.error(request, f"Error al procesar el archivo: {resultado.get('error', 'Error desconocido')}")
            except Exception as e:
                analisis.estado = OpticsAnalisisDatos.Estado.ERROR
                analisis.save()
                messages.error(request, f"Error al procesar el archivo: {str(e)}")
            
            return redirect('sigmaoptics:analisis_list')
    else:
        form = OpticsAnalisisDatosForm()
    
    context = {
        'form': form,
        'title': 'Crear Análisis de Datos Ópticos'
    }
    return render(request, 'sigmaoptics/crear_analisis_datos.html', context)


@dtf_required
@user_passes_test(is_optics_technician)
def analisis_list(request):
    """Lista de análisis de datos ópticos"""
    analisis_list = OpticsAnalisisDatos.objects.filter(tecnico=request.user).order_by('-creado_en')
    
    # Filtros
    estado = request.GET.get('estado')
    if estado:
        analisis_list = analisis_list.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(analisis_list, 10)
    page_number = request.GET.get('page')
    analisis = paginator.get_page(page_number)
    
    context = {
        'analisis': analisis,
        'estados': OpticsAnalisisDatos.Estado.choices,
        'estado_actual': estado
    }
    return render(request, 'sigmaoptics/analisis_list.html', context)


@dtf_required
@user_passes_test(is_optics_technician)
def analisis_detail(request, pk):
    """Detalle de análisis de datos ópticos"""
    analisis = get_object_or_404(OpticsAnalisisDatos, pk=pk, tecnico=request.user)
    
    context = {
        'analisis': analisis
    }
    return render(request, 'sigmaoptics/analisis_detail.html', context)
