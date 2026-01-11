from datetime import date
from io import BytesIO
from pathlib import Path
import re
import logging

from django.contrib import messages

logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.db import transaction
from django.db.models import Q, Count, Max
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

User = get_user_model()

from docx import Document
from docx.shared import Inches
from openpyxl import load_workbook

from core.quality_templates import QUALITY_TEMPLATES_ROOT
from icts.auth_utils import TECH_SIMS_GROUPS, get_normalized_user_groups, user_in_groups
from icts.models import AccessProposal
from .forms import (
    SIMSAnnualPlanEntryForm,
    SIMSAnnualPlanYearForm,
    SIMSDocumentForm,
    SIMSEquipmentDocRefForm,
    SIMSEquipmentForm,
    SIMSEquipmentIncidentForm,
    SIMSMaintenanceActivityForm,
    SIMSMaintenanceRecordForm,
    SIMSRecordForm,
    SIMSRecordRemovalForm,
    SIMSReportForm,
    SIMSSparePartInventoryForm,
    SIMSReferenceMaterialForm,
)
from .models import (
    SIMSAnnualPlan,
    SIMSAnnualPlanEntry,
    SIMSAnnualPlanChangeLog,
    SIMSRecord,
    SIMSReport,
    SIMSReportImage,
    SIMSReportFile,
    SIMSDocument,
    SIMSEquipment,
    SIMSEquipmentDocRef,
    SIMSEquipmentIncident,
    SIMSMaintenanceActivity,
    SIMSMaintenanceRecord,
    SIMSSparePartInventory,
    SIMSReferenceMaterial,
)
from .services.quality_indicators import compute_i1_stats


