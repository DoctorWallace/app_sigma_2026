import re
import textwrap
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Count, Max, Q
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from icts.decorators import login_required_icts
from icts.auth_utils import (
    VDG_TECH_GROUPS,
    MANAGER_GROUPS,
    RESPONSABLE_GROUPS,
    get_normalized_user_groups,
    user_in_groups,
)
from icts.models import AccessProposal

from .forms import (
    VDGEquipmentDocumentForm,
    VDGEquipmentForm,
    VDGEquipmentIncidentForm,
    VDGItemForm,
    VDGItemMovementInForm,
    VDGItemMovementOutForm,
    VDGSampleRecordForm,
    VDGSessionCreateForm,
    VDGSessionUpdateForm,
)
from .models import (
    VDGEquipment,
    VDGEquipmentDocument,
    VDGEquipmentIncident,
    VDGItem,
    VDGItemMovement,
    VDGSampleRecord,
    VDGSession,
)


def _vdg_access_flags(user):
    groups = get_normalized_user_groups(user)
    is_privileged = user.is_staff or user.is_superuser
    is_tech = user_in_groups(user, VDG_TECH_GROUPS, groups) or is_privileged
    return is_tech, is_privileged


def _is_vdg_blocked(user, groups=None):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff or user.is_superuser:
        return False
    groups = groups or get_normalized_user_groups(user)
    if user_in_groups(user, VDG_TECH_GROUPS, groups):
        return False
    return user_in_groups(user, RESPONSABLE_GROUPS | MANAGER_GROUPS, groups)


def _ensure_vdg_technician(request):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        messages.error(request, "No tienes permisos para acceder a esta seccion.")
        return False
    return True


def _can_edit_session(user, session):
    groups = get_normalized_user_groups(user)
    if _is_vdg_blocked(user, groups):
        return False
    is_tech = user_in_groups(user, VDG_TECH_GROUPS, groups)
    is_privileged = user.is_staff or user.is_superuser
    return (is_tech and session.technician_id == user.id) or is_privileged


def _can_view_session(user, session):
    groups = get_normalized_user_groups(user)
    if _is_vdg_blocked(user, groups):
        return False, True
    is_tech = user_in_groups(user, VDG_TECH_GROUPS, groups)
    is_applicant = session.access_proposal.applicant_id == user.id
    is_privileged = user.is_staff or user.is_superuser
    allowed = is_applicant or is_tech or is_privileged
    can_edit = (is_tech and session.technician_id == user.id) or is_privileged
    read_only = not can_edit
    return allowed, read_only


def _parse_vdg_samples(vdg_data):
    if not isinstance(vdg_data, dict):
        return []
    pattern = re.compile(
        r"^vdg_sample_(\d+)_(code|material|electron_fluence|temperature|atmosphere|sample_size|sample_geometry)$"
    )
    grouped = {}
    for key, value in vdg_data.items():
        match = pattern.match(key)
        if not match:
            continue
        idx = int(match.group(1))
        field = match.group(2)
        grouped.setdefault(idx, {})[field] = value
    return [grouped[idx] for idx in sorted(grouped.keys())]


