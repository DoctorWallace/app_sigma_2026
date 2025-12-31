import pytest
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from sigmavdg.models import VDGItem, VDGItemMovement


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
def test_vdg_item_movement_flow(client):
    tech = _create_user("vdg_item_tech", ["vdg_technicians"])
    item = VDGItem.objects.create(code="ITEM-01", description="Item test")

    client.force_login(tech)
    _set_icts_session(client)

    fecha_salida = timezone.localdate()
    response = client.post(
        reverse("sigmavdg:vdg_item_movement_create"),
        data={
            "item": item.pk,
            "fecha_salida": fecha_salida.isoformat(),
            "motivo_salida": "Revision",
            "forma_envio": "Mensajeria",
            "destino": "Proveedor",
            "responsable_destino": "Responsable",
            "cumplimentado_por_salida": "Tecnico",
            "notas": "Salida inicial",
        },
    )
    assert response.status_code == 302

    movement = VDGItemMovement.objects.get(item=item)
    assert movement.fecha_salida == fecha_salida

    response = client.post(
        reverse("sigmavdg:vdg_item_movement_receive", args=[movement.pk]),
        data={
            "fecha_entrada": (fecha_salida - timedelta(days=1)).isoformat(),
            "estado_recepcion": "ok",
            "estado_recepcion_detalle": "",
            "cumplimentado_por_entrada": "Tecnico",
            "notas": "Entrada invalida",
        },
    )
    assert response.status_code == 200
    movement.refresh_from_db()
    assert movement.fecha_entrada is None

    response = client.post(
        reverse("sigmavdg:vdg_item_movement_receive", args=[movement.pk]),
        data={
            "fecha_entrada": fecha_salida.isoformat(),
            "estado_recepcion": "ok",
            "estado_recepcion_detalle": "",
            "cumplimentado_por_entrada": "Tecnico",
            "notas": "Entrada correcta",
        },
    )
    assert response.status_code == 302
    movement.refresh_from_db()
    assert movement.fecha_entrada == fecha_salida