def is_sims_technician(user):
    """Verifica si el usuario es técnico SIMS."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    groups = get_normalized_user_groups(user)
    return user_in_groups(user, TECH_SIMS_GROUPS, groups)


def is_sims_responsable(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    groups = get_normalized_user_groups(user)
    return user_in_groups(
        user,
        {
            "tecnico_responsable_s_sims",
            "tecnicos_responsables_s_sims",
        },
        groups,
    )


def _parse_date(raw_value):
    """Parsear fecha desde string."""
    if not raw_value:
        return None
    try:
        # Intentar formato ISO
        if isinstance(raw_value, str):
            # Limpiar espacios y tomar solo la parte de fecha
            raw_value = raw_value.strip().split()[0] if raw_value.strip() else raw_value.strip()
        return date.fromisoformat(raw_value)
    except (TypeError, ValueError):
        # Intentar otros formatos comunes
        try:
            from datetime import datetime
            # Formato con hora
            if " " in str(raw_value):
                return datetime.strptime(str(raw_value).split()[0], "%Y-%m-%d").date()
            return datetime.strptime(str(raw_value), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None


def _get_sims_technicians_list():
    """Obtener lista de técnicos/responsables SIMS con sus siglas para dropdowns."""
    from icts.models import ICTSUserProfile

    technicians = []

    # Obtener usuarios de los grupos de técnicos SIMS
    sims_groups = Group.objects.filter(name__in=TECH_SIMS_GROUPS)
    sims_users = User.objects.filter(groups__in=sims_groups).distinct()

    for user in sims_users:
        try:
            profile = user.icts_profile
            siglas = profile.user_siglas or ""
        except ICTSUserProfile.DoesNotExist:
            siglas = ""

        # Usar siglas si están disponibles, sino el nombre de usuario
        full_name = user.get_full_name() or user.get_username()

        if siglas:
            label = f"{siglas} ({full_name})"
        else:
            label = full_name

        technicians.append({
            "siglas": siglas,
            "username": user.get_username(),
            "display": label,
        })

    # Ordenar por display
    technicians.sort(key=lambda x: x["display"])

    return technicians


def _filter_records(request):
    # Excluir registros eliminados por defecto
    records = SIMSRecord.objects.filter(is_removed=False).select_related("access_proposal")
    date_from_raw = request.GET.get("date_from")
    date_to_raw = request.GET.get("date_to")
    query = (request.GET.get("q") or "").strip()

    date_from = _parse_date(date_from_raw)
    date_to = _parse_date(date_to_raw)
    if date_from:
        records = records.filter(reception_date__gte=date_from)
    if date_to:
        records = records.filter(reception_date__lte=date_to)
    if query:
        records = records.filter(
            Q(sims_id__icontains=query)
            | Q(request_code__icontains=query)
            | Q(client_name__icontains=query)
            | Q(sample_identification__icontains=query)
        )

    return records, {
        "date_from": date_from_raw or "",
        "date_to": date_to_raw or "",
        "query": query,
    }


def _get_client_name_from_proposal(proposal):
    if not proposal:
        return ""
    applicant = proposal.applicant
    return (applicant.get_full_name() or applicant.get_username()).strip()


def _format_request_code(access_code):
    if not access_code:
        return ""
    return str(access_code).replace("_", "-")


def _get_sims_facility_payload(proposal):
    if not proposal or not isinstance(proposal.facility_data, dict):
        return {}
    payload = proposal.facility_data.get("sims") or {}
    return payload if isinstance(payload, dict) else {}


def _pick_first_sims_sample_value(payload, field_name):
    if not isinstance(payload, dict):
        return ""
    pattern = re.compile(rf"^sims_sample_(\d+)_{re.escape(field_name)}$")
    matches = []
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        match = pattern.match(str(key))
        if not match:
            continue
        try:
            index = int(match.group(1))
        except ValueError:
            index = 0
        matches.append((index, value))
    if not matches:
        return ""
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def _extract_sims_sample_fields(proposal):
    payload = _get_sims_facility_payload(proposal)
    return (
        _pick_first_sims_sample_value(payload, "identification"),
        _pick_first_sims_sample_value(payload, "details"),
    )


def _get_proposal_samples(proposal):
    """Obtener todas las muestras de una propuesta desde facility_data."""
    if not proposal or not isinstance(proposal.facility_data, dict):
        return []
    
    samples = []
    sims_data = proposal.facility_data.get("sims", {})
    
    # Buscar muestras en la estructura de facility_data
    # El formulario guarda: sims_sample_0_identification, sims_sample_0_name, sims_sample_0_details
    # También soportamos el formato antiguo: sample_0_identification (sin prefijo sims_)
    if isinstance(sims_data, dict):
        # Buscar todos los índices de muestras
        sample_indices = set()
        for key in sims_data.keys():
            if isinstance(key, str):
                # Buscar formato nuevo: sims_sample_0_identification
                if key.startswith("sims_sample_") and "_identification" in key:
                    try:
                        # Extraer número: sims_sample_0_identification -> 0
                        idx_str = key.replace("sims_sample_", "").replace("_identification", "")
                        idx = int(idx_str)
                        sample_indices.add(idx)
                    except (ValueError, AttributeError):
                        pass
                # Buscar formato antiguo: sample_0_identification (sin prefijo sims_)
                elif key.startswith("sample_") and "_identification" in key and not key.startswith("sims_sample_"):
                    try:
                        # Extraer número: sample_0_identification -> 0
                        idx_str = key.replace("sample_", "").replace("_identification", "")
                        idx = int(idx_str)
                        sample_indices.add(idx)
                    except (ValueError, AttributeError):
                        pass
        
        # Construir lista de muestras
        for idx in sorted(sample_indices):
            # Intentar primero el formato nuevo (sims_sample_)
            identification = sims_data.get(f"sims_sample_{idx}_identification", "") or sims_data.get(f"sample_{idx}_identification", "")
            name = sims_data.get(f"sims_sample_{idx}_name", "") or sims_data.get(f"sample_{idx}_name", "")
            details = sims_data.get(f"sims_sample_{idx}_details", "") or sims_data.get(f"sample_{idx}_details", "")
            
            # Solo añadir si tiene identificación o nombre
            if identification or name:
                samples.append({
                    "index": idx,
                    "identification": identification or name or f"Muestra {idx + 1}",
                    "name": name or identification or f"Muestra {idx + 1}",
                    "details": details,
                })
    
    return samples


def _build_request_code_from_proposal(proposal):
    if not proposal:
        return ""
    request_code = _format_request_code(proposal.access_code)
    if request_code:
        return request_code
    return f"PROPOSAL-{proposal.pk}"


def _autofill_from_proposal(record, proposal=None):
    proposal = proposal or record.access_proposal
    if not proposal:
        return
    sample_identification, sample_characteristics = _extract_sims_sample_fields(proposal)
    if sample_identification and not record.sample_identification:
        record.sample_identification = sample_identification
    if sample_characteristics and not record.sample_characteristics:
        record.sample_characteristics = sample_characteristics
    name = _get_client_name_from_proposal(proposal)
    if name and not record.client_name:
        record.client_name = name
    if not record.request_code:
        record.request_code = _build_request_code_from_proposal(proposal)


def _replace_docx_placeholders(document, placeholders):
    replaced = False
    for paragraph in document.paragraphs:
        for key, value in placeholders.items():
            if key in paragraph.text:
                paragraph.text = paragraph.text.replace(key, value)
                replaced = True
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in placeholders.items():
                    if key in cell.text:
                        cell.text = cell.text.replace(key, value)
                replaced = True
    return replaced


def _build_equipment_detail_context(request, equipment, forms=None):
    context = {
        "equipment": equipment,
        "doc_refs": equipment.doc_refs.all().order_by("doc_code", "id"),
        "maintenance_activities": equipment.maintenance_activities.all().order_by("activity", "id"),
        "maintenance_records": equipment.maintenance_records.all().order_by("-performed_at", "id"),
        "incidents": equipment.incidents.all().order_by("-date", "id"),
        "can_edit": is_sims_responsable(request.user),
        "docref_form": SIMSEquipmentDocRefForm(),
        "maintenance_activity_form": SIMSMaintenanceActivityForm(),
        "maintenance_record_form": SIMSMaintenanceRecordForm(),
        "incident_form": SIMSEquipmentIncidentForm(),
    }
    if forms:
        context.update(forms)
    return context


def _annual_plan_redirect(year):
    return redirect(f"{reverse('icts:sigmasims:annual_plan')}?year={year}")


def _annual_plan_entry_snapshot(entry):
    return {
        "equipment_id": entry.equipment_id,
        "equipment_code": entry.equipment_code,
        "description": entry.description,
        "activity": entry.activity,
        "execution_type": entry.execution_type,
        "month_01": entry.month_01,
        "month_02": entry.month_02,
        "month_03": entry.month_03,
        "month_04": entry.month_04,
        "month_05": entry.month_05,
        "month_06": entry.month_06,
        "month_07": entry.month_07,
        "month_08": entry.month_08,
        "month_09": entry.month_09,
        "month_10": entry.month_10,
        "month_11": entry.month_11,
        "month_12": entry.month_12,
        "notes": entry.notes,
    }


def _log_annual_plan_change(plan, user, action, entry=None, before_data=None, after_data=None, message=""):
    SIMSAnnualPlanChangeLog.objects.create(
        plan=plan,
        entry=entry,
        user=user if user and user.is_authenticated else None,
        action=action,
        before_data=before_data,
        after_data=after_data,
        message=message or "",
    )


def _summarize_change_log(log):
    if log.message:
        return log.message
    if not log.before_data or not log.after_data:
        return ""
    changed = []
    for key, after_value in log.after_data.items():
        if log.before_data.get(key) != after_value:
            changed.append(key)
    if not changed:
        return ""
    return "Cambios: " + ", ".join(changed)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def dashboard(request):
    """
    Dashboard SIMS: Solo muestra propuestas aceptadas (accepted).
    Las propuestas 'submitted' están en revisión y solo son visibles para revisores.
    """
    # Solo propuestas aceptadas son visibles para técnicos SIMS
    base_qs = (
        AccessProposal.objects
        .filter(facility_sims=True, status="accepted")
    )

    proposals = (
        base_qs
        .select_related("applicant", "applicant__icts_profile")
        .annotate(sample_count=Count("sims_records", filter=Q(sims_records__is_removed=False)))
        .order_by("-submitted_at", "-created_at")
    )

    # Separar por si tienen fecha de análisis o no (solo registros activos)
    # Propuestas disponibles (sin fecha de análisis asignada)
    proposals_without_analysis = []
    proposals_with_analysis = []
    
    for p in proposals:
        active_records = p.sims_records.filter(is_removed=False)
        has_analysis = active_records.filter(analysis_date__isnull=False).exists()
        if has_analysis:
            proposals_with_analysis.append(p)
        else:
            proposals_without_analysis.append(p)

    # Contadores
    count_disponibles = len(proposals_without_analysis)
    count_aceptadas = len(proposals_with_analysis)
    
    # Limitar a las últimas 5
    proposals_without_analysis = proposals_without_analysis[:5]
    proposals_with_analysis = proposals_with_analysis[:5]

    # Total de muestras activas
    total_samples = SIMSRecord.objects.filter(is_removed=False).count()
    proposal_total = base_qs.count()

    # Búsqueda de propuestas
    search_query = request.GET.get("q", "").strip()
    search_results = None
    if search_query:
        search_results = list(
            proposals.filter(
                Q(access_code__icontains=search_query) |
                Q(title__icontains=search_query) |
                Q(applicant__username__icontains=search_query) |
                Q(applicant__first_name__icontains=search_query) |
                Q(applicant__last_name__icontains=search_query) |
                Q(applicant__icts_profile__user_siglas__icontains=search_query)
            )[:20]
        )
        # Añadir información de si tienen análisis
        for p in search_results:
            active_records = p.sims_records.filter(is_removed=False)
            p.has_analysis = active_records.filter(analysis_date__isnull=False).exists()

    return render(
        request,
        "sigmasims/dashboard.html",
        {
            "proposals_without_analysis": proposals_without_analysis,
            "proposals_with_analysis": proposals_with_analysis,
            "total_samples": total_samples,
            "proposal_total": proposal_total,
            "count_disponibles": count_disponibles,
            "count_aceptadas": count_aceptadas,
            "search_query": search_query,
            "search_results": search_results,
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def record_list(request):
    records, filters = _filter_records(request)
    return render(
        request,
        "sigmasims/record_list.html",
        {"records": records, **filters},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def record_create(request):
    proposal_id = request.GET.get("proposal_id")
    proposal = None
    initial = {}
    if proposal_id:
        try:
            proposal = (
                AccessProposal.objects
                .select_related("applicant", "applicant__icts_profile")
                .get(pk=proposal_id)
            )
        except (AccessProposal.DoesNotExist, ValueError, TypeError):
            proposal = None
    if proposal:
        initial["access_proposal"] = proposal
        request_code = _build_request_code_from_proposal(proposal)
        if request_code:
            initial["request_code"] = request_code
        client_name = _get_client_name_from_proposal(proposal)
        if client_name:
            initial["client_name"] = client_name
        sample_identification, sample_characteristics = _extract_sims_sample_fields(proposal)
        if sample_identification:
            initial["sample_identification"] = sample_identification
        if sample_characteristics:
            initial["sample_characteristics"] = sample_characteristics
    technicians_list = _get_sims_technicians_list()
    
    if request.method == "POST":
        form = SIMSRecordForm(request.POST, initial=initial, technicians_list=technicians_list)
        if proposal:
            form.fields["access_proposal"].queryset = AccessProposal.objects.filter(pk=proposal.pk)
            form.fields["access_proposal"].disabled = True
        if form.is_valid():
            record = form.save(commit=False)
            if proposal:
                record.access_proposal = proposal
            _autofill_from_proposal(record, proposal)
            record.save()
            messages.success(request, "Registro SIMS creado.")
            return redirect("icts:sigmasims:record_list")
    else:
        form = SIMSRecordForm(initial=initial, technicians_list=technicians_list)
        if proposal:
            form.fields["access_proposal"].queryset = AccessProposal.objects.filter(pk=proposal.pk)
            form.fields["access_proposal"].disabled = True
    
    # Obtener muestras disponibles de la propuesta
    available_samples = []
    if proposal:
        available_samples = _get_proposal_samples(proposal)
    
    return render(
        request,
        "sigmasims/record_form.html",
        {
            "form": form,
            "proposal": proposal,
            "available_samples": available_samples,
            "is_create": True,
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def record_create_bulk(request):
    """Añadir múltiples muestras con datos comunes."""
    proposal_id = request.GET.get("proposal_id")
    if not proposal_id:
        messages.error(request, "Debe especificar una propuesta.")
        return redirect("icts:sigmasims:dashboard")
    
    try:
        proposal = (
            AccessProposal.objects
            .select_related("applicant", "applicant__icts_profile")
            .get(pk=proposal_id, facility_sims=True)
        )
    except (AccessProposal.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Propuesta no encontrada.")
        return redirect("icts:sigmasims:dashboard")
    
    available_samples = _get_proposal_samples(proposal)
    # Obtener muestras ya registradas para deshabilitarlas
    registered_samples = set(
        SIMSRecord.objects
        .filter(access_proposal=proposal)
        .values_list("sample_identification", flat=True)
    )
    
    if request.method == "POST":
        selected_samples = request.POST.getlist("selected_samples")
        new_sample_id = request.POST.get("new_sample_id", "").strip()
        new_sample_details = request.POST.get("new_sample_details", "").strip()
        
        # Datos comunes
        reception_date_str = request.POST.get("reception_date")
        analysis_date_str = request.POST.get("analysis_date")

        # Convertir fechas de string a date
        reception_date = _parse_date(reception_date_str) if reception_date_str else None
        analysis_date = _parse_date(analysis_date_str) if analysis_date_str else None
        
        if not reception_date:
            messages.error(request, "La fecha de recepción es obligatoria.")
        else:
            common_data = {
                "reception_date": reception_date,
                "client_name": request.POST.get("client_name", "").strip(),
                "responsible_name": request.POST.get("responsible_name", "").strip(),
                "client_requirements": request.POST.get("client_requirements", "").strip(),
                "analysis_date": analysis_date,
                "incidents": request.POST.get("incidents", "").strip(),
                "comments": request.POST.get("comments", "").strip(),
            }
            
            if not selected_samples and not new_sample_id:
                messages.error(request, "Debe seleccionar al menos una muestra o añadir una nueva.")
            else:
                created_count = 0
                request_code = _build_request_code_from_proposal(proposal)
                client_name = common_data["client_name"] or _get_client_name_from_proposal(proposal)
                
                # Crear registros para muestras seleccionadas
                for sample_idx in selected_samples:
                    try:
                        idx = int(sample_idx)
                        if 0 <= idx < len(available_samples):
                            sample = available_samples[idx]
                            record = SIMSRecord(
                                access_proposal=proposal,
                                request_code=request_code,
                                reception_date=common_data["reception_date"],
                                sample_identification=sample["identification"],
                                client_name=client_name,
                                sample_characteristics=sample.get("details", ""),
                                responsible_name=common_data["responsible_name"],
                                client_requirements=common_data["client_requirements"],
                                analysis_date=common_data["analysis_date"],
                                incidents=common_data["incidents"],
                                comments=common_data["comments"],
                                is_original_sample=True,
                            )
                            _autofill_from_proposal(record, proposal)
                            record.save()
                            created_count += 1
                    except (ValueError, IndexError):
                        continue
                
                # Crear registro para nueva muestra
                if new_sample_id:
                    record = SIMSRecord(
                        access_proposal=proposal,
                        request_code=request_code,
                        reception_date=common_data["reception_date"],
                        sample_identification=new_sample_id,
                        client_name=client_name,
                        sample_characteristics=new_sample_details,
                        responsible_name=common_data["responsible_name"],
                        client_requirements=common_data["client_requirements"],
                        analysis_date=common_data["analysis_date"],
                        incidents=common_data["incidents"],
                        comments=common_data["comments"],
                        is_original_sample=False,
                    )
                    _autofill_from_proposal(record, proposal)
                    record.save()
                    created_count += 1
                
                if created_count > 0:
                    messages.success(request, f"{created_count} muestra(s) registrada(s) correctamente.")
                    return redirect("icts:sigmasims:proposal_summary", proposal_id=proposal.pk)
                else:
                    messages.error(request, "No se pudo crear ningún registro.")
    
    client_name = _get_client_name_from_proposal(proposal)
    technicians_list = _get_sims_technicians_list()
    
    return render(
        request,
        "sigmasims/record_form_bulk.html",
        {
            "proposal": proposal,
            "available_samples": available_samples,
            "registered_samples": registered_samples,
            "client_name": client_name,
            "technicians_list": technicians_list,
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def record_edit(request, pk):
    record = get_object_or_404(SIMSRecord, pk=pk)
    technicians_list = _get_sims_technicians_list()
    if request.method == "POST":
        form = SIMSRecordForm(request.POST, instance=record, technicians_list=technicians_list)
        if form.is_valid():
            record = form.save(commit=False)
            _autofill_from_proposal(record)
            record.save()
            messages.success(request, "Registro SIMS actualizado.")
            return redirect("icts:sigmasims:record_list")
    else:
        form = SIMSRecordForm(instance=record, technicians_list=technicians_list)
    return render(
        request,
        "sigmasims/record_form.html",
        {"form": form, "is_create": False, "record": record},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def record_remove(request, pk):
    """Vista para eliminar/cancelar una muestra con motivo obligatorio."""
    record = get_object_or_404(SIMSRecord, pk=pk)
    
    if record.is_removed:
        messages.warning(request, "Esta muestra ya fue eliminada anteriormente.")
        if record.access_proposal:
            return redirect("icts:sigmasims:proposal_summary", proposal_id=record.access_proposal.pk)
        return redirect("icts:sigmasims:record_list")
    
    if request.method == "POST":
        form = SIMSRecordRemovalForm(request.POST)
        if form.is_valid():
            record.is_removed = True
            record.removal_reason = form.cleaned_data["removal_reason"]
            record.removed_by = request.user
            record.removed_at = timezone.now()
            record.save()
            messages.success(request, f"Muestra {record.sims_id} eliminada correctamente.")
            if record.access_proposal:
                return redirect("icts:sigmasims:proposal_summary", proposal_id=record.access_proposal.pk)
            return redirect("icts:sigmasims:record_list")
    else:
        form = SIMSRecordRemovalForm()
    
    return render(
        request,
        "sigmasims/record_remove.html",
        {"form": form, "record": record},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def record_export_xlsx(request):
    records, _filters = _filter_records(request)
    records = list(records)
    template_path = QUALITY_TEMPLATES_ROOT / "sims" / "REV001" / "sims_register_template.xlsx"
    if not template_path.exists():
        raise Http404("Plantilla Excel SIMS no encontrada.")

    workbook = load_workbook(template_path)
    if "SIMS" not in workbook.sheetnames:
        raise Http404("Hoja SIMS no encontrada en la plantilla.")
    sheet = workbook["SIMS"]

    data_columns = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16)
    max_row = max(sheet.max_row or 11, 10 + len(records))
    for row in range(11, max_row + 1):
        for col in data_columns:
            sheet.cell(row=row, column=col).value = None

    for index, record in enumerate(records):
        row = 11 + index
        sheet.cell(row=row, column=2).value = record.sims_id or ""
        sheet.cell(row=row, column=3).value = record.request_code or ""
        sheet.cell(row=row, column=4).value = record.reception_date
        sheet.cell(row=row, column=5).value = record.sample_identification or ""
        sheet.cell(row=row, column=6).value = record.client_name or ""
        sheet.cell(row=row, column=7).value = record.sample_characteristics or ""
        sheet.cell(row=row, column=8).value = record.responsible_name or ""
        sheet.cell(row=row, column=9).value = record.client_requirements or ""
        sheet.cell(row=row, column=10).value = record.analysis_date
        sheet.cell(row=row, column=11).value = record.return_date
        sheet.cell(row=row, column=12).value = record.incidents or ""
        sheet.cell(row=row, column=16).value = record.comments or ""

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    filename = f"sims_records_{timezone.now():%Y%m%d}.xlsx"
    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def docs_list(request):
    documents = SIMSDocument.objects.filter(is_active=True).order_by("-date")
    return render(
        request,
        "sigmasims/docs_list.html",
        {"documents": documents, "can_edit": is_sims_responsable(request.user)},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def doc_upload(request):
    if request.method == "POST":
        form = SIMSDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Documento SIMS subido.")
            return redirect("icts:sigmasims:docs_list")
    else:
        form = SIMSDocumentForm()
    return render(
        request,
        "sigmasims/doc_upload.html",
        {"form": form},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def doc_download(request, pk):
    document = get_object_or_404(SIMSDocument, pk=pk)
    if not document.file:
        raise Http404("Documento no disponible.")
    response = FileResponse(document.file.open("rb"), as_attachment=True)
    return response


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def equipment_list(request):
    query = (request.GET.get("q") or "").strip()
    equipments = SIMSEquipment.objects.all()
    if query:
        equipments = equipments.filter(
            Q(code__icontains=query)
            | Q(description__icontains=query)
            | Q(responsible__icontains=query)
            | Q(location__icontains=query)
        )
    last_update = SIMSEquipment.objects.aggregate(last_update=Max("updated_at"))["last_update"]
    return render(
        request,
        "sigmasims/equipment_list.html",
        {
            "equipments": equipments,
            "query": query,
            "last_update": last_update,
            "can_edit": is_sims_responsable(request.user),
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def equipment_detail(request, equipment_id):
    equipment = get_object_or_404(
        SIMSEquipment.objects.prefetch_related(
            "doc_refs",
            "maintenance_activities",
            "maintenance_records",
            "incidents",
        ),
        pk=equipment_id,
    )
    context = _build_equipment_detail_context(request, equipment)
    return render(request, "sigmasims/equipment_detail.html", context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def equipment_create(request):
    if request.method == "POST":
        form = SIMSEquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, "Equipo SIMS creado.")
            return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    else:
        form = SIMSEquipmentForm()
    return render(
        request,
        "sigmasims/equipment_form.html",
        {"form": form, "is_create": True},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def equipment_edit(request, equipment_id):
    equipment = get_object_or_404(SIMSEquipment, pk=equipment_id)
    if request.method == "POST":
        form = SIMSEquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, "Equipo SIMS actualizado.")
            return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    else:
        form = SIMSEquipmentForm(instance=equipment)
    return render(
        request,
        "sigmasims/equipment_form.html",
        {"form": form, "is_create": False, "equipment": equipment},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def equipment_docref_add(request, equipment_id):
    equipment = get_object_or_404(SIMSEquipment, pk=equipment_id)
    if request.method != "POST":
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    form = SIMSEquipmentDocRefForm(request.POST, request.FILES)
    if form.is_valid():
        docref = form.save(commit=False)
        docref.equipment = equipment
        docref.uploaded_by = request.user
        docref.save()
        messages.success(request, "Documentacion asociada creada.")
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(request, equipment, {"docref_form": form})
    return render(request, "sigmasims/equipment_detail.html", context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def equipment_maintenance_activity_add(request, equipment_id):
    equipment = get_object_or_404(SIMSEquipment, pk=equipment_id)
    if request.method != "POST":
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    form = SIMSMaintenanceActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.equipment = equipment
        activity.save()
        messages.success(request, "Actividad de mantenimiento creada.")
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(
        request,
        equipment,
        {"maintenance_activity_form": form},
    )
    return render(request, "sigmasims/equipment_detail.html", context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def equipment_maintenance_record_add(request, equipment_id):
    equipment = get_object_or_404(SIMSEquipment, pk=equipment_id)
    if request.method != "POST":
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    form = SIMSMaintenanceRecordForm(request.POST)
    if form.is_valid():
        record = form.save(commit=False)
        record.equipment = equipment
        record.save()
        messages.success(request, "Registro de mantenimiento creado.")
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(
        request,
        equipment,
        {"maintenance_record_form": form},
    )
    return render(request, "sigmasims/equipment_detail.html", context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def equipment_incident_add(request, equipment_id):
    equipment = get_object_or_404(SIMSEquipment, pk=equipment_id)
    if request.method != "POST":
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    form = SIMSEquipmentIncidentForm(request.POST, request.FILES)
    if form.is_valid():
        incident = form.save(commit=False)
        incident.equipment = equipment
        incident.save()
        messages.success(request, "Incidencia creada.")
        return redirect("icts:sigmasims:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(request, equipment, {"incident_form": form})
    return render(request, "sigmasims/equipment_detail.html", context)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def equipment_docref_download(request, docref_id):
    docref = get_object_or_404(SIMSEquipmentDocRef, pk=docref_id)
    if not docref.file:
        raise Http404("Documento no disponible.")
    return FileResponse(docref.file.open("rb"), as_attachment=True)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def equipment_incident_download(request, incident_id):
    incident = get_object_or_404(SIMSEquipmentIncident, pk=incident_id)
    if not incident.attachment:
        raise Http404("Adjunto no disponible.")
    return FileResponse(incident.attachment.open("rb"), as_attachment=True)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def inventory_list(request):
    query = (request.GET.get("q") or "").strip()
    items = SIMSSparePartInventory.objects.all()
    if query:
        items = items.filter(item_name__icontains=query)
    return render(
        request,
        "sigmasims/inventory_list.html",
        {
            "items": items,
            "query": query,
            "can_edit": is_sims_responsable(request.user),
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def inventory_create(request):
    if request.method == "POST":
        form = SIMSSparePartInventoryForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, "Item de inventario creado.")
            return redirect("icts:sigmasims:inventory_list")
    else:
        form = SIMSSparePartInventoryForm()
    return render(
        request,
        "sigmasims/inventory_form.html",
        {"form": form, "is_create": True},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def inventory_edit(request, pk):
    item = get_object_or_404(SIMSSparePartInventory, pk=pk)
    if request.method == "POST":
        form = SIMSSparePartInventoryForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, "Item de inventario actualizado.")
            return redirect("icts:sigmasims:inventory_list")
    else:
        form = SIMSSparePartInventoryForm(instance=item)
    return render(
        request,
        "sigmasims/inventory_form.html",
        {"form": form, "is_create": False, "item": item},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def annual_plan_view(request):
    year_raw = request.GET.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year

    plan = SIMSAnnualPlan.objects.filter(year=year).first()
    preview = False
    source_plan = None
    if plan:
        entries = (
            SIMSAnnualPlanEntry.objects
            .filter(plan=plan)
            .select_related("equipment")
        )
    else:
        source_plan = (
            SIMSAnnualPlan.objects
            .filter(year__lt=year)
            .order_by("-year")
            .first()
        )
        if source_plan:
            preview = True
            entries = (
                SIMSAnnualPlanEntry.objects
                .filter(plan=source_plan)
                .select_related("equipment")
            )
        else:
            entries = SIMSAnnualPlanEntry.objects.none()

    return render(
        request,
        "sigmasims/annual_plan.html",
        {
            "plan": plan,
            "preview": preview,
            "source_plan": source_plan,
            "year": year,
            "year_form": SIMSAnnualPlanYearForm(initial={"year": year}),
            "entries": entries,
            "can_edit": is_sims_responsable(request.user),
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def annual_plan_copy_previous(request):
    if request.method != "POST":
        return _annual_plan_redirect(timezone.now().year)
    year_raw = request.POST.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year

    if SIMSAnnualPlan.objects.filter(year=year).exists():
        messages.info(request, "El plan anual ya existe para ese ano.")
        return _annual_plan_redirect(year)

    source_plan = (
        SIMSAnnualPlan.objects
        .filter(year__lt=year)
        .order_by("-year")
        .first()
    )
    if not source_plan:
        messages.warning(request, "No hay plan anterior para copiar.")
        return _annual_plan_redirect(year)

    with transaction.atomic():
        plan = SIMSAnnualPlan.objects.create(year=year)
        source_entries = SIMSAnnualPlanEntry.objects.filter(plan=source_plan).select_related("equipment")
        created_count = 0
        for source in source_entries:
            entry = SIMSAnnualPlanEntry.objects.create(
                plan=plan,
                equipment=source.equipment,
                equipment_code=source.equipment_code,
                description=source.description,
                activity=source.activity,
                execution_type=source.execution_type,
                month_01=False,
                month_02=False,
                month_03=False,
                month_04=False,
                month_05=False,
                month_06=False,
                month_07=False,
                month_08=False,
                month_09=False,
                month_10=False,
                month_11=False,
                month_12=False,
                notes=source.notes,
            )
            created_count += 1
            _log_annual_plan_change(
                plan,
                request.user,
                SIMSAnnualPlanChangeLog.ACTION_CREATE,
                entry=entry,
                after_data=_annual_plan_entry_snapshot(entry),
            )
        _log_annual_plan_change(
            plan,
            request.user,
            SIMSAnnualPlanChangeLog.ACTION_COPY,
            message=f"Copia desde {source_plan.year} ({created_count} entradas).",
            after_data={"source_year": source_plan.year, "entries_copied": created_count},
        )

    messages.success(request, "Plan anual copiado.")
    return _annual_plan_redirect(year)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def annual_plan_history(request):
    year_raw = request.GET.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year

    plan = SIMSAnnualPlan.objects.filter(year=year).first()
    logs = []
    if plan:
        logs = list(
            SIMSAnnualPlanChangeLog.objects
            .filter(plan=plan)
            .select_related("user", "entry")
            .order_by("-created_at", "-id")
        )

    activity_labels = dict(SIMSAnnualPlanEntry.ACTIVITY_CHOICES)
    execution_labels = dict(SIMSAnnualPlanEntry.EXECUTION_CHOICES)
    log_rows = []
    for log in logs:
        data = log.after_data or log.before_data or {}
        entry_code = data.get("equipment_code") or ""
        if not entry_code and log.entry:
            entry_code = log.entry.equipment_code
        activity_value = data.get("activity") or (log.entry.activity if log.entry else "")
        execution_value = data.get("execution_type") or (log.entry.execution_type if log.entry else "")
        log_rows.append(
            {
                "log": log,
                "equipment_code": entry_code,
                "activity": activity_labels.get(activity_value, activity_value or "-"),
                "execution": execution_labels.get(execution_value, execution_value or "-"),
                "summary": _summarize_change_log(log),
            }
        )

    return render(
        request,
        "sigmasims/annual_plan_history.html",
        {
            "plan": plan,
            "year": year,
            "log_rows": log_rows,
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def annual_plan_entry_create(request):
    year_raw = request.GET.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year
    plan, _created = SIMSAnnualPlan.objects.get_or_create(year=year)

    if request.method == "POST":
        form = SIMSAnnualPlanEntryForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.plan = plan
                entry.save()
                _log_annual_plan_change(
                    plan,
                    request.user,
                    SIMSAnnualPlanChangeLog.ACTION_CREATE,
                    entry=entry,
                    after_data=_annual_plan_entry_snapshot(entry),
                )
            messages.success(request, "Entrada del plan anual creada.")
            return _annual_plan_redirect(year)
    else:
        form = SIMSAnnualPlanEntryForm()
    return render(
        request,
        "sigmasims/annual_plan_entry_form.html",
        {"form": form, "is_create": True, "year": year},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def annual_plan_entry_edit(request, pk):
    entry = get_object_or_404(SIMSAnnualPlanEntry, pk=pk)
    plan = entry.plan
    year = plan.year
    if request.method == "POST":
        before_data = _annual_plan_entry_snapshot(entry)
        form = SIMSAnnualPlanEntryForm(request.POST, instance=entry)
        if form.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.plan = plan
                entry.save()
                _log_annual_plan_change(
                    plan,
                    request.user,
                    SIMSAnnualPlanChangeLog.ACTION_UPDATE,
                    entry=entry,
                    before_data=before_data,
                    after_data=_annual_plan_entry_snapshot(entry),
                )
            messages.success(request, "Entrada del plan anual actualizada.")
            return _annual_plan_redirect(year)
    else:
        form = SIMSAnnualPlanEntryForm(instance=entry)
    return render(
        request,
        "sigmasims/annual_plan_entry_form.html",
        {"form": form, "is_create": False, "entry": entry, "year": year},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def annual_plan_entry_delete(request, pk):
    entry = get_object_or_404(SIMSAnnualPlanEntry, pk=pk)
    year = entry.plan.year
    if request.method == "POST":
        with transaction.atomic():
            before_data = _annual_plan_entry_snapshot(entry)
            plan = entry.plan
            _log_annual_plan_change(
                plan,
                request.user,
                SIMSAnnualPlanChangeLog.ACTION_DELETE,
                entry=entry,
                before_data=before_data,
            )
            entry.delete()
            messages.success(request, "Entrada del plan anual eliminada.")
    return _annual_plan_redirect(year)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def proposal_summary(request, proposal_id):
    """Vista de resumen de la propuesta con todos los datos."""
    proposal = get_object_or_404(AccessProposal, pk=proposal_id, facility_sims=True)
    
    # Separar registros activos de eliminados
    all_records = SIMSRecord.objects.filter(access_proposal=proposal)
    records = all_records.filter(is_removed=False)
    removed_records = all_records.filter(is_removed=True)
    
    report = SIMSReport.objects.filter(access_proposal=proposal).first()
    available_samples = _get_proposal_samples(proposal)
    
    # Obtener muestras ya registradas (solo las activas)
    registered_samples = set(
        records.values_list("sample_identification", flat=True)
    )
    
    # Verificar si algún registro tiene fecha de análisis
    has_analysis_date = records.filter(analysis_date__isnull=False).exists()

    return render(
        request,
        "sigmasims/proposal_summary.html",
        {
            "proposal": proposal,
            "records": records,
            "removed_records": removed_records,
            "report": report,
            "available_samples": available_samples,
            "registered_samples": registered_samples,
            "has_analysis_date": has_analysis_date,
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def report_detail(request, proposal_id):
    proposal = get_object_or_404(AccessProposal, pk=proposal_id)
    report = SIMSReport.objects.filter(access_proposal=proposal).first()
    records = SIMSRecord.objects.filter(access_proposal=proposal, is_removed=False)
    return render(
        request,
        "sigmasims/report_detail.html",
        {
            "proposal": proposal,
            "report": report,
            "records": records,
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def report_edit(request, proposal_id):
    proposal = get_object_or_404(AccessProposal, pk=proposal_id)
    report, _created = SIMSReport.objects.get_or_create(access_proposal=proposal)
    
    # Inicializar campos si es nuevo
    if _created:
        # entry_date: fecha cuando se acepta (submitted_at o fecha actual si está aceptada)
        if proposal.status == "accepted" and proposal.submitted_at:
            report.entry_date = proposal.submitted_at.date()
        elif proposal.status == "accepted":
            report.entry_date = timezone.now().date()
        
        # analysis_date: primera fecha de análisis de los records
        first_analysis = (
            SIMSRecord.objects
            .filter(access_proposal=proposal, analysis_date__isnull=False)
            .order_by("analysis_date")
            .values_list("analysis_date", flat=True)
            .first()
        )
        if first_analysis:
            report.analysis_date = first_analysis
        report.save()
    
    if request.method == "POST":
        form = SIMSReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, "Control de análisis actualizado.")
            return redirect("icts:sigmasims:report_detail", proposal_id=proposal.pk)
    else:
        form = SIMSReportForm(instance=report)
    return render(
        request,
        "sigmasims/report_form.html",
        {"form": form, "proposal": proposal, "report": report},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def report_add_image(request, proposal_id):
    proposal = get_object_or_404(AccessProposal, pk=proposal_id)
    report, _created = SIMSReport.objects.get_or_create(access_proposal=proposal)
    if request.method == "POST" and request.FILES.get("image"):
        SIMSReportImage.objects.create(
            report=report,
            image=request.FILES["image"],
            caption=(request.POST.get("caption") or "").strip(),
        )
        messages.success(request, "Imagen añadida.")
    return redirect("icts:sigmasims:report_detail", proposal_id=proposal.pk)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def report_add_file(request, proposal_id):
    proposal = get_object_or_404(AccessProposal, pk=proposal_id)
    report, _created = SIMSReport.objects.get_or_create(access_proposal=proposal)
    if request.method == "POST" and request.FILES.get("file"):
        SIMSReportFile.objects.create(
            report=report,
            file=request.FILES["file"],
            caption=(request.POST.get("caption") or "").strip(),
        )
        messages.success(request, "Archivo añadido.")
    return redirect("icts:sigmasims:report_detail", proposal_id=proposal.pk)


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def report_export_docx(request, proposal_id):
    proposal = get_object_or_404(AccessProposal, pk=proposal_id)
    report = get_object_or_404(SIMSReport, access_proposal=proposal)
    records = list(SIMSRecord.objects.filter(access_proposal=proposal))

    request_code = proposal.access_code
    if records and not request_code:
        request_code = records[0].request_code

    profile = getattr(proposal.applicant, "icts_profile", None)
    client_name = (
        proposal.contact_person
        or proposal.applicant.get_full_name()
        or proposal.applicant.get_username()
    ).strip()
    client_email = (proposal.email or proposal.applicant.email or "").strip()
    client_phone = (proposal.phone or "").strip()
    client_center = (getattr(profile, "center", "") or "").strip()
    reception_date = records[0].reception_date if records else None
    analysis_date = records[0].analysis_date if records else None

    placeholders = {
        "{{REQUEST_CODE}}": request_code or "",
        "{{CLIENT_NAME}}": client_name,
        "{{CLIENT_EMAIL}}": client_email,
        "{{CLIENT_PHONE}}": client_phone,
        "{{CLIENT_CENTER}}": client_center,
        "{{RECEPTION_DATE}}": str(reception_date or ""),
        "{{ANALYSIS_DATE}}": str(analysis_date or ""),
        "{{DETERMINATION}}": report.determination or "",
        "{{PROCEDURE}}": report.procedure_used or "",
        "{{TECHNIQUE}}": report.technique_text or "",
        "{{SAMPLE_DESCRIPTION}}": report.sample_description or "",
        "{{MEASUREMENT_CONDITIONS}}": report.measurement_conditions or "",
        "{{RESULTS_TEXT}}": report.results_text or "",
        "{{CONCLUSIONS}}": report.conclusions or "",
    }

    template_path = (
        Path(settings.BASE_DIR)
        / "Templates de referencia"
        / "PT-DTF-05-F05-Informe de resultados_v0_1.docx"
    )
    if template_path.exists():
        document = Document(str(template_path))
        placeholders_replaced = _replace_docx_placeholders(document, placeholders)
    else:
        document = Document()
        placeholders_replaced = False

    if not placeholders_replaced:
        # Fallback: insert core sections if no template/placeholders are available.
        document.add_heading("INFORME DE RESULTADOS", level=1)
        document.add_paragraph(f"Codigo acceso: {request_code or ''}")
        document.add_paragraph(f"Determinacion: {report.determination}")
        document.add_paragraph(f"Procedimiento: {report.procedure_used}")
        document.add_paragraph(f"Tecnica: {report.technique_text}")
        document.add_paragraph("Descripcion de las muestras:")
        document.add_paragraph(report.sample_description)
        document.add_paragraph("Condiciones de medida:")
        document.add_paragraph(report.measurement_conditions)
        document.add_paragraph("Resultados:")
        document.add_paragraph(report.results_text)
        document.add_paragraph("Conclusiones:")
        document.add_paragraph(report.conclusions)

    table = document.add_table(rows=1, cols=3)
    header_cells = table.rows[0].cells
    header_cells[0].text = "ID Lab"
    header_cells[1].text = "Identificacion cliente"
    header_cells[2].text = "Observaciones"
    for record in records:
        row_cells = table.add_row().cells
        row_cells[0].text = record.sims_id or ""
        row_cells[1].text = record.sample_identification
        row_cells[2].text = record.comments or ""

    for image in report.images.all():
        try:
            document.add_paragraph(image.caption or "")
            document.add_picture(image.image.path, width=Inches(5))
        except Exception:
            continue

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    filename = f"sims_report_{proposal.pk}.docx"
    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _avg(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _semester_ranges(year):
    return (
        (date(year, 1, 1), date(year, 6, 30)),
        (date(year, 7, 1), date(year, 12, 31)),
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def indicators_dashboard(request):
    year_raw = request.GET.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    semester_data = []
    for idx, (start_date, end_date) in enumerate(_semester_ranges(year), start=1):
        i1_values = []
        records = SIMSRecord.objects.filter(
            analysis_date__range=(start_date, end_date),
            reception_date__isnull=False,
        )
        for record in records:
            days = record.quality_i1_days
            if days is not None and days >= 0:
                i1_values.append(days)

        i2_values = []
        reports = SIMSReport.objects.filter(
            delivery_date__range=(start_date, end_date)
        )
        for report in reports:
            analysis_date = (
                SIMSRecord.objects.filter(
                    access_proposal=report.access_proposal,
                    analysis_date__isnull=False,
                )
                .order_by("analysis_date")
                .values_list("analysis_date", flat=True)
                .first()
            )
            if analysis_date and report.delivery_date:
                i2_values.append((report.delivery_date - analysis_date).days)

        i1_avg = _avg(i1_values)
        i2_avg = _avg(i2_values)
        semester_data.append(
            {
                "label": f"Semestre {idx}",
                "i1_avg": i1_avg,
                "i2_avg": i2_avg,
                "i1_ok": i1_avg is not None and i1_avg < 15,
                "i2_ok": i2_avg is not None and i2_avg < 30,
            }
        )

    # Use analysis_date for completed analyses, plus reception_date for pending samples.
    i1_records = SIMSRecord.objects.filter(
        Q(analysis_date__range=(year_start, year_end))
        | Q(analysis_date__isnull=True, reception_date__range=(year_start, year_end))
    )
    i1_stats = compute_i1_stats(i1_records)

    return render(
        request,
        "sigmasims/indicators_dashboard.html",
        {"year": year, "semester_data": semester_data, "i1_stats": i1_stats},
    )


# --- Materiales de Referencia ---

def _read_reference_material_from_excel(code):
    """
    Lee los datos de un material de referencia del Excel.
    Retorna un diccionario con los datos o None si no se encuentra.
    El Excel tiene formato clave-valor donde columna 2 = etiqueta, columna 3 = valor.
    """
    excel_path = Path(settings.BASE_DIR) / "media" / "Datos" / "SIMS" / "Materiales de referencia" / "LI-DTF_MR L05_ed2.xlsx"
    sheet_name = "MR-DTF-L05-01"
    
    if not excel_path.exists():
        return None
    
    try:
        from openpyxl import load_workbook
        wb = load_workbook(excel_path, data_only=True)
        
        # Verificar que la hoja existe
        if sheet_name not in wb.sheetnames:
            return None
            
        ws = wb[sheet_name]
        
        # Buscar la fila con el código
        code_row = None
        for row_idx in range(1, ws.max_row + 1):
            cell_value = ws.cell(row=row_idx, column=2).value
            if cell_value:
                cell_str = str(cell_value).strip().upper()
                if "CÓDIGO" in cell_str or "CODIGO" in cell_str:
                    # Verificar el valor en la columna siguiente
                    code_value = ws.cell(row=row_idx, column=3).value
                    if code_value and str(code_value).strip() == code:
                        code_row = row_idx
                        break
        
        if not code_row:
            return None
        
        # Leer todos los datos desde esta sección hasta encontrar otra sección o fin de datos
        data = {}
        current_section = None
        
        # Leer hacia atrás un poco para capturar datos anteriores al código
        start_row = max(1, code_row - 5)
        # Leer hacia adelante hasta encontrar nueva sección (número o título)
        end_row = min(ws.max_row + 1, code_row + 100)
        
        for row_idx in range(start_row, end_row):
            label_cell = ws.cell(row=row_idx, column=2).value
            value_cell = ws.cell(row=row_idx, column=3).value
            
            if label_cell:
                label_str = str(label_cell).strip()
                
                # Detectar inicio de nueva sección (números o títulos en mayúsculas)
                if (label_str.isdigit() and len(label_str) <= 2) or \
                   ("DATOS DEL MATERIAL" in label_str.upper()) or \
                   ("PROPIEDADES" in label_str.upper() and "FISICAS" in label_str.upper()):
                    # Si encontramos una nueva sección después del código, parar
                    if row_idx > code_row and current_section:
                        break
                    current_section = label_str
                    continue
                
                # Si encontramos el código, empezar a leer datos
                if "CÓDIGO" in label_str.upper() or "CODIGO" in label_str.upper():
                    if value_cell and str(value_cell).strip() == code:
                        continue  # Ya sabemos que es nuestro código
                
                # Leer el valor
                if value_cell is not None:
                    value_str = str(value_cell).strip()
                    # Ignorar valores vacíos, "NA", "x" solos
                    if value_str and value_str not in ["NA", "x", ""]:
                        data[label_str] = value_str
                else:
                    # Buscar valor en otras columnas
                    for col in range(4, min(ws.max_column + 1, 11)):
                        alt_value = ws.cell(row=row_idx, column=col).value
                        if alt_value:
                            alt_str = str(alt_value).strip()
                            if alt_str and alt_str not in ["NA", "x", ""]:
                                data[label_str] = alt_str
                                break
        
        return data if data else None
        
    except Exception as e:
        logger.exception(f"Error leyendo Excel de materiales de referencia: {e}")
        return None


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def reference_materials_list(request):
    """Lista de materiales de referencia."""
    materials = SIMSReferenceMaterial.objects.filter(is_active=True).order_by("code")
    
    # Si no hay materiales en BD, intentar leer del Excel
    if not materials.exists():
        # Leer códigos del Excel
        excel_path = Path(settings.BASE_DIR) / "media" / "Datos" / "SIMS" / "Materiales de referencia" / "LI-DTF_MR L05_ed2.xlsx"
        sheet_name = "MR-DTF-L05-01"
        
        if excel_path.exists():
            try:
                from openpyxl import load_workbook
                wb = load_workbook(excel_path, data_only=True)
                
                if sheet_name not in wb.sheetnames:
                    logger.warning(f"Hoja {sheet_name} no encontrada en Excel")
                else:
                    ws = wb[sheet_name]
                    
                    # Buscar todos los códigos
                    codes_found = []
                    for row_idx in range(1, ws.max_row + 1):
                        cell_value = ws.cell(row=row_idx, column=2).value
                        if cell_value:
                            cell_str = str(cell_value).strip().upper()
                            if "CÓDIGO" in cell_str or "CODIGO" in cell_str:
                                code_value = ws.cell(row=row_idx, column=3).value
                                if code_value:
                                    code_str = str(code_value).strip()
                                    # Validar que sea un código válido (no números sueltos, no texto genérico)
                                    if code_str and len(code_str) > 3 and code_str not in codes_found:
                                        # Verificar que no sea solo un número
                                        if not (code_str.isdigit() and len(code_str) <= 2):
                                            codes_found.append(code_str)
                                            
                                            # Leer descripción (suele estar en la fila siguiente)
                                            desc = ""
                                            responsible = ""
                                            for r in range(row_idx + 1, min(row_idx + 15, ws.max_row + 1)):
                                                label = ws.cell(row=r, column=2).value
                                                if label:
                                                    label_str = str(label).strip().lower()
                                                    if "descripción" in label_str or "descripcion" in label_str:
                                                        desc_value = ws.cell(row=r, column=3).value
                                                        if desc_value:
                                                            desc = str(desc_value).strip()
                                                    elif "responsable" in label_str:
                                                        resp_value = ws.cell(row=r, column=3).value
                                                        if resp_value:
                                                            responsible = str(resp_value).strip()
                                            
                                            # Crear o actualizar material
                                            material, created = SIMSReferenceMaterial.objects.get_or_create(
                                                code=code_str,
                                                defaults={
                                                    "description": desc[:255] if desc else "",
                                                    "responsible": responsible[:100] if responsible else "",
                                                    "is_active": True,
                                                }
                                            )
                                            
                                            # Si es nuevo, sincronizar todos los datos del Excel
                                            if created:
                                                _sync_material_from_excel(material)
                                            
            except Exception as e:
                logger.exception(f"Error leyendo códigos del Excel: {e}")
        
        # Recargar materiales
        materials = SIMSReferenceMaterial.objects.filter(is_active=True).order_by("code")
    
    return render(
        request,
        "sigmasims/reference_materials_list.html",
        {
            "materials": materials,
            "can_edit": is_sims_responsable(request.user),
        },
    )


def _sync_material_from_excel(material):
    """
    Sincroniza los datos del Excel con el modelo.
    Si el material tiene datos en BD, no los sobrescribe.
    """
    excel_data = _read_reference_material_from_excel(material.code)
    if not excel_data:
        return False
    
    # Mapeo de campos del Excel a campos del modelo (búsqueda flexible)
    field_mapping = {
        "PATRÓN": ("is_pattern", lambda v: str(v).strip().upper() in ["SI", "SÍ", "X"]),
        "pattern": ("is_pattern", lambda v: str(v).strip().upper() in ["SI", "SÍ", "X"]),
        "patrón": ("is_pattern", lambda v: str(v).strip().upper() in ["SI", "SÍ", "X"]),
        "tipo de patrón": ("pattern_type", None),
        "Responsable": ("responsible", None),
        "responsable": ("responsible", None),
        "Descripción": ("description", None),
        "descripción": ("description", None),
        "descripcion": ("description", None),
        "Referencia": ("reference", None),
        "referencia": ("reference", None),
        "Fecha recepción": ("reception_date", lambda v: _parse_date(str(v).split()[0]) if v else None),
        "Fecha recepción": ("reception_date", lambda v: _parse_date(str(v).split()[0]) if v else None),
        "fecha recepción": ("reception_date", lambda v: _parse_date(str(v).split()[0]) if v else None),
        "Proveedor": ("supplier", None),
        "proveedor": ("supplier", None),
        "Localización": ("location", None),
        "localización": ("location", None),
        "localizacion": ("location", None),
        "Condiciones conservación": ("conservation_conditions", None),
        "condiciones conservación": ("conservation_conditions", None),
        "Tipo emisión": ("emission_type", None),
        "tipo emisión": ("emission_type", None),
        "Actividad": ("activity", None),
        "actividad": ("activity", None),
        "Tasa emisión": ("emission_rate", None),
        "tasa emisión": ("emission_rate", None),
        "Caducidad": ("expiry_date", lambda v: _parse_date(str(v).split()[0]) if v else None),
        "caducidad": ("expiry_date", lambda v: _parse_date(str(v).split()[0]) if v else None),
        "Fecha apertura": ("opening_date", lambda v: _parse_date(str(v).split()[0]) if v else None),
        "fecha apertura": ("opening_date", lambda v: _parse_date(str(v).split()[0]) if v else None),
        "Criterio de aceptación calibraciones": ("calibration_acceptance_criteria", None),
        "criterio de aceptación": ("calibration_acceptance_criteria", None),
        "Verificación de la conformidad": ("conformity_verification", None),
        "verificación de la conformidad": ("conformity_verification", None),
    }
    
    updated = False
    # Búsqueda flexible por clave (case-insensitive, parcial)
    for excel_key, excel_value in excel_data.items():
        excel_key_lower = excel_key.lower().strip()
        for map_key, (model_field, transform) in field_mapping.items():
            if map_key.lower() in excel_key_lower or excel_key_lower in map_key.lower():
                value = excel_value
                if value and str(value).strip() not in ["NA", "x", ""]:
                    if transform:
                        try:
                            value = transform(value)
                        except Exception:
                            value = str(value).strip()
                    else:
                        value = str(value).strip()
                    
                    if value:
                        current_value = getattr(material, model_field)
                        # Solo actualizar si el campo está vacío en BD
                        if not current_value or (isinstance(current_value, str) and not current_value.strip()):
                            setattr(material, model_field, value)
                            updated = True
                break
    
    # Guardar cache de Excel
    material.excel_data = excel_data
    
    if updated:
        material.save()
    
    return updated


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def reference_material_detail(request, code):
    """Detalle de un material de referencia."""
    material = get_object_or_404(SIMSReferenceMaterial, code=code)
    
    # Intentar sincronizar con Excel si no tiene datos
    if not material.description and not material.responsible:
        _sync_material_from_excel(material)
        material.refresh_from_db()
    
    # Obtener solo campos con datos
    filled_fields = material.get_filled_fields()
    
    return render(
        request,
        "sigmasims/reference_material_detail.html",
        {
            "material": material,
            "filled_fields": filled_fields,
            "can_edit": is_sims_responsable(request.user),
        },
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def reference_material_create(request):
    """Crear nuevo material de referencia."""
    if request.method == "POST":
        form = SIMSReferenceMaterialForm(request.POST)
        if form.is_valid():
            material = form.save()
            messages.success(request, f"Material de referencia {material.code} creado correctamente.")
            return redirect("icts:sigmasims:reference_material_detail", code=material.code)
    else:
        form = SIMSReferenceMaterialForm()
    
    return render(
        request,
        "sigmasims/reference_material_form.html",
        {"form": form, "is_create": True},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_responsable)
def reference_material_edit(request, code):
    """Editar material de referencia."""
    material = get_object_or_404(SIMSReferenceMaterial, code=code)
    
    if request.method == "POST":
        form = SIMSReferenceMaterialForm(request.POST, instance=material)
        if form.is_valid():
            material = form.save()
            messages.success(request, f"Material de referencia {material.code} actualizado correctamente.")
            return redirect("icts:sigmasims:reference_material_detail", code=material.code)
    else:
        form = SIMSReferenceMaterialForm(instance=material)
    
    return render(
        request,
        "sigmasims/reference_material_form.html",
        {"form": form, "is_create": False, "material": material},
    )
