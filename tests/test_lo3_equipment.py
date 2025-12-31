import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from sigmaconf.models import LO3Equipment, LO3EquipmentDocument


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
def test_lo3_equipment_crud_permissions(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    technician = _create_user("lo3_tech_eq", ["confocal_technicians"])
    applicant = _create_user("lo3_applicant_eq", ["icts_users"])

    client.force_login(technician)
    _set_icts_session(client)

    response = client.post(
        reverse("sigmaconf:lo3_equipment_create"),
        data={
            "name": "Leica DCM8",
            "manufacturer": "Leica",
            "model": "DCM8",
            "serial_number": "DCM8-001",
            "location": "LO3",
            "status": "active",
            "description": "Equipo confocal LO3.",
        },
    )
    assert response.status_code == 302
    equipment = LO3Equipment.objects.get(name="Leica DCM8")

    response = client.get(reverse("sigmaconf:lo3_equipment_detail", args=[equipment.pk]))
    assert response.status_code == 200

    doc_file = SimpleUploadedFile(
        "manual.pdf",
        b"%PDF-1.4\n%Manual",
        content_type="application/pdf",
    )
    response = client.post(
        reverse("sigmaconf:lo3_equipment_document_add", args=[equipment.pk]),
        data={"title": "Manual DCM8", "doc_type": "manual", "file": doc_file},
    )
    assert response.status_code == 302
    assert LO3EquipmentDocument.objects.filter(equipment=equipment).count() == 1

    client.force_login(applicant)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:lo3_equipment_list"))
    assert response.status_code == 403

    doc_file = SimpleUploadedFile(
        "otro.pdf",
        b"%PDF-1.4\n%No",
        content_type="application/pdf",
    )
    response = client.post(
        reverse("sigmaconf:lo3_equipment_document_add", args=[equipment.pk]),
        data={"title": "Manual", "doc_type": "manual", "file": doc_file},
    )
    assert response.status_code == 403
