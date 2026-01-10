import re
import textwrap
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from icts.auth_utils import OPTICS_TECH_GROUPS, get_normalized_user_groups, user_in_groups
from icts.decorators import login_required_icts
from icts.models import AccessProposal

from .forms import (
    OpticsAnnualPlanEntryForm,
    OpticsAnnualPlanYearForm,
    OpticsEquipmentDocRefForm,
    OpticsEquipmentForm,
    OpticsEquipmentIncidentForm,
    OpticsMaintenanceActivityForm,
    OpticsMaintenanceRecordForm,
    OpticsReportForm,
    OpticsSampleForm,
    OpticsSessionForm,
)
from .models import (
    OpticsAnnualPlan,
    OpticsAnnualPlanChangeLog,
    OpticsAnnualPlanEntry,
    OpticsEquipment,
    OpticsEquipmentDocRef,
    OpticsEquipmentIncident,
    OpticsMaintenanceActivity,
    OpticsMaintenanceRecord,
    OpticsReport,
    OpticsSample,
    OpticsSession,
)


def is_optics_technician(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    groups = get_normalized_user_groups(user)
    return user_in_groups(user, OPTICS_TECH_GROUPS, groups)


def is_optics_responsable(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    groups = get_normalized_user_groups(user)
    return user_in_groups(
        user,
        {
            "tecnico_responsable_s_optics",
            "tecnicos_responsables_s_optics",
        },
        groups,
    )


def _resolve_client_name(session):
    report = getattr(session, "report", None)
    if report and report.client_name:
        return report.client_name
    proposal = session.access_proposal
    if not proposal:
        return ""
    return (
        proposal.contact_person
        or proposal.applicant.get_full_name()
        or proposal.applicant.get_username()
    )


def _resolve_project_name(session):
    report = getattr(session, "report", None)
    if report and report.project:
        return report.project
    proposal = session.access_proposal
    if not proposal:
        return ""
    return proposal.project_name or proposal.title or ""


def _get_optics_payload(proposal):
    data = proposal.facility_data or {}
    if isinstance(data, dict):
        payload = data.get("optics", {})
        return payload if isinstance(payload, dict) else {}
    return {}


def _extract_optics_samples(payload):
    if not isinstance(payload, dict):
        return []
    pattern = re.compile(r"^optics_sample_(\\d+)_(identification|name|observations)$")
    samples = {}
    for key, value in payload.items():
        match = pattern.match(str(key))
        if not match:
            continue
        try:
            index = int(match.group(1))
        except ValueError:
            index = 0
        field = match.group(2)
        samples.setdefault(index, {})[field] = value

    results = []
    for index in sorted(samples.keys()):
        data = samples[index]
        results.append(
            {
                "index": index,
                "identification": str(data.get("identification") or "").strip(),
                "name": str(data.get("name") or "").strip(),
                "observations": str(data.get("observations") or "").strip(),
            }
        )
    return results


def _resolve_measurement_magnitude(payload):
    measurement_type = str(payload.get("optics_measurement_type") or "").lower().strip()
    if measurement_type == "ftir":
        return "Espectro FTIR"
    if measurement_type == "uvvis":
        return "Espectro UV-VIS"
    return ""


def _resolve_measurement_type(payload):
    measurement_type = str(payload.get("optics_measurement_type") or "").lower().strip()
    if measurement_type == "ftir":
        return "FTIR"
    if measurement_type == "uvvis":
        return "UV-VIS"
    return ""


def _build_equipment_detail_context(request, equipment, forms=None):
    context = {
        "equipment": equipment,
        "doc_refs": equipment.doc_refs.all().order_by("doc_code", "id"),
        "maintenance_activities": equipment.maintenance_activities.all().order_by("activity", "id"),
        "maintenance_records": equipment.maintenance_records.all().order_by("-performed_at", "id"),
        "incidents": equipment.incidents.all().order_by("-date", "id"),
        "can_edit": is_optics_responsable(request.user),
        "docref_form": OpticsEquipmentDocRefForm(),
        "maintenance_activity_form": OpticsMaintenanceActivityForm(),
        "maintenance_record_form": OpticsMaintenanceRecordForm(),
        "incident_form": OpticsEquipmentIncidentForm(),
    }
    if forms:
        context.update(forms)
    return context


def _annual_plan_redirect(year):
    return redirect(f"{reverse('sigmaoptics_icts:annual_plan')}?year={year}")


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
    OpticsAnnualPlanChangeLog.objects.create(
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


@login_required_icts
@user_passes_test(is_optics_technician)
def dashboard(request):
    accepted_proposals = AccessProposal.objects.filter(
        status="accepted",
        facility_optics=True,
        optics_sessions__isnull=True,
    ).order_by("-created_at")
    sessions = (
        OpticsSession.objects
        .select_related("access_proposal", "technician")
        .annotate(sample_count=Count("samples"))
        .order_by("-created_at")
    )
    accepted_count = AccessProposal.objects.filter(
        facility_optics=True,
        status="accepted",
    ).count()
    return render(
        request,
        "sigmaoptics_icts/dashboard.html",
        {
            "accepted_count": accepted_count,
            "session_count": sessions.count(),
            "accepted_proposals": accepted_proposals,
            "sessions": sessions,
        },
    )


@login_required_icts
@user_passes_test(is_optics_technician)
def equipment_list(request):
    query = (request.GET.get("q") or "").strip()
    equipments = OpticsEquipment.objects.all()
    if query:
        equipments = equipments.filter(
            Q(code__icontains=query)
            | Q(description__icontains=query)
            | Q(responsible__icontains=query)
            | Q(location__icontains=query)
        )
    last_update = OpticsEquipment.objects.aggregate(last_update=Max("updated_at"))["last_update"]
    return render(
        request,
        "sigmaoptics_icts/equipment_list.html",
        {
            "equipments": equipments,
            "query": query,
            "last_update": last_update,
            "can_edit": is_optics_responsable(request.user),
        },
    )


@login_required_icts
@user_passes_test(is_optics_technician)
def equipment_detail(request, equipment_id):
    equipment = get_object_or_404(
        OpticsEquipment.objects.prefetch_related(
            "doc_refs",
            "maintenance_activities",
            "maintenance_records",
            "incidents",
        ),
        pk=equipment_id,
    )
    context = _build_equipment_detail_context(request, equipment)
    return render(request, "sigmaoptics_icts/equipment_detail.html", context)


@login_required_icts
@user_passes_test(is_optics_responsable)
def equipment_create(request):
    if request.method == "POST":
        form = OpticsEquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, "Equipo Optics creado.")
            return redirect("sigmaoptics_icts:equipment_detail", equipment_id=equipment.pk)
    else:
        form = OpticsEquipmentForm()
    return render(
        request,
        "sigmaoptics_icts/equipment_form.html",
        {"form": form, "is_create": True},
    )


@login_required_icts
@user_passes_test(is_optics_responsable)
def equipment_edit(request, equipment_id):
    equipment = get_object_or_404(OpticsEquipment, pk=equipment_id)
    if request.method == "POST":
        form = OpticsEquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, "Equipo Optics actualizado.")
            return redirect("sigmaoptics_icts:equipment_detail", equipment_id=equipment.pk)
    else:
        form = OpticsEquipmentForm(instance=equipment)
    return render(
        request,
        "sigmaoptics_icts/equipment_form.html",
        {"form": form, "is_create": False, "equipment": equipment},
    )


@login_required_icts
@user_passes_test(is_optics_responsable)
def equipment_docref_add(request, equipment_id):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")
    equipment = get_object_or_404(OpticsEquipment, pk=equipment_id)
    form = OpticsEquipmentDocRefForm(request.POST, request.FILES)
    if form.is_valid():
        docref = form.save(commit=False)
        docref.equipment = equipment
        docref.uploaded_by = request.user
        docref.save()
        messages.success(request, "Documento Optics subido.")
        return redirect("sigmaoptics_icts:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(request, equipment, {"docref_form": form})
    return render(request, "sigmaoptics_icts/equipment_detail.html", context)


@login_required_icts
@user_passes_test(is_optics_responsable)
def equipment_maintenance_activity_add(request, equipment_id):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")
    equipment = get_object_or_404(OpticsEquipment, pk=equipment_id)
    form = OpticsMaintenanceActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.equipment = equipment
        activity.save()
        messages.success(request, "Actividad creada.")
        return redirect("sigmaoptics_icts:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(
        request,
        equipment,
        {"maintenance_activity_form": form},
    )
    return render(request, "sigmaoptics_icts/equipment_detail.html", context)


@login_required_icts
@user_passes_test(is_optics_responsable)
def equipment_maintenance_record_add(request, equipment_id):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")
    equipment = get_object_or_404(OpticsEquipment, pk=equipment_id)
    form = OpticsMaintenanceRecordForm(request.POST)
    if form.is_valid():
        record = form.save(commit=False)
        record.equipment = equipment
        record.save()
        messages.success(request, "Registro de mantenimiento creado.")
        return redirect("sigmaoptics_icts:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(
        request,
        equipment,
        {"maintenance_record_form": form},
    )
    return render(request, "sigmaoptics_icts/equipment_detail.html", context)


@login_required_icts
@user_passes_test(is_optics_responsable)
def equipment_incident_add(request, equipment_id):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")
    equipment = get_object_or_404(OpticsEquipment, pk=equipment_id)
    form = OpticsEquipmentIncidentForm(request.POST, request.FILES)
    if form.is_valid():
        incident = form.save(commit=False)
        incident.equipment = equipment
        incident.save()
        messages.success(request, "Incidencia registrada.")
        return redirect("sigmaoptics_icts:equipment_detail", equipment_id=equipment.pk)
    context = _build_equipment_detail_context(request, equipment, {"incident_form": form})
    return render(request, "sigmaoptics_icts/equipment_detail.html", context)


@login_required_icts
@user_passes_test(is_optics_technician)
def equipment_docref_download(request, docref_id):
    docref = get_object_or_404(OpticsEquipmentDocRef, pk=docref_id)
    if not docref.file:
        raise Http404("Documento no disponible.")
    filename = docref.file.name.rsplit("/", 1)[-1]
    return FileResponse(docref.file.open("rb"), as_attachment=True, filename=filename)


@login_required_icts
@user_passes_test(is_optics_technician)
def equipment_incident_download(request, incident_id):
    incident = get_object_or_404(OpticsEquipmentIncident, pk=incident_id)
    if not incident.attachment:
        raise Http404("Adjunto no disponible.")
    filename = incident.attachment.name.rsplit("/", 1)[-1]
    return FileResponse(incident.attachment.open("rb"), as_attachment=True, filename=filename)


@login_required_icts
@user_passes_test(is_optics_technician)
def annual_plan_view(request):
    year_raw = request.GET.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year

    plan = OpticsAnnualPlan.objects.filter(year=year).first()
    preview = False
    source_plan = None
    if plan:
        entries = (
            OpticsAnnualPlanEntry.objects
            .filter(plan=plan)
            .select_related("equipment")
        )
    else:
        source_plan = (
            OpticsAnnualPlan.objects
            .filter(year__lt=year)
            .order_by("-year")
            .first()
        )
        if source_plan:
            preview = True
            entries = (
                OpticsAnnualPlanEntry.objects
                .filter(plan=source_plan)
                .select_related("equipment")
            )
        else:
            entries = OpticsAnnualPlanEntry.objects.none()

    return render(
        request,
        "sigmaoptics_icts/annual_plan.html",
        {
            "plan": plan,
            "preview": preview,
            "source_plan": source_plan,
            "year": year,
            "year_form": OpticsAnnualPlanYearForm(initial={"year": year}),
            "entries": entries,
            "can_edit": is_optics_responsable(request.user),
        },
    )


@login_required_icts
@user_passes_test(is_optics_responsable)
def annual_plan_copy_previous(request):
    if request.method != "POST":
        return _annual_plan_redirect(timezone.now().year)
    year_raw = request.POST.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year

    if OpticsAnnualPlan.objects.filter(year=year).exists():
        messages.info(request, "El plan anual ya existe para ese ano.")
        return _annual_plan_redirect(year)

    source_plan = (
        OpticsAnnualPlan.objects
        .filter(year__lt=year)
        .order_by("-year")
        .first()
    )
    if not source_plan:
        messages.warning(request, "No hay plan anterior para copiar.")
        return _annual_plan_redirect(year)

    with transaction.atomic():
        plan = OpticsAnnualPlan.objects.create(year=year)
        source_entries = OpticsAnnualPlanEntry.objects.filter(plan=source_plan).select_related("equipment")
        created_count = 0
        for source in source_entries:
            entry = OpticsAnnualPlanEntry.objects.create(
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
                OpticsAnnualPlanChangeLog.ACTION_CREATE,
                entry=entry,
                after_data=_annual_plan_entry_snapshot(entry),
            )
        _log_annual_plan_change(
            plan,
            request.user,
            OpticsAnnualPlanChangeLog.ACTION_COPY,
            message=f"Copia desde {source_plan.year} ({created_count} entradas).",
            after_data={"source_year": source_plan.year, "entries_copied": created_count},
        )

    messages.success(request, "Plan anual copiado.")
    return _annual_plan_redirect(year)


@login_required_icts
@user_passes_test(is_optics_technician)
def annual_plan_history(request):
    year_raw = request.GET.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year

    plan = OpticsAnnualPlan.objects.filter(year=year).first()
    logs = []
    if plan:
        logs = list(
            OpticsAnnualPlanChangeLog.objects
            .filter(plan=plan)
            .select_related("user", "entry")
            .order_by("-created_at", "-id")
        )

    activity_labels = dict(OpticsAnnualPlanEntry.ACTIVITY_CHOICES)
    execution_labels = dict(OpticsAnnualPlanEntry.EXECUTION_CHOICES)
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
        "sigmaoptics_icts/annual_plan_history.html",
        {
            "plan": plan,
            "year": year,
            "log_rows": log_rows,
        },
    )


@login_required_icts
@user_passes_test(is_optics_responsable)
def annual_plan_entry_create(request):
    year_raw = request.GET.get("year")
    try:
        year = int(year_raw) if year_raw else timezone.now().year
    except ValueError:
        year = timezone.now().year
    plan, _created = OpticsAnnualPlan.objects.get_or_create(year=year)

    if request.method == "POST":
        form = OpticsAnnualPlanEntryForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.plan = plan
                entry.save()
                _log_annual_plan_change(
                    plan,
                    request.user,
                    OpticsAnnualPlanChangeLog.ACTION_CREATE,
                    entry=entry,
                    after_data=_annual_plan_entry_snapshot(entry),
                )
            messages.success(request, "Entrada del plan anual creada.")
            return _annual_plan_redirect(year)
    else:
        form = OpticsAnnualPlanEntryForm()
    return render(
        request,
        "sigmaoptics_icts/annual_plan_entry_form.html",
        {"form": form, "is_create": True, "year": year},
    )


@login_required_icts
@user_passes_test(is_optics_responsable)
def annual_plan_entry_edit(request, pk):
    entry = get_object_or_404(OpticsAnnualPlanEntry, pk=pk)
    plan = entry.plan
    year = plan.year
    if request.method == "POST":
        before_data = _annual_plan_entry_snapshot(entry)
        form = OpticsAnnualPlanEntryForm(request.POST, instance=entry)
        if form.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.plan = plan
                entry.save()
                _log_annual_plan_change(
                    plan,
                    request.user,
                    OpticsAnnualPlanChangeLog.ACTION_UPDATE,
                    entry=entry,
                    before_data=before_data,
                    after_data=_annual_plan_entry_snapshot(entry),
                )
            messages.success(request, "Entrada del plan anual actualizada.")
            return _annual_plan_redirect(year)
    else:
        form = OpticsAnnualPlanEntryForm(instance=entry)
    return render(
        request,
        "sigmaoptics_icts/annual_plan_entry_form.html",
        {"form": form, "is_create": False, "entry": entry, "year": year},
    )


@login_required_icts
@user_passes_test(is_optics_responsable)
def annual_plan_entry_delete(request, pk):
    entry = get_object_or_404(OpticsAnnualPlanEntry, pk=pk)
    year = entry.plan.year
    if request.method == "POST":
        with transaction.atomic():
            before_data = _annual_plan_entry_snapshot(entry)
            plan = entry.plan
            _log_annual_plan_change(
                plan,
                request.user,
                OpticsAnnualPlanChangeLog.ACTION_DELETE,
                entry=entry,
                before_data=before_data,
            )
            entry.delete()
            messages.success(request, "Entrada del plan anual eliminada.")
    return _annual_plan_redirect(year)


def _build_optics_report_pdf(session):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    def format_date(value):
        return value.strftime("%d/%m/%Y") if value else "-"

    report = getattr(session, "report", None)
    samples = list(session.samples.order_by("sequence"))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
    height = A4[1]

    def add_paragraph(text_obj, content, width=92):
        for line in textwrap.wrap(content, width=width):
            text_obj.textLine(line)

    client_name = _resolve_client_name(session)
    project_name = _resolve_project_name(session)
    determination = (report.determination if report else "") or "-"
    technique = (report.technique if report else "") or (session.measurement_magnitude or "-")

    text = pdf.beginText(50, height - 70)
    text.setFont("Helvetica-Bold", 13)
    text.textLine("INFORME DE RESULTADOS")
    text.textLine("")
    text.setFont("Helvetica", 11)
    text.textLine(f"Referencia: {session.report_code or '-'}")
    text.textLine(f"Solicitud: {session.request_code or '-'}")
    if client_name:
        text.textLine(f"Cliente: {client_name}")
    if project_name:
        text.textLine(f"Proyecto: {project_name}")
    text.textLine("")

    text.textLine("Datos del análisis:")
    text.textLine(f"Fecha entrada: {format_date(session.reception_date)}")
    text.textLine(f"Fecha análisis: {format_date(session.analysis_date)}")
    text.textLine(f"Fecha informe: {format_date(session.report_delivery_date)}")
    text.textLine(f"Determinación: {determination}")
    text.textLine(f"Procedimiento: {session.procedure_code or '-'}")
    text.textLine(f"Técnica: {technique}")
    text.textLine("")

    text.textLine("Datos de la muestra:")
    if not samples:
        text.textLine("No hay muestras registradas.")
    for sample in samples:
        summary = (
            f"Muestra {sample.sequence}: "
            f"Ref. {sample.identification or '-'}; "
            f"Nombre {sample.name or '-'}; "
            f"Material {sample.material or '-'}"
        )
        add_paragraph(text, summary)
        if sample.observations:
            add_paragraph(text, f"Observaciones: {sample.observations}")

    text.textLine("")
    legal_note = (
        "Este informe es válido únicamente para las muestras analizadas y no "
        "podrá reproducirse parcialmente sin autorización."
    )
    add_paragraph(text, legal_note)

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


@login_required_icts
@user_passes_test(is_optics_technician)
def create_session_from_proposal(request, proposal_id):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")

    proposal = get_object_or_404(
        AccessProposal,
        pk=proposal_id,
        status="accepted",
        facility_optics=True,
    )

    existing = OpticsSession.objects.filter(access_proposal=proposal).first()
    if existing:
        messages.info(request, "La sesion ya existe para esta propuesta.")
        return redirect("sigmaoptics_icts:session_detail", pk=existing.pk)

    payload = _get_optics_payload(proposal)
    session = OpticsSession(
        access_proposal=proposal,
        technician=request.user,
        reception_date=timezone.now().date(),
        measurement_magnitude=_resolve_measurement_magnitude(payload),
    )
    session.save()

    report_defaults = {
        "client_name": proposal.contact_person
        or proposal.applicant.get_full_name()
        or proposal.applicant.get_username(),
        "project": proposal.project_name or proposal.title or "",
        "technique": _resolve_measurement_type(payload),
    }
    OpticsReport.objects.get_or_create(session=session, defaults=report_defaults)

    material = str(payload.get("optics_material") or "").strip()
    samples_data = _extract_optics_samples(payload)
    created = 0
    sequence = 1
    for sample in samples_data:
        if not any([sample.get("identification"), sample.get("name"), sample.get("observations")]):
            continue
        OpticsSample.objects.create(
            session=session,
            sequence=sequence,
            identification=sample.get("identification", ""),
            name=sample.get("name", ""),
            observations=sample.get("observations", ""),
            material=material,
        )
        sequence += 1
        created += 1

    if created == 0:
        OpticsSample.objects.create(
            session=session,
            sequence=1,
            identification="Sample 1",
            material=material,
        )
        messages.warning(request, "Sesión creada con una muestra base sin datos importados.")
    else:
        messages.success(request, f"Sesión creada con {created} muestras importadas.")

    return redirect("sigmaoptics_icts:session_detail", pk=session.pk)


@login_required_icts
@user_passes_test(is_optics_technician)
def session_detail(request, pk):
    session = get_object_or_404(
        OpticsSession.objects.select_related("access_proposal", "technician"),
        pk=pk,
    )
    samples = list(session.samples.order_by("sequence"))
    report, _ = OpticsReport.objects.get_or_create(session=session)

    return render(
        request,
        "sigmaoptics_icts/session_detail.html",
        {
            "session": session,
            "samples": samples,
            "session_form": OpticsSessionForm(instance=session),
            "report": report,
        },
    )


@login_required_icts
@user_passes_test(is_optics_technician)
def session_update(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")

    session = get_object_or_404(OpticsSession, pk=pk)
    form = OpticsSessionForm(request.POST, instance=session)
    if form.is_valid():
        form.save()
        messages.success(request, "Sesión actualizada.")
    else:
        messages.error(request, "Revisa los datos de la sesión.")
    return redirect("sigmaoptics_icts:session_detail", pk=session.pk)


@login_required_icts
@user_passes_test(is_optics_technician)
def sample_add(request, session_id):
    session = get_object_or_404(OpticsSession, pk=session_id)
    if request.method == "POST":
        form = OpticsSampleForm(request.POST)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.session = session
            if not sample.sequence:
                max_seq = session.samples.aggregate(max_seq=Max("sequence")).get("max_seq") or 0
                sample.sequence = max_seq + 1
            sample.save()
            messages.success(request, "Muestra añadida.")
            return redirect("sigmaoptics_icts:session_detail", pk=session.pk)
    else:
        next_seq = session.samples.aggregate(max_seq=Max("sequence")).get("max_seq") or 0
        form = OpticsSampleForm(initial={"sequence": next_seq + 1})

    return render(
        request,
        "sigmaoptics_icts/sample_form.html",
        {"form": form, "session": session, "editing": False},
    )


@login_required_icts
@user_passes_test(is_optics_technician)
def sample_edit(request, pk):
    sample = get_object_or_404(OpticsSample, pk=pk)
    session = sample.session
    if request.method == "POST":
        form = OpticsSampleForm(request.POST, instance=sample)
        if form.is_valid():
            form.save()
            messages.success(request, "Muestra actualizada.")
            return redirect("sigmaoptics_icts:session_detail", pk=session.pk)
    else:
        form = OpticsSampleForm(instance=sample)

    return render(
        request,
        "sigmaoptics_icts/sample_form.html",
        {"form": form, "session": session, "editing": True, "sample": sample},
    )


@login_required_icts
@user_passes_test(is_optics_technician)
def report_edit(request, session_id):
    session = get_object_or_404(OpticsSession, pk=session_id)
    report, _created = OpticsReport.objects.get_or_create(
        session=session,
        defaults={
            "client_name": _resolve_client_name(session),
            "project": _resolve_project_name(session),
        },
    )

    if request.method == "POST":
        form = OpticsReportForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, "Informe actualizado.")
            return redirect("sigmaoptics_icts:session_detail", pk=session.pk)
    else:
        form = OpticsReportForm(instance=report)

    return render(
        request,
        "sigmaoptics_icts/report_form.html",
        {"form": form, "session": session},
    )


@login_required_icts
@user_passes_test(is_optics_technician)
def report_pdf_download(request, session_id):
    session = get_object_or_404(OpticsSession, pk=session_id)
    report, _ = OpticsReport.objects.get_or_create(session=session)
    if not session.report_pdf:
        pdf_bytes = _build_optics_report_pdf(session)
        filename = f"Informe_resultados_{session.report_code or session.pk}.pdf"
        session.report_pdf.save(filename, ContentFile(pdf_bytes), save=False)
        session.save(update_fields=["report_pdf"])
    filename = session.report_pdf.name.rsplit("/", 1)[-1]
    return FileResponse(session.report_pdf.open("rb"), as_attachment=True, filename=filename)


@login_required_icts
@user_passes_test(is_optics_technician)
def register_view(request):
    samples = (
        OpticsSample.objects
        .select_related("session", "session__access_proposal", "session__technician")
        .order_by("-session__created_at", "sequence")
    )
    rows = []
    for sample in samples:
        session = sample.session
        applicant_name = _resolve_client_name(session)
        rows.append(
            {
                "session": session,
                "sample": sample,
                "applicant": applicant_name,
                "request_code": session.request_code,
                "report_code": session.report_code,
                "reception_date": session.reception_date,
                "analysis_date": session.analysis_date,
                "report_delivery_date": session.report_delivery_date,
                "measurement_magnitude": session.measurement_magnitude,
                "technician": session.technician,
            }
        )

    return render(
        request,
        "sigmaoptics_icts/register.html",
        {"rows": rows},
    )