def _build_notice_pdf(session):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
    height = A4[1]

    proposal = session.access_proposal
    access_code = proposal.access_code or f"#{proposal.id}"
    applicant_name = (
        proposal.contact_person
        or proposal.applicant.get_full_name()
        or proposal.applicant.get_username()
    )
    profile = getattr(proposal.applicant, "icts_profile", None)
    center = (getattr(profile, "center", "") or "").strip()
    address = (getattr(profile, "address", "") or "").strip()
    completion_date = (
        session.completed_at.date() if session.completed_at else timezone.now().date()
    )
    date_str = completion_date.strftime("%d/%m/%Y")

    default_title = "Responsable del laboratorio Van de Graaff (L07)"
    default_name = "Dra. Teresa Hernandez Diaz"
    responsible_title = getattr(settings, "VDG_RESPONSIBLE_TITLE", default_title) or default_title
    responsible_name = getattr(settings, "VDG_RESPONSIBLE_NAME", default_name) or default_name

    def add_paragraph(text_obj, content):
        for line in textwrap.wrap(content, width=90):
            text_obj.textLine(line)

    text = pdf.beginText(50, height - 70)
    text.setFont("Helvetica", 11)
    text.textLine(f"A la atencion de D/Dna {applicant_name}")
    if center:
        text.textLine(center)
    if address:
        text.textLine(address)
    text.textLine("")
    text.textLine(f"Madrid, {date_str}")
    text.textLine("")
    text.textLine("Estimado Sr/Sra.:")
    text.textLine("")
    add_paragraph(
        text,
        "Adjunto le enviamos el resultado de las determinaciones efectuadas mediante "
        f"Van de Graaff (L07) del lote: {session.lot_code}.",
    )
    text.textLine("")
    add_paragraph(
        text,
        "Puede encontrar dichos informes en su cuenta de usuario SIGMA ICTS, "
        f"asociados a la solicitud {access_code}.",
    )
    text.textLine("")
    text.textLine("Un cordial saludo")
    text.textLine("")
    text.textLine(responsible_title)
    text.textLine(responsible_name)

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def _build_report_pdf(session, samples):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    def format_date(value):
        return value.strftime("%d/%m/%Y") if value else "-"

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
    height = A4[1]

    proposal = session.access_proposal
    access_code = proposal.access_code or f"#{proposal.id}"
    applicant_name = (
        proposal.contact_person
        or proposal.applicant.get_full_name()
        or proposal.applicant.get_username()
    )
    profile = getattr(proposal.applicant, "icts_profile", None)
    center = (getattr(profile, "center", "") or "").strip()

    def add_paragraph(text_obj, content):
        for line in textwrap.wrap(content, width=90):
            text_obj.textLine(line)

    text = pdf.beginText(50, height - 70)
    text.setFont("Helvetica", 11)
    text.textLine("Informe de resultados - Van de Graaff (L07)")
    text.textLine("")
    text.textLine(f"Solicitante: {applicant_name}")
    if center:
        text.textLine(f"Centro: {center}")
    text.textLine(f"Solicitud: {access_code}")
    text.textLine(f"Lote: {session.lot_code}")
    text.textLine(f"Codigo informe: {session.report_code}")
    text.textLine("")
    text.textLine(f"Fecha recepcion: {format_date(session.received_date)}")
    text.textLine(
        "Fechas irradiacion: "
        f"{format_date(session.irradiation_start_date)}"
        f" - {format_date(session.irradiation_end_date)}"
    )
    text.textLine(f"Fecha emision informe: {format_date(session.report_issue_date)}")
    text.textLine(f"Fecha entrega informe: {format_date(session.report_delivery_date)}")
    text.textLine("")

    if session.observations:
        add_paragraph(text, f"Observaciones: {session.observations}")
        text.textLine("")

    text.textLine("Muestras:")
    for sample in samples:
        summary = (
            f"Muestra {sample.sequence}: Codigo {sample.code or '-'}; "
            f"Material {sample.material or '-'}; Fluencia solicitada {sample.electron_fluence or '-'}; "
            f"Temperatura {sample.temperature or '-'}; Atmosfera {sample.atmosphere or '-'}; "
            f"Tamano {sample.sample_size or '-'}; Geometria {sample.sample_geometry or '-'}; "
            f"Fluencia resultado {sample.fluence_result or '-'}; "
            f"Corriente {sample.current_na or '-'}; Tiempo {sample.time_minutes or '-'}"
        )
        add_paragraph(text, summary)

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


@login_required_icts
def vdg_home(request):
    groups = get_normalized_user_groups(request.user)
    if _is_vdg_blocked(request.user, groups):
        return HttpResponseForbidden("No autorizado.")
    if not _ensure_vdg_technician(request):
        return redirect("icts:dashboard")

    is_tech, is_privileged = _vdg_access_flags(request.user)
    sessions = VDGSession.objects.all() if is_privileged else VDGSession.objects.filter(technician=request.user)

    context = {
        "in_progress_count": sessions.filter(status="in_progress").count(),
        "completed_count": sessions.filter(status="completed").count(),
        "accepted_count": AccessProposal.objects.filter(status="accepted", facility_vdg=True).count(),
        "session_count": sessions.count(),
        "is_privileged": is_privileged,
        "is_tech": is_tech,
    }
    return render(request, "sigmavdg/vdg_home.html", context)


