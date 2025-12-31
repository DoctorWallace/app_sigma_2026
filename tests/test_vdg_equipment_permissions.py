import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from sigmavdg.models import VDGEquipment


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
def test_vdg_equipment_permissions(client):
    tech = _create_user("vdg_equipment_tech", ["vdg_technicians"])
    outsider = _create_user("vdg_equipment_outsider", ["icts_users"])
    equipment = VDGEquipment.objects.create(code="EQ-TEST")

    client.force_login(tech)
    _set_icts_session(client)

    response = client.get(reverse("sigmavdg:vdg_equipment_list"))
    assert response.status_code == 200

    client.force_login(outsider)
    _set_icts_session(client)

    response = client.get(reverse("sigmavdg:vdg_equipment_list"))
    assert response.status_code == 403

    response = client.get(reverse("sigmavdg:vdg_equipment_edit", args=[equipment.pk]))
    assert response.status_code == 403
