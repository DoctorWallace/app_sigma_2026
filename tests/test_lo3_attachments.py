import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from sigmaconf.models import LO3Attachment, MCFSession, MCFSampleRecord


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
def test_lo3_attachments_permissions(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_applicant_att", ["icts_users"])
    technician = _create_user("lo3_tech_att", ["confocal_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="LO3 Proposal",
        status="accepted",
        facility_confocal=True,
        access_code="ACC-LO3-005",
        facility_data={},
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=technician)
    sample = MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        identification="S-001",
        analysis_date=timezone.now().date(),
        roughness=True,
    )

    client.force_login(technician)
    _set_icts_session(client)

    session_file = SimpleUploadedFile(
        "foto.jpg",
        b"fake-image",
        content_type="image/jpeg",
    )
    response = client.post(
        reverse("sigmaconf:mcf_session_attachment_add", args=[session.pk]),
        data={
            "attachment_type": "photo",
            "description": "Foto de sesi\u00f3n",
            "file": session_file,
        },
    )
    assert response.status_code == 302
    assert LO3Attachment.objects.filter(session=session).exists()

    sample_file = SimpleUploadedFile(
        "raw.dat",
        b"raw-data",
        content_type="application/octet-stream",
    )
    response = client.post(
        reverse("sigmaconf:mcf_sample_attachment_add", args=[sample.pk]),
        data={
            "attachment_type": "rawdata",
            "description": "Raw data",
            "file": sample_file,
        },
    )
    assert response.status_code == 302
    sample_attachment = LO3Attachment.objects.get(sample=sample)

    download_url = reverse(
        "sigmaconf:mcf_attachment_download", args=[sample_attachment.pk]
    )
    response = client.get(download_url)
    assert response.status_code == 200

    client.force_login(applicant)
    _set_icts_session(client)

    blocked_file = SimpleUploadedFile(
        "no.txt",
        b"blocked",
        content_type="text/plain",
    )
    response = client.post(
        reverse("sigmaconf:mcf_session_attachment_add", args=[session.pk]),
        data={
            "attachment_type": "other",
            "description": "No permitido",
            "file": blocked_file,
        },
    )
    assert response.status_code == 403

    response = client.get(download_url)
    assert response.status_code == 200

    response = client.post(
        reverse("sigmaconf:mcf_attachment_delete", args=[sample_attachment.pk])
    )
    assert response.status_code == 403