@login_required_icts
def vdg_dashboard(request):
    if not _ensure_vdg_technician(request):
        return redirect("icts:dashboard")

    is_tech, is_privileged = _vdg_access_flags(request.user)
    accepted_proposals = AccessProposal.objects.filter(
        status="accepted", facility_vdg=True, vdg_sessions__isnull=True
    ).order_by("-created_at")

    sessions_qs = VDGSession.objects.all() if is_privileged else VDGSession.objects.filter(technician=request.user)
    sessions = (
        sessions_qs.annotate(
            sample_count=Count("samples", distinct=True),
            extra_samples=Count("samples", filter=Q(samples__source="session"), distinct=True),
        )
        .order_by("-created_at")
    )

    context = {
        "accepted_proposals": accepted_proposals,
        "sessions": sessions,
        "in_progress_count": sessions_qs.filter(status="in_progress").count(),
        "completed_count": sessions_qs.filter(status="completed").count(),
        "is_privileged": is_privileged,
        "is_tech": is_tech,
    }
    return render(request, "sigmavdg/vdg_dashboard.html", context)


@login_required_icts
def vdg_create_session(request, proposal_id=None):
    if not _ensure_vdg_technician(request):
        return redirect("icts:dashboard")

    proposal = None
    if proposal_id:
        proposal = get_object_or_404(
            AccessProposal, pk=proposal_id, status="accepted", facility_vdg=True
        )

    if request.method == "POST":
        if proposal is None:
            form = VDGSessionCreateForm(request.POST)
            if not form.is_valid():
                return render(
                    request,
                    "sigmavdg/vdg_create_session.html",
                    {
                        "form": form,
                        "available_proposals": form.fields["access_proposal"].queryset,
                    },
                )
            proposal = form.cleaned_data["access_proposal"]

        session = VDGSession(access_proposal=proposal, technician=request.user)
        proposal_data = proposal.facility_data or {}
        if isinstance(proposal_data, dict):
            session.request_snapshot = proposal_data.get("vdg", {}) or {}
        session.save()

        samples_data = _parse_vdg_samples(session.request_snapshot)
        created = 0
        sequence = 1
        for sample in samples_data:
            code = str(sample.get("code") or "").strip()
            material = str(sample.get("material") or "").strip()
            if not code and not material:
                continue
            VDGSampleRecord.objects.create(
                session=session,
                sequence=sequence,
                source="proposal",
                code=code or material or f"Sample {sequence}",
                material=material,
                electron_fluence=str(sample.get("electron_fluence") or "").strip(),
                temperature=str(sample.get("temperature") or "").strip(),
                atmosphere=str(sample.get("atmosphere") or "").strip(),
                sample_size=str(sample.get("sample_size") or "").strip(),
                sample_geometry=str(sample.get("sample_geometry") or "").strip(),
            )
            sequence += 1
            created += 1

        if created == 0:
            VDGSampleRecord.objects.create(
                session=session,
                sequence=1,
                source="proposal",
                code="Sample 1",
            )
            messages.warning(request, "Sesion creada con una muestra base sin datos importados.")
        else:
            messages.success(request, f"Sesion creada con {created} muestras importadas.")

        return redirect("sigmavdg:vdg_session_detail", pk=session.pk)

    form = VDGSessionCreateForm(initial={"access_proposal": proposal} if proposal else None)
    if proposal:
        form.fields["access_proposal"].queryset = AccessProposal.objects.filter(pk=proposal.pk)

    available = AccessProposal.objects.filter(
        status="accepted", facility_vdg=True, vdg_sessions__isnull=True
    ).order_by("-created_at")
    return render(
        request,
        "sigmavdg/vdg_create_session.html",
        {"form": form, "available_proposals": available},
    )


@login_required_icts
def vdg_session_detail(request, pk):
    session = get_object_or_404(VDGSession, pk=pk)
    allowed, read_only = _can_view_session(request.user, session)
    if not allowed:
        messages.error(request, "No tienes permisos para acceder a esta sesion.")
        return redirect("icts:dashboard")

    samples = list(session.samples.order_by("sequence"))
    total_samples = len(samples)
    extra_samples = sum(1 for sample in samples if sample.source == "session")
    declared_samples = total_samples - extra_samples

    back_url = "sigmavdg:vdg_dashboard"
    if session.access_proposal.applicant_id == request.user.id:
        back_url = "icts:user_dashboard"

    context = {
        "session": session,
        "samples": samples,
        "read_only": read_only,
        "back_url": back_url,
        "sample_stats": {
            "total": total_samples,
            "declared": declared_samples,
            "extra": extra_samples,
        },
        "session_form": VDGSessionUpdateForm(instance=session),
    }
    return render(request, "sigmavdg/vdg_session_detail.html", context)


