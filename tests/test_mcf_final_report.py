import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from icts.models import AccessProposal
from sigmaconf.models import MCFSession


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


def _set_icts_session(client):
    session = client.session
    session["module"] = "icts"
    session.save()


@pytest.mark.django_db
def test_mcf_final_report_permissions(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_applicant_fr", ["icts_users"])
    technician = _create_user("lo3_tech_fr", ["confocal_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="LO3 Proposal",
        status="accepted",
        facility_confocal=True,
        access_code="ACC-LO3-002",
        facility_data={},
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=technician)

    client.force_login(technician)
    _set_icts_session(client)

    pdf_file = SimpleUploadedFile(
        "informe.pdf",
        b"%PDF-1.4\n%LO3 final report",
        content_type="application/pdf",
    )
    response = client.post(
        reverse("sigmaconf:mcf_final_report_upload", args=[session.pk]),
        data={"file": pdf_file},
    )
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.final_report_pdf
    assert session.final_report_uploaded_by == technician

    response = client.get(reverse("sigmaconf:mcf_final_report_download", args=[session.pk]))
    assert response.status_code == 200

    client.force_login(applicant)
    _set_icts_session(client)

    pdf_file = SimpleUploadedFile(
        "otro.pdf",
        b"%PDF-1.4\n%should not upload",
        content_type="application/pdf",
    )
    response = client.post(
        reverse("sigmaconf:mcf_final_report_upload", args=[session.pk]),
        data={"file": pdf_file},
    )
    assert response.status_code == 403

    response = client.get(reverse("sigmaconf:mcf_final_report_download", args=[session.pk]))
    assert response.status_code == 200
