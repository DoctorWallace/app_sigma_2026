import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from sigmaconf.models import LO3ReferenceMaterial


@pytest.mark.django_db
def test_import_lo3_reference_materials_idempotent(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "LISTADO MR"
    sheet.append(
        [
            "Codigo",
            "Descripcion",
            "Referencia",
            "Responsable",
            "Localizacion",
            "Fecha recepcion",
            "Caducidad",
            "Observaciones",
        ]
    )
    sheet.append(
        [
            "MR-01",
            "Material 1",
            "REF-1",
            "Resp 1",
            "Almacen",
            "2024-01-10",
            "2025-01-10",
            "Ok",
        ]
    )
    sheet.append(
        [
            "MR-02",
            "Material 2",
            "REF-2",
            "Resp 2",
            "Almacen",
            "2023-01-10",
            "2023-02-10",
            "Caducado",
        ]
    )

    file_path = tmp_path / "mr.xlsx"
    workbook.save(file_path)

    call_command("import_lo3_reference_materials", "--file", str(file_path))
    assert LO3ReferenceMaterial.objects.count() == 2

    call_command("import_lo3_reference_materials", "--file", str(file_path))
    assert LO3ReferenceMaterial.objects.count() == 2

    expired = LO3ReferenceMaterial.objects.get(code="MR-02")
    assert expired.status == "retired"


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
def test_reference_material_due_flags(client):
    technician = _create_user("lo3_tech_mr", ["confocal_technicians"])
    today = timezone.localdate()
    LO3ReferenceMaterial.objects.create(
        code="MR-01",
        description="Material",
        expiry_date=today + timezone.timedelta(days=10),
    )
    LO3ReferenceMaterial.objects.create(
        code="MR-02",
        description="Material",
        expiry_date=today - timezone.timedelta(days=1),
    )
    LO3ReferenceMaterial.objects.create(
        code="MR-03",
        description="Material",
        status="retired",
    )

    client.force_login(technician)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:lo3_reference_material_list"))
    assert response.status_code == 200
    materials = response.context["materials"]
    status_map = {material.code: material.status_style for material in materials}
    assert status_map["MR-01"] == "due_soon"
    assert status_map["MR-02"] == "expired"
    assert status_map["MR-03"] == "retired"
