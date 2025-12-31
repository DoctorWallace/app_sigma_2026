import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from sigmaconf.models import LO3Equipment, LO3Habilitation


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
def test_lo3_habilitation_permissions(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    principal = _create_user("lo3_principal", ["tecnico_responsable_s_conf"])
    technician = _create_user("lo3_tech_plain", ["confocal_technicians"])
    investigator = _create_user("lo3_investigator", ["icts_users"])

    equipment = LO3Equipment.objects.create(name="DCM8")

    client.force_login(technician)
    _set_icts_session(client)
    response = client.post(
        reverse("sigmaconf:lo3_habilitation_create"),
        data={
            "investigator_user": investigator.pk,
            "equipment": equipment.pk,
            "issued_at": timezone.localdate().isoformat(),
        },
    )
    assert response.status_code == 403

    client.force_login(principal)
    _set_icts_session(client)
    response = client.post(
        reverse("sigmaconf:lo3_habilitation_create"),
        data={
            "investigator_user": investigator.pk,
            "equipment": equipment.pk,
            "issued_at": timezone.localdate().isoformat(),
            "valid_until": (timezone.localdate()).isoformat(),
        },
    )
    assert response.status_code == 302
    habilitation = LO3Habilitation.objects.get(investigator_user=investigator)
    assert habilitation.certificate_pdf
    assert habilitation.issued_by == principal

    response = client.post(
        reverse("sigmaconf:lo3_habilitation_revoke", args=[habilitation.pk]),
        data={"revoke_reason": "Motivo"},
    )
    assert response.status_code == 302
    habilitation.refresh_from_db()
    assert habilitation.status == "revoked"

    client.force_login(investigator)
    _set_icts_session(client)
    response = client.get(
        reverse("sigmaconf:lo3_habilitation_download", args=[habilitation.pk])
    )
    assert response.status_code == 200
