import pytest
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from docx import Document

from icts.models import AccessProposal
from icts.sigmasims.models import SIMSRecord, SIMSReport, SIMSReportImage


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_sigmasims_report_export_docx(client):
    applicant = _create_user("sims_applicant", ["icts_users"])
    tech = _create_user("sims_docx", ["tecnicos_sims"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="SIMS Proposal",
        facility_sims=True,
        access_code="SIMS_REQ_001",
    )

    report = SIMSReport.objects.create(
        access_proposal=proposal,
        determination="Det",
        technique_text="Tech",
        sample_description="Desc",
        measurement_conditions="Cond",
        results_text="Res",
        conclusions="Conc",
    )
    SIMSRecord.objects.create(
        access_proposal=proposal,
        reception_date=date(2025, 2, 1),
        analysis_date=date(2025, 2, 2),
        sample_identification="Sample A",
        client_name="Client A",
        sample_characteristics="Chars",
        responsible_name="Resp",
        client_requirements="Req",
    )

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01"
        b"\x01\x01\x00\x18\xdd\x8d\xbb\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    SIMSReportImage.objects.create(
        report=report,
        image=SimpleUploadedFile("image.png", png_bytes, content_type="image/png"),
        caption="Grafica",
    )

    client.force_login(tech)
    response = client.get(reverse("icts:sigmasims:report_export_docx", args=[proposal.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    doc = Document(BytesIO(response.content))
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    assert "INFORME DE RESULTADOS" in text
    assert "SIMS_REQ_001" in text