@login_required_icts
def vdg_session_update(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")

    session = get_object_or_404(VDGSession, pk=pk)
    if not _can_edit_session(request.user, session):
        return HttpResponseForbidden("No autorizado.")

    form = VDGSessionUpdateForm(request.POST, instance=session)
    if form.is_valid():
        form.save()
        messages.success(request, "Sesion actualizada.")
    else:
        messages.error(request, "Revisa los datos de la sesion.")
    return redirect("sigmavdg:vdg_session_detail", pk=session.pk)


@login_required_icts
def vdg_add_sample(request, pk):
    session = get_object_or_404(VDGSession, pk=pk)
    if not _can_edit_session(request.user, session):
        return HttpResponseForbidden("No autorizado.")

    if request.method == "POST":
        form = VDGSampleRecordForm(request.POST)
        if form.is_valid():
            sample = form.save(commit=False)
            sample.session = session
            sample.source = "session"
            max_seq = session.samples.aggregate(max_seq=Max("sequence")).get("max_seq") or 0
            sample.sequence = max_seq + 1
            sample.save()
            messages.success(request, "Muestra anadida correctamente.")
            return redirect("sigmavdg:vdg_session_detail", pk=session.pk)
    else:
        form = VDGSampleRecordForm()

    return render(
        request,
        "sigmavdg/vdg_sample_edit.html",
        {"form": form, "session": session, "editing": False},
    )


@login_required_icts
def vdg_sample_edit(request, pk):
    sample = get_object_or_404(VDGSampleRecord, pk=pk)
    session = sample.session
    if not _can_edit_session(request.user, session):
        return HttpResponseForbidden("No autorizado.")

    if request.method == "POST":
        form = VDGSampleRecordForm(request.POST, instance=sample)
        if form.is_valid():
            form.save()
            messages.success(request, "Muestra actualizada.")
            return redirect("sigmavdg:vdg_session_detail", pk=session.pk)
    else:
        form = VDGSampleRecordForm(instance=sample)

    return render(
        request,
        "sigmavdg/vdg_sample_edit.html",
        {"form": form, "session": session, "editing": True, "sample": sample},
    )


@login_required_icts
def vdg_finish_session(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")

    session = get_object_or_404(VDGSession, pk=pk)
    if not _can_edit_session(request.user, session):
        return HttpResponseForbidden("No autorizado.")

    session_fields = [
        "received_date",
        "irradiation_start_date",
        "irradiation_end_date",
        "report_issue_date",
        "report_delivery_date",
        "observations",
    ]
    if any(field in request.POST for field in session_fields):
        form = VDGSessionUpdateForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save()
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect("sigmavdg:vdg_session_detail", pk=session.pk)

    samples = list(session.samples.order_by("sequence"))
    if not samples:
        messages.error(request, "No hay muestras registradas para finalizar la sesion.")
        return redirect("sigmavdg:vdg_session_detail", pk=session.pk)

    errors = []
    for sample in samples:
        label = f"Muestra {sample.sequence}"
        code = (sample.code or "").strip()
        material = (sample.material or "").strip()
        if not code and not material:
            errors.append(f"{label}: falta el codigo o material.")

    if not session.received_date:
        errors.append("Sesion: falta la fecha de recepcion.")
    if not session.irradiation_start_date:
        errors.append("Sesion: falta la fecha de irradiacion.")
    if not session.report_issue_date and not session.report_delivery_date:
        errors.append("Sesion: indica la fecha de emision o entrega del informe.")

    if session.received_date and session.irradiation_start_date:
        if session.irradiation_start_date < session.received_date:
            errors.append("Sesion: irradiacion anterior a la recepcion.")
    if session.irradiation_end_date and session.irradiation_start_date:
        if session.irradiation_end_date < session.irradiation_start_date:
            errors.append("Sesion: fin de irradiacion anterior al inicio.")
    if session.report_issue_date and session.irradiation_end_date:
        if session.report_issue_date < session.irradiation_end_date:
            errors.append("Sesion: emision anterior al fin de irradiacion.")
    if session.report_issue_date and session.irradiation_start_date:
        if session.report_issue_date < session.irradiation_start_date:
            errors.append("Sesion: emision anterior a la irradiacion.")
    if session.report_delivery_date and session.irradiation_end_date:
        if session.report_delivery_date < session.irradiation_end_date:
            errors.append("Sesion: entrega anterior al fin de irradiacion.")
    if session.report_delivery_date and session.irradiation_start_date:
        if session.report_delivery_date < session.irradiation_start_date:
            errors.append("Sesion: entrega anterior a la irradiacion.")
    if session.report_delivery_date and session.report_issue_date:
        if session.report_delivery_date < session.report_issue_date:
            errors.append("Sesion: entrega anterior a la emision del informe.")

    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect("sigmavdg:vdg_session_detail", pk=session.pk)

    update_fields = []
    if session.status != "completed":
        session.status = "completed"
        update_fields.append("status")
    if not session.completed_at:
        session.completed_at = timezone.now()
        update_fields.append("completed_at")

    if not session.notice_pdf:
        pdf_bytes = _build_notice_pdf(session)
        filename = f"Aviso_resultados_{session.lot_code}.pdf"
        session.notice_pdf.save(filename, ContentFile(pdf_bytes), save=False)
        update_fields.append("notice_pdf")

    if not session.report_pdf:
        report_bytes = _build_report_pdf(session, samples)
        filename = f"Informe_resultados_{session.lot_code}.pdf"
        session.report_pdf.save(filename, ContentFile(report_bytes), save=False)
        update_fields.append("report_pdf")

    if update_fields:
        session.save(update_fields=update_fields)

    messages.success(request, "Sesion finalizada y documentos generados.")
    return redirect("sigmavdg:vdg_session_detail", pk=session.pk)


@login_required_icts
def vdg_notice_download(request, pk):
    session = get_object_or_404(VDGSession, pk=pk)
    allowed, _ = _can_view_session(request.user, session)
    if not allowed:
        return HttpResponseForbidden("No autorizado.")
    if not session.notice_pdf:
        raise Http404("Aviso no disponible.")
    filename = session.notice_pdf.name.rsplit("/", 1)[-1]
    return FileResponse(session.notice_pdf.open("rb"), as_attachment=True, filename=filename)


@login_required_icts
def vdg_report_download(request, pk):
    session = get_object_or_404(VDGSession, pk=pk)
    allowed, _ = _can_view_session(request.user, session)
    if not allowed:
        return HttpResponseForbidden("No autorizado.")
    if not session.report_pdf:
        raise Http404("Informe no disponible.")
    filename = session.report_pdf.name.rsplit("/", 1)[-1]
    return FileResponse(session.report_pdf.open("rb"), as_attachment=True, filename=filename)


@login_required_icts
def vdg_equipment_list(request):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    query = (request.GET.get("q") or "").strip()
    equipment_list = VDGEquipment.objects.all()
    if query:
        equipment_list = equipment_list.filter(
            Q(code__icontains=query) | Q(description__icontains=query)
        )

    context = {"equipment_list": equipment_list, "query": query}
    return render(request, "sigmavdg/vdg_equipment_list.html", context)


@login_required_icts
def vdg_equipment_detail(request, equipment_id):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    equipment = get_object_or_404(VDGEquipment, pk=equipment_id)
    documents = equipment.documents.select_related("uploaded_by")
    incidents = equipment.incidents.all()
    context = {
        "equipment": equipment,
        "documents": documents,
        "incidents": incidents,
        "document_form": VDGEquipmentDocumentForm(),
        "incident_form": VDGEquipmentIncidentForm(),
        "can_edit": is_tech,
    }
    return render(request, "sigmavdg/vdg_equipment_detail.html", context)


@login_required_icts
def vdg_equipment_create(request):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    if request.method == "POST":
        form = VDGEquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, "Equipo creado.")
            return redirect("sigmavdg:vdg_equipment_detail", equipment_id=equipment.pk)
    else:
        form = VDGEquipmentForm()

    return render(
        request,
        "sigmavdg/vdg_equipment_form.html",
        {"form": form, "is_editing": False},
    )


@login_required_icts
def vdg_equipment_edit(request, equipment_id):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    equipment = get_object_or_404(VDGEquipment, pk=equipment_id)
    if request.method == "POST":
        form = VDGEquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            form.save()
            messages.success(request, "Equipo actualizado.")
            return redirect("sigmavdg:vdg_equipment_detail", equipment_id=equipment.pk)
    else:
        form = VDGEquipmentForm(instance=equipment)

    return render(
        request,
        "sigmavdg/vdg_equipment_form.html",
        {"form": form, "equipment": equipment, "is_editing": True},
    )


@login_required_icts
def vdg_equipment_document_add(request, equipment_id):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    equipment = get_object_or_404(VDGEquipment, pk=equipment_id)
    form = VDGEquipmentDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.equipment = equipment
        document.uploaded_by = request.user
        document.save()
        messages.success(request, "Documento subido.")
    else:
        messages.error(request, "No se pudo subir el documento.")
    return redirect("sigmavdg:vdg_equipment_detail", equipment_id=equipment.pk)


@login_required_icts
def vdg_equipment_document_download(request, document_id):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    document = get_object_or_404(VDGEquipmentDocument, pk=document_id)
    filename = document.file.name.rsplit("/", 1)[-1]
    return FileResponse(document.file.open("rb"), as_attachment=True, filename=filename)


@login_required_icts
def vdg_equipment_incident_add(request, equipment_id):
    if request.method != "POST":
        return HttpResponseForbidden("Metodo no permitido.")
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    equipment = get_object_or_404(VDGEquipment, pk=equipment_id)
    form = VDGEquipmentIncidentForm(request.POST, request.FILES)
    if form.is_valid():
        incident = form.save(commit=False)
        incident.equipment = equipment
        incident.save()
        messages.success(request, "Incidencia registrada.")
    else:
        messages.error(request, "No se pudo registrar la incidencia.")
    return redirect("sigmavdg:vdg_equipment_detail", equipment_id=equipment.pk)


@login_required_icts
def vdg_equipment_incident_download(request, incident_id):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    incident = get_object_or_404(VDGEquipmentIncident, pk=incident_id)
    if not incident.attachment:
        raise Http404("Adjunto no disponible.")
    filename = incident.attachment.name.rsplit("/", 1)[-1]
    return FileResponse(
        incident.attachment.open("rb"), as_attachment=True, filename=filename
    )


@login_required_icts
def vdg_item_list(request):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    items = VDGItem.objects.all()
    context = {"items": items}
    return render(request, "sigmavdg/vdg_item_list.html", context)


@login_required_icts
def vdg_item_create(request):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    if request.method == "POST":
        form = VDGItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, "Item creado.")
            return redirect("sigmavdg:vdg_item_list")
    else:
        form = VDGItemForm()

    return render(request, "sigmavdg/vdg_item_form.html", {"form": form})


