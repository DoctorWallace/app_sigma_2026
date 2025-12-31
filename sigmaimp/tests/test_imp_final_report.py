import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from icts.models import AccessProposal
from sigmaimp.models import IMPSession


def _create_user(username, groups=None):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups or []:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_imp_final_report_upload_permissions(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tech = _create_user("imp_report_tech", ["implant_technicians"])
    applicant = _create_user("imp_report_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="IMP Report",
        facility_imp=True,
        status="accepted",
    )
    session = IMPSession.objects.create(access_proposal=proposal, technician=tech)

    pdf_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 test")

    client.force_login(applicant)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.post(
        reverse("sigmaimp:imp_final_report_upload", args=[session.pk]),
        {"file": pdf_file},
    )
    assert response.status_code == 403

    client.force_login(tech)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    pdf_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 test")
    response = client.post(
        reverse("sigmaimp:imp_final_report_upload", args=[session.pk]),
        {"file": pdf_file},
    )
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.final_report_pdf
    assert session.final_report_uploaded_by == tech

    client.force_login(applicant)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.get(reverse("sigmaimp:imp_final_report_download", args=[session.pk]))
    assert response.status_code == 200
