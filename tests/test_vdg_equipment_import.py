import pytest
from django.core.management import call_command

from openpyxl import Workbook

from sigmavdg.models import VDGEquipment


@pytest.mark.django_db
def test_vdg_equipment_import_idempotent(tmp_path):
    file_path = tmp_path / "equipos.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "LISTADO EQUIPOS"
    ws.append(
        [
            "Codigo",
            "Descripcion",
            "Es patron",
            "Responsable",
            "Localizacion",
            "Fecha recepcion",
            "Fecha baja",
            "Marca",
            "Modelo",
            "Serie",
            "Rango",
            "Resolucion",
            "Tolerancia",
            "Observaciones",
        ]
    )
    ws.append(
        [
            "EQ-001",
            "Equipo principal",
            "SI",
            "Equipo VDG",
            "Laboratorio",
            "2024-01-15",
            "",
            "ACME",
            "VDG-100",
            "SN-01",
            "0-10",
            "0.01",
            "±0.1",
            "Observacion inicial",
        ]
    )
    wb.save(file_path)

    call_command("import_vdg_equipment_from_xlsx", "--file", str(file_path))
    assert VDGEquipment.objects.count() == 1

    call_command("import_vdg_equipment_from_xlsx", "--file", str(file_path))
    assert VDGEquipment.objects.count() == 1

    equipment = VDGEquipment.objects.get(code="EQ-001")
    assert equipment.is_reference is True
    assert equipment.brand == "ACME"
