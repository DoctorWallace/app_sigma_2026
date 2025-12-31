import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from icts.models import AccessProposal
from sigmaconf.models import LO3Equipment, LO3Incident, MCFSession


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
def test_lo3_incident_permissions_and_status(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_applicant_inc", ["icts_users"])
    technician = _create_user("lo3_tech_inc", ["confocal_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="LO3 Proposal",
        status="accepted",
        facility_confocal=True,
        access_code="ACC-LO3-006",
        facility_data={},
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=technician)
    equipment = LO3Equipment.objects.create(name="DCM8")

    client.force_login(applicant)
    _set_icts_session(client)
    response = client.get(reverse("sigmaconf:lo3_incident_list"))
    assert response.status_code == 403

    client.force_login(technician)
    _set_icts_session(client)

    response = client.post(
        reverse("sigmaconf:lo3_incident_create"),
        data={
            "incident_type": "incidencia",
            "equipment": equipment.pk,
            "session": session.pk,
            "title": "Incidencia 1",
            "description": "Descripcion",
            "severity": "high",
            "status": "open",
            "corrective_actions": "",
        },
    )
    assert response.status_code == 302
    incident = LO3Incident.objects.get(title="Incidencia 1")
    assert incident.status == "open"

    response = client.post(reverse("sigmaconf:lo3_incident_close", args=[incident.pk]))
    assert response.status_code == 302
    incident.refresh_from_db()
    assert incident.status == "closed"
    assert incident.closed_at is not None

    response = client.post(
        reverse("sigmaconf:lo3_incident_edit", args=[incident.pk]),
        data={
            "incident_type": "incidencia",
            "equipment": equipment.pk,
            "session": session.pk,
            "title": "Incidencia 1",
            "description": "Descripcion",
            "severity": "medium",
            "status": "in_progress",
            "corrective_actions": "Seguimiento",
        },
    )
    assert response.status_code == 302
    incident.refresh_from_db()
    assert incident.status == "in_progress"
    assert incident.closed_at is None

    attach_file = SimpleUploadedFile(
        "evidencia.txt",
        b"evidencia",
        content_type="text/plain",
    )
    response = client.post(
        reverse("sigmaconf:lo3_incident_attachment_add", args=[incident.pk]),
        data={"file": attach_file},
    )
    assert response.status_code == 302
    attachment = incident.attachments.first()
    assert attachment is not None

    response = client.get(
        reverse("sigmaconf:lo3_incident_attachment_download", args=[attachment.pk])
    )
    assert response.status_code == 200
