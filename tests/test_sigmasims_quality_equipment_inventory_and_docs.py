import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from icts.sigmasims.models import SIMSEquipment, SIMSSparePartInventory, SIMSEquipmentDocRef


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
def test_sims_equipment_create_only_responsable(client):
    tech = _create_user("sims_tech_eq", ["tecnicos_sims"])
    resp = _create_user("sims_resp_eq", ["tecnico_responsable_s_sims"])

    create_url = reverse("icts:sigmasims:equipment_create")

    client.force_login(tech)
    r = client.get(create_url)
    assert r.status_code in {302, 403}

    # Un técnico NO debe poder crear (ni siquiera por POST)
    r = client.post(
        create_url,
        data={
            "code": "EQ-TEST-100",
            "description": "Equipo test",
            "is_reference": False,
            "responsible": "Resp",
            "location": "Sala 01",
            "received_date": "2024-01-01",
        },
    )
    assert r.status_code in {302, 403}
    assert not SIMSEquipment.objects.filter(code="EQ-TEST-100").exists()

    client.force_login(resp)
    r = client.post(
        create_url,
        data={
            "code": "EQ-TEST-100",
            "description": "Equipo test",
            "is_reference": False,
            "responsible": "Resp",
            "location": "Sala 01",
            "received_date": "2024-01-01",
        },
    )
    assert r.status_code == 302
    assert SIMSEquipment.objects.filter(code="EQ-TEST-100").exists()


@pytest.mark.django_db
def test_sims_inventory_create_only_responsable(client):
    tech = _create_user("sims_tech_inv", ["tecnicos_sims"])
    resp = _create_user("sims_resp_inv", ["tecnico_responsable_s_sims"])

    create_url = reverse("icts:sigmasims:inventory_create")

    client.force_login(tech)
    r = client.get(create_url)
    assert r.status_code in {302, 403}

    # Un técnico NO debe poder crear (ni siquiera por POST)
    r = client.post(
        create_url,
        data={
            "item_name": "Filamentos X",
            "stock_2024_01": 1,
            "stock_2024_06": 2,
            "next_orders": 3,
            "actions": "Comprar",
        },
    )
    assert r.status_code in {302, 403}
    assert not SIMSSparePartInventory.objects.filter(item_name="Filamentos X").exists()

    client.force_login(resp)
    r = client.post(
        create_url,
        data={
            "item_name": "Filamentos X",
            "stock_2024_01": 1,
            "stock_2024_06": 2,
            "next_orders": 3,
            "actions": "Comprar",
        },
    )
    assert r.status_code == 302
    assert SIMSSparePartInventory.objects.filter(item_name="Filamentos X").exists()


@pytest.mark.django_db
def test_sims_equipment_docref_upload_and_download_acl(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    tech = _create_user("sims_tech_doc", ["tecnicos_sims"])
    resp = _create_user("sims_resp_doc", ["tecnico_responsable_s_sims"])

    equipment = SIMSEquipment.objects.create(
        code="EQ-TEST-DOC",
        description="Equipo con docs",
    )

    add_url = reverse("icts:sigmasims:equipment_docref_add", args=[equipment.pk])

    # Técnico NO puede subir
    client.force_login(tech)
    file_obj = SimpleUploadedFile("manual.pdf", b"%PDF-1.4\n%doc", content_type="application/pdf")
    r = client.post(add_url, data={"title": "Manual", "doc_code": "DOC-1", "file": file_obj})
    assert r.status_code in {302, 403}
    assert SIMSEquipmentDocRef.objects.filter(equipment=equipment).count() == 0

    # Responsable SÍ puede subir
    client.force_login(resp)
    file_obj = SimpleUploadedFile("manual.pdf", b"%PDF-1.4\n%doc", content_type="application/pdf")
    r = client.post(add_url, data={"title": "Manual", "doc_code": "DOC-1", "file": file_obj})
    assert r.status_code == 302
    docref = SIMSEquipmentDocRef.objects.get(equipment=equipment)
    assert docref.title == "Manual"
    assert docref.doc_code == "DOC-1"
    assert docref.uploaded_by_id == resp.id
    assert docref.file

    # Técnico puede descargar
    client.force_login(tech)
    download_url = reverse("icts:sigmasims:equipment_docref_download", args=[docref.pk])
    r = client.get(download_url)
    assert r.status_code == 200
    assert "attachment" in (r.get("Content-Disposition", "").lower())