@login_required_icts
def vdg_item_movements(request):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    show_pending = request.GET.get("pending") in {"1", "true", "True"}
    movements = VDGItemMovement.objects.select_related("item").all()
    if show_pending:
        movements = movements.filter(fecha_entrada__isnull=True)
    movements = movements.order_by("-fecha_salida")

    context = {
        "movements": movements,
        "show_pending": show_pending,
    }
    return render(request, "sigmavdg/vdg_item_movements.html", context)


@login_required_icts
def vdg_item_movement_create(request):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    initial = {}
    item_id = request.GET.get("item")
    if item_id:
        try:
            initial["item"] = VDGItem.objects.get(pk=item_id)
        except VDGItem.DoesNotExist:
            pass

    if request.method == "POST":
        form = VDGItemMovementOutForm(request.POST, initial=initial)
        if form.is_valid():
            movement = form.save(commit=False)
            if not movement.cumplimentado_por_salida:
                movement.cumplimentado_por_salida = (
                    request.user.get_full_name() or request.user.get_username()
                )
            movement.save()
            messages.success(request, "Salida registrada.")
            return redirect("sigmavdg:vdg_item_movements")
    else:
        form = VDGItemMovementOutForm(initial=initial)

    return render(request, "sigmavdg/vdg_item_movement_form.html", {"form": form})


@login_required_icts
def vdg_item_movement_receive(request, movement_id):
    is_tech, _ = _vdg_access_flags(request.user)
    if not is_tech:
        return HttpResponseForbidden("No autorizado.")

    movement = get_object_or_404(VDGItemMovement, pk=movement_id)
    if request.method == "POST":
        form = VDGItemMovementInForm(request.POST, instance=movement)
        if form.is_valid():
            movement = form.save(commit=False)
            if not movement.cumplimentado_por_entrada:
                movement.cumplimentado_por_entrada = (
                    request.user.get_full_name() or request.user.get_username()
                )
            movement.save()
            messages.success(request, "Entrada registrada.")
            return redirect("sigmavdg:vdg_item_movements")
    else:
        form = VDGItemMovementInForm(instance=movement)

    context = {"form": form, "movement": movement}
    return render(request, "sigmavdg/vdg_item_movement_receive.html", context)
