from datetime import date
from io import BytesIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from docx import Document
from docx.shared import Inches
from openpyxl import Workbook

from icts.auth_utils import TECH_SIMS_GROUPS, get_normalized_user_groups, user_in_groups
from icts.models import AccessProposal
from .forms import SIMSRecordForm, SIMSReportForm, SIMSDocumentForm
from .models import (
    SIMSRecord,
    SIMSReport,
    SIMSReportImage,
    SIMSReportFile,
    SIMSDocument,
)


def is_sims_technician(user):
    """Verifica si el usuario es técnico SIMS."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
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


def _autofill_from_proposal(record):
    if not record.access_proposal:
        return
    applicant = record.access_proposal.applicant
    name = (applicant.get_full_name() or applicant.get_username()).strip()
    if name and not record.client_name:
        record.client_name = name
    if not record.request_code:
        record.request_code = record.access_proposal.access_code or ""


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


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_sims_technician)
def dashboard(request):
    return render(request, "sigmasims/dashboard.html", {})


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
    if request.method == "POST":
        form = SIMSRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            _autofill_from_proposal(record)
            record.save()
            messages.success(request, "Registro SIMS creado.")
            return redirect("icts:sigmasims:record_list")
    else:
        form = SIMSRecordForm()
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
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Registro SIMS"

    headers = [
        "Número ID",
        "Número de solicitud",
        "FECHA",
        "Identificación muestra",
        "Cliente",
        "Características de la muestra",
        "Responsable",
        "Requerimientos cliente",
        "Fecha del análisis",
        "Fecha de devolución",
        "Observaciones e Incidencias",
        "Indicador de Calidad (I1 días)",
        "Comentarios",
    ]
    sheet.append(headers)

    for record in records:
        sheet.append(
            [
                record.sims_id,
                record.request_code,
                record.reception_date,
                record.sample_identification,
                record.client_name,
                record.sample_characteristics,
                record.responsible_name,
                record.client_requirements,
                record.analysis_date,
                record.return_date,
                record.incidents,
                record.i1_days,
                record.comments,
            ]
        )

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
    documents = SIMSDocument.objects.filter(is_active=True)
    return render(
        request,
        "sigmasims/docs_list.html",
        {"documents": documents},
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

    semester_data = []
    for idx, (start_date, end_date) in enumerate(_semester_ranges(year), start=1):
        i1_values = []
        records = SIMSRecord.objects.filter(
            analysis_date__range=(start_date, end_date),
            reception_date__isnull=False,
        )
        for record in records:
            if record.analysis_date and record.reception_date:
                i1_values.append((record.analysis_date - record.reception_date).days)

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

    return render(
        request,
        "sigmasims/indicators_dashboard.html",
        {"year": year, "semester_data": semester_data},
    )
