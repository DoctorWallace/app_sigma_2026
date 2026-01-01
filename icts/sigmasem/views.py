from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from pathlib import Path
import json
import os
import uuid
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from icts.models import AccessProposal
from .models import SEMAnalysis, SEMSample


ALLOWED_BROWSE_ROOTS = [
    Path(path).resolve(strict=False)
    for path in getattr(settings, "SIGMASEM_ALLOWED_BROWSE_ROOTS", [])
]


def _resolve_browse_path(raw_path: str) -> tuple[Path, Path]:
    """Valida que la ruta esté dentro de los directorios permitidos."""
    if not ALLOWED_BROWSE_ROOTS:
        raise ValueError("No hay rutas configuradas para explorar archivos.")

    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = ALLOWED_BROWSE_ROOTS[0] / candidate

    resolved_candidate = candidate.resolve(strict=False)

    for root in ALLOWED_BROWSE_ROOTS:
        root_resolved = Path(root).resolve(strict=False)
        if root_resolved == resolved_candidate or root_resolved in resolved_candidate.parents:
            return resolved_candidate, root_resolved

    raise ValueError("Ruta fuera de los directorios permitidos.")
from .forms import SEMAnalysisForm, SEMSampleForm, SampleSelectionForm, AddSampleForm


def is_sem_technician(user):
    """Verifica si el usuario es técnico SEM/FIB"""
    from icts.auth_utils import TECH_SEM_GROUPS, get_normalized_user_groups, user_in_groups
    
    if not user.is_authenticated:
        return False
    
    # Superusuarios siempre tienen acceso
    if user.is_superuser:
        return True
    
    # Usar el sistema de roles centralizado
    groups = get_normalized_user_groups(user)
    return user_in_groups(user, TECH_SEM_GROUPS, groups)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def dashboard(request):
    """Dashboard principal para técnicos SEM/FIB"""
    
    # Obtener propuestas aceptadas que incluyan SEM o FIB
    accepted_proposals = AccessProposal.objects.filter(
        status='accepted'
    ).filter(
        Q(facility_sem=True) | Q(facility_sem_fib=True)
    ).order_by('-created_at')
    
    # Estadísticas
    total_analyses = SEMAnalysis.objects.count()
    sem_analyses = SEMAnalysis.objects.filter(analysis_type='sem').count()
    fib_analyses = SEMAnalysis.objects.filter(analysis_type='fib').count()
    
    # Análisis recientes
    recent_analyses = SEMAnalysis.objects.select_related(
        'access_proposal', 'technician'
    ).order_by('-analysis_date')[:10]
    
    context = {
        'accepted_proposals': accepted_proposals,
        'total_analyses': total_analyses,
        'sem_analyses': sem_analyses,
        'fib_analyses': fib_analyses,
        'recent_analyses': recent_analyses,
    }
    
    return render(request, 'sigmasem/dashboard.html', context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def create_analysis(request):
    """Crear nuevo análisis SEM/FIB"""
    
    if request.method == 'POST':
        form = SEMAnalysisForm(request.POST)
        if form.is_valid():
            analysis = form.save(commit=False)
            analysis.technician = request.user
            
            # Obtener información de la propuesta
            proposal = analysis.access_proposal
            analysis.client = f"{proposal.applicant.first_name} {proposal.applicant.last_name}".strip()
            
            # Inicializar muestras vacías
            analysis.samples_data = []
            
            analysis.save()
            messages.success(request, f"Análisis {analysis.registration_number} creado exitosamente.")
            return redirect('icts:sigmasem:analysis_detail', pk=analysis.pk)
    else:
        form = SEMAnalysisForm()
    
    # Obtener propuestas disponibles
    available_proposals = AccessProposal.objects.filter(
        status='accepted'
    ).filter(
        Q(facility_sem=True) | Q(facility_sem_fib=True)
    ).order_by('-created_at')
    
    context = {
        'form': form,
        'available_proposals': available_proposals,
    }
    
    return render(request, 'sigmasem/create_analysis.html', context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def analysis_detail(request, pk):
    """Detalle de un análisis SEM/FIB"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    additional_samples = analysis.additional_samples.all()
    
    context = {
        'analysis': analysis,
        'additional_samples': additional_samples,
    }
    
    return render(request, 'sigmasem/analysis_detail.html', context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def analysis_list(request):
    """Lista de todos los análisis"""
    
    # Filtros
    analysis_type = request.GET.get('type', '')
    search = request.GET.get('search', '')
    
    analyses = SEMAnalysis.objects.select_related(
        'access_proposal', 'technician'
    ).order_by('-analysis_date')
    
    if analysis_type:
        analyses = analyses.filter(analysis_type=analysis_type)
    
    if search:
        analyses = analyses.filter(
            Q(sample_name__icontains=search) |
            Q(sample_identification__icontains=search) |
            Q(client__icontains=search) |
            Q(registration_number__icontains=search)
        )
    
    context = {
        'analyses': analyses,
        'current_type': analysis_type,
        'current_search': search,
    }
    
    return render(request, 'sigmasem/analysis_list.html', context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def add_sample(request, analysis_pk):
    """Agregar muestra adicional a un análisis"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=analysis_pk)
    
    if request.method == 'POST':
        form = SEMSampleForm(request.POST)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.analysis = analysis
            sample.save()
            messages.success(request, "Muestra agregada exitosamente.")
            return redirect('icts:sigmasem:analysis_detail', pk=analysis.pk)
    else:
        form = SEMSampleForm()
    
    context = {
        'form': form,
        'analysis': analysis,
    }
    
    return render(request, 'sigmasem/add_sample.html', context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def browse_files(request):
    """Explorador de archivos para informes"""

    if request.method == 'POST':
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Formato JSON inválido'}, status=400)

        folder_path = (data.get('folder_path') or '').strip()
        if not folder_path:
            return JsonResponse({'error': 'La ruta de la carpeta es obligatoria'}, status=400)

        try:
            target_dir, root_dir = _resolve_browse_path(folder_path)
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        if not target_dir.exists() or not target_dir.is_dir():
            return JsonResponse({'error': 'Carpeta no encontrada'}, status=404)

        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        files = []

        for entry in target_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in image_extensions:
                continue

            stat = entry.stat()
            files.append({
                'name': entry.name,
                'path': str(entry.resolve(strict=False).relative_to(root_dir)),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M')
            })

        return JsonResponse({'files': files})

    return render(request, 'sigmasem/file_browser.html')


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def update_report_files(request, pk):
    """Actualizar archivos del informe"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            files = data.get('files', [])
            
            analysis.report_files = files
            analysis.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def get_proposal_samples(request, proposal_id):
    """Obtener muestras de una propuesta específica"""
    try:
        proposal = get_object_or_404(AccessProposal, pk=proposal_id, status="accepted")
        if not (proposal.facility_sem or proposal.facility_sem_fib):
            raise Http404
        samples = []

        if proposal.facility_data:
            sem_data = proposal.facility_data.get('sem', {})
            for key, value in sem_data.items():
                if 'identification' in key.lower():
                    # Buscar el nombre correspondiente
                    sample_key = key.replace('identification', 'name')
                    sample_name = sem_data.get(sample_key, 'Sin nombre')
                    samples.append({
                        'identification': value,
                        'name': sample_name
                    })

        return JsonResponse({'samples': samples})

    except Http404:
        raise
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def add_samples_to_analysis(request, pk):
    """Añadir muestras a un análisis existente"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    if request.method == 'POST':
        # Procesar muestras seleccionadas de la propuesta
        selected_samples = request.POST.getlist('selected_samples')
        # Procesar nueva muestra añadida
        new_sample_id = request.POST.get('new_sample_id')
        new_sample_name = request.POST.get('new_sample_name')
        new_sample_desc = request.POST.get('new_sample_desc')
        
        # Actualizar muestras del análisis
        if not analysis.samples_data:
            analysis.samples_data = []
        
        # Añadir muestras seleccionadas de la propuesta
        if selected_samples:
            proposal = analysis.access_proposal
            if proposal.facility_data:
                sem_data = proposal.facility_data.get('sem', {})
                for sample_id in selected_samples:
                    # Buscar la muestra en facility_data
                    for key, value in sem_data.items():
                        if 'identification' in key and str(sample_id) in key:
                            sample_key = key.replace('identification', 'name')
                            sample_name = sem_data.get(sample_key, 'Sin nombre')
                            analysis.samples_data.append({
                                'id': sample_id,
                                'identification': value,
                                'name': sample_name,
                                'source': 'proposal'
                            })
        
        # Añadir nueva muestra
        if new_sample_id and new_sample_name:
            analysis.samples_data.append({
                'id': f"new_{len(analysis.samples_data)}",
                'identification': new_sample_id,
                'name': new_sample_name,
                'description': new_sample_desc or '',
                'source': 'session'
            })
        
        analysis.save()
        messages.success(request, "Muestras añadidas exitosamente.")
        return redirect('icts:sigmasem:analysis_detail', pk=analysis.pk)
    
    # Obtener muestras disponibles de la propuesta
    proposal = analysis.access_proposal
    available_samples = []
    if proposal.facility_data:
        sem_data = proposal.facility_data.get('sem', {})
        for key, value in sem_data.items():
            if 'identification' in key:
                sample_id = key.split('_')[-1] if '_' in key else '1'
                sample_key = key.replace('identification', 'name')
                sample_name = sem_data.get(sample_key, 'Sin nombre')
                available_samples.append({
                    'id': sample_id,
                    'identification': value,
                    'name': sample_name
                })
    
    context = {
        'analysis': analysis,
        'available_samples': available_samples,
    }
    
    return render(request, 'sigmasem/add_samples.html', context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def update_session_comments(request, pk):
    """Actualizar comentarios de la sesión"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    if request.method == 'POST':
        comments = request.POST.get('session_comments', '')
        analysis.session_comments = comments
        analysis.save()
        
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': True})
        else:
            messages.success(request, "Comentarios actualizados.")
            return redirect('icts:sigmasem:analysis_detail', pk=analysis.pk)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def finish_session(request, pk):
    """Finalizar sesión de análisis"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    if request.method == 'POST':
        # Marcar sesión como completada
        analysis.session_status = 'completed'
        analysis.completion_date = timezone.now().date()
        analysis.save()
        
        messages.success(request, f"Sesión {analysis.registration_number} finalizada exitosamente.")
        return redirect('icts:sigmasem:analysis_detail', pk=analysis.pk)
    
    context = {
        'analysis': analysis,
    }
    
    return render(request, 'sigmasem/finish_session.html', context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def upload_files(request, pk):
    """Subir archivos mediante drag & drop"""

    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    if request.method == 'POST':
        try:
            uploaded_files = []
            
            # Procesar archivos subidos
            for file_key in request.FILES:
                file = request.FILES[file_key]
                
                # Validar tipo de archivo
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.doc', '.docx']
                file_extension = os.path.splitext(file.name)[1].lower()
                
                if file_extension not in allowed_extensions:
                    continue
                
                # Generar nombre único para el archivo
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                
                # Guardar archivo
                file_path = default_storage.save(f'sem_files/{analysis.registration_number}/{unique_filename}', ContentFile(file.read()))
                
                # Obtener información del archivo
                file_size = file.size
                file_modified = timezone.now()
                
                uploaded_files.append({
                    'name': file.name,
                    'path': file_path,
                    'size': f"{file_size / 1024:.1f} KB",
                    'modified': file_modified.strftime('%d/%m/%Y %H:%M'),
                    'type': 'image' if file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif'] else 'document'
                })
            
            # Actualizar archivos del análisis
            if not analysis.report_files:
                analysis.report_files = []
            
            analysis.report_files.extend(uploaded_files)
            analysis.save()
            
            return JsonResponse({
                'success': True,
                'files': uploaded_files,
                'message': f'{len(uploaded_files)} archivo(s) subido(s) exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def delete_file(request, pk):
    """Eliminar archivo del análisis"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            file_path = data.get('file_path')
            
            if not file_path:
                return JsonResponse({'error': 'Ruta de archivo no proporcionada'}, status=400)
            
            # Eliminar archivo del almacenamiento
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
            
            # Eliminar archivo de la lista
            if analysis.report_files:
                analysis.report_files = [f for f in analysis.report_files if f.get('path') != file_path]
                analysis.save()
            
            return JsonResponse({'success': True, 'message': 'Archivo eliminado exitosamente'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def download_file(request, pk):
    """Descargar archivo del análisis"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    file_path = request.GET.get('path')
    if not file_path:
        return JsonResponse({'error': 'Ruta de archivo no proporcionada'}, status=400)
    
    try:
        if default_storage.exists(file_path):
            file = default_storage.open(file_path)
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
        else:
            return JsonResponse({'error': 'Archivo no encontrado'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sem_technician)
def generate_report_pdf(request, pk):
    """Generar informe PDF del análisis"""
    
    analysis = get_object_or_404(SEMAnalysis, pk=pk)
    
    # Crear respuesta HTTP para el PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="IN-{analysis.analysis_type.upper()}-{analysis.report_code}.pdf"'
    
    # Crear documento PDF
    doc = SimpleDocTemplate(response, pagesize=A4)
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )
    
    normal_style = styles['Normal']
    
    # Título del informe
    story.append(Paragraph(f"INFORME DE ANÁLISIS {analysis.analysis_type.upper()}", title_style))
    story.append(Paragraph(f"Código: {analysis.report_code}", normal_style))
    story.append(Spacer(1, 20))
    
    # Información del análisis
    story.append(Paragraph("INFORMACIÓN DEL ANÁLISIS", heading_style))
    
    analysis_data = [
        ['Código de Registro:', analysis.registration_number],
        ['Tipo de Análisis:', analysis.get_analysis_type_display()],
        ['Fecha de Análisis:', analysis.analysis_date.strftime('%d/%m/%Y') if analysis.analysis_date else 'No especificada'],
        ['Técnico:', f"{analysis.technician.first_name} {analysis.technician.last_name}"],
        ['Cliente:', analysis.client],
        ['Estado de la Sesión:', analysis.get_session_status_display()],
    ]
    
    if analysis.completion_date:
        analysis_data.append(['Fecha de Finalización:', analysis.completion_date.strftime('%d/%m/%Y')])
    
    analysis_table = Table(analysis_data, colWidths=[2*inch, 4*inch])
    analysis_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(analysis_table)
    story.append(Spacer(1, 20))
    
    # Información de la propuesta
    story.append(Paragraph("INFORMACIÓN DE LA PROPUESTA", heading_style))
    
    proposal = analysis.access_proposal
    proposal_data = [
        ['Código de Acceso:', proposal.access_code],
        ['Título del Proyecto:', proposal.title],
        ['Investigador Principal:', f"{proposal.applicant.first_name} {proposal.applicant.last_name}"],
        ['Institución:', getattr(proposal.applicant.icts_profile, 'center', 'No especificada') if hasattr(proposal.applicant, 'icts_profile') and proposal.applicant.icts_profile else 'No especificada'],
        ['Email:', proposal.applicant.email],
    ]
    
    proposal_table = Table(proposal_data, colWidths=[2*inch, 4*inch])
    proposal_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(proposal_table)
    story.append(Spacer(1, 20))
    
    # Muestras analizadas
    story.append(Paragraph("MUESTRAS ANALIZADAS", heading_style))
    
    if analysis.samples_data:
        samples_data = [['Identificación', 'Nombre', 'Origen']]
        for sample in analysis.samples_data:
            samples_data.append([
                sample.get('identification', 'N/A'),
                sample.get('name', 'N/A'),
                'Propuesta' if sample.get('source') == 'proposal' else 'Sesión'
            ])
        
        samples_table = Table(samples_data, colWidths=[2*inch, 2.5*inch, 1.5*inch])
        samples_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(samples_table)
    else:
        story.append(Paragraph("No se registraron muestras para este análisis.", normal_style))
    
    story.append(Spacer(1, 20))
    
    # Comentarios de la sesión
    if analysis.session_comments:
        story.append(Paragraph("COMENTARIOS Y OBSERVACIONES", heading_style))
        story.append(Paragraph(analysis.session_comments, normal_style))
        story.append(Spacer(1, 20))
    
    # Archivos adjuntos
    if analysis.report_files:
        story.append(Paragraph("ARCHIVOS ADJUNTOS", heading_style))
        
        files_data = [['Nombre del Archivo', 'Tipo', 'Tamaño', 'Fecha']]
        for file_info in analysis.report_files:
            files_data.append([
                file_info.get('name', 'N/A'),
                file_info.get('type', 'N/A'),
                file_info.get('size', 'N/A'),
                file_info.get('modified', 'N/A')
            ])
        
        files_table = Table(files_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1.5*inch])
        files_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(files_table)
        story.append(Spacer(1, 20))
        
        # Añadir imágenes al PDF
        image_files = [f for f in analysis.report_files if f.get('type') == 'image']
        if image_files:
            story.append(Paragraph("IMÁGENES DEL ANÁLISIS", heading_style))
            story.append(Paragraph(f"Se encontraron {len(image_files)} archivos de imagen.", normal_style))
            
            for i, image_file in enumerate(image_files[:10]):  # Máximo 10 imágenes
                try:
                    file_path = image_file.get('path')
                    file_name = image_file.get('name', 'Sin nombre')
                    
                    # Debug info
                    story.append(Paragraph(f"<b>Procesando imagen {i+1}:</b> {file_name}", normal_style))
                    story.append(Paragraph(f"Ruta: {file_path}", normal_style))
                    
                    if file_path and default_storage.exists(file_path):
                        # Leer el contenido del archivo
                        with default_storage.open(file_path, 'rb') as image_data:
                            image_content = image_data.read()
                        
                        # Verificar que el archivo no esté vacío
                        file_size = len(image_content)
                        story.append(Paragraph(f"Tamaño del archivo: {file_size} bytes", normal_style))
                        
                        if file_size == 0:
                            story.append(Paragraph(f"<b>Imagen {i+1}:</b> {file_name} (Archivo vacío)", normal_style))
                            story.append(Spacer(1, 10))
                            continue
                        
                        # Crear un archivo temporal en memoria
                        image_buffer = BytesIO(image_content)
                        
                        # Intentar crear la imagen con diferentes configuraciones
                        try:
                            # Primero intentar con tamaño automático
                            img = Image(image_buffer)
                            
                            # Redimensionar si es muy grande
                            if img.drawWidth > 6*inch or img.drawHeight > 4*inch:
                                # Mantener proporción
                                ratio = min(6*inch/img.drawWidth, 4*inch/img.drawHeight)
                                img = Image(image_buffer, width=img.drawWidth*ratio, height=img.drawHeight*ratio)
                            
                            img.hAlign = 'CENTER'
                            
                            story.append(Paragraph(f"<b>Imagen {i+1}:</b> {file_name}", normal_style))
                            story.append(img)
                            story.append(Spacer(1, 10))
                            
                        except Exception as img_error:
                            # Si falla, intentar con tamaño fijo
                            image_buffer.seek(0)  # Resetear el buffer
                            img = Image(image_buffer, width=4*inch, height=3*inch)
                            img.hAlign = 'CENTER'
                            
                            story.append(Paragraph(f"<b>Imagen {i+1}:</b> {file_name}", normal_style))
                            story.append(img)
                            story.append(Spacer(1, 10))
                        
                except Exception as e:
                    # Si hay error con la imagen, continuar con la siguiente
                    story.append(Paragraph(f"<b>Imagen {i+1}:</b> {file_name} (Error al cargar: {str(e)})", normal_style))
                    story.append(Spacer(1, 10))
                    continue
    
    # Pie de página
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Informe generado el {timezone.now().strftime('%d/%m/%Y a las %H:%M')}", 
                          ParagraphStyle('Footer', parent=normal_style, alignment=TA_RIGHT, fontSize=8)))
    
    # Construir PDF
    doc.build(story)
    
    return response
