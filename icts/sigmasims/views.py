from datetime import date
from io import BytesIO
from pathlib import Path
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.db import transaction
from django.db.models import Q, Count, Max
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

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
    SIMSReportForm,
    SIMSSparePartInventoryForm,
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
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except (TypeError, ValueError):
        return None


def _filter_records(request):
    records = SIMSRecord.objects.all().select_related("access_proposal")
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
    base_qs = (
        AccessProposal.objects
        .filter(facility_sims=True)
        .exclude(status__in=["draft", "rejected"])
    )
    proposals = (
        base_qs
        .select_related("applicant", "applicant__icts_profile")
        .annotate(sample_count=Count("sims_records"))
        .order_by("-submitted_at", "-created_at")
    )
    proposals = list(proposals)
    accepted_proposals = [proposal for proposal in proposals if proposal.status == "accepted"]
    submitted_proposals = [proposal for proposal in proposals if proposal.status == "submitted"]
    other_proposals = [
        proposal
        for proposal in proposals
        if proposal.status not in {"accepted", "submitted"}
    ]
    status_counts = {
        item["status"]: item["total"]
        for item in base_qs.values("status").annotate(total=Count("id")).order_by()
    }
    total_samples = base_qs.aggregate(total=Count("sims_records"))["total"] or 0
    proposal_total = base_qs.count()

    return render(
        request,
        "sigmasims/dashboard.html",
        {
            "proposals": proposals,
            "accepted_proposals": accepted_proposals,
            "submitted_proposals": submitted_proposals,
            "other_proposals": other_proposals,
            "status_counts": status_counts,
            "total_samples": total_samples,
            "proposal_total": proposal_total,
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
    if request.method == "POST":
        form = SIMSRecordForm(request.POST, initial=initial)
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
        form = SIMSRecordForm(initial=initial)
        if proposal:
            form.fields["access_proposal"].queryset = AccessProposal.objects.filter(pk=proposal.pk)
            form.fields["access_proposal"].disabled = True
    return render(
        request,
        "sigmasims/record_form.html",
        {"form": form, "is_create": True},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def record_edit(request, pk):
    record = get_object_or_404(SIMSRecord, pk=pk)
    if request.method == "POST":
        form = SIMSRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save(commit=False)
            _autofill_from_proposal(record)
            record.save()
            messages.success(request, "Registro SIMS actualizado.")
            return redirect("icts:sigmasims:record_list")
    else:
        form = SIMSRecordForm(instance=record)
    return render(
        request,
        "sigmasims/record_form.html",
        {"form": form, "is_create": False, "record": record},
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
def report_detail(request, proposal_id):
    proposal = get_object_or_404(AccessProposal, pk=proposal_id)
    report = SIMSReport.objects.filter(access_proposal=proposal).first()
    records = SIMSRecord.objects.filter(access_proposal=proposal)
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
    if request.method == "POST":
        form = SIMSReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, "Informe SIMS actualizado.")
            return redirect("icts:sigmasims:report_detail", proposal_id=proposal.pk)
    else:
        form = SIMSReportForm(instance=report)
    return render(
        request,
        "sigmasims/report_form.html",
        {"form": form, "proposal": proposal},
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
