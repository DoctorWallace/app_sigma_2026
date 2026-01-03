import pytest
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from dtf.models import DTFUserProfile
from sigmadp.models import DpMensaje, DpNecesidad


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass")
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_module(client, module="dtf"):
    session = client.session
    session["module"] = module
    session.save()


@pytest.mark.django_db
def test_sigmadp_inbox_scopes_messages_for_user(client):
    user_a = _create_user("dp_user_a", ["usuarios_dtf"])
    user_b = _create_user("dp_user_b", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_dp_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_dp_restringido=False,
    )
    DpMensaje.objects.create(autor=user_a, asunto="A-visible", mensaje="A")
    DpMensaje.objects.create(autor=user_b, asunto="B-hidden", mensaje="B")

    client.force_login(user_a)
    _set_module(client)
    response = client.get(reverse("sigmadp:inbox"))

    assert response.status_code == 200
    content = response.content.decode("utf-8", errors="ignore")
    assert "A-visible" in content
    assert "B-hidden" not in content


@pytest.mark.django_db
def test_sigmadp_inbox_allows_dp_tech_to_see_all(client):
    user_a = _create_user("dp_user_a2", ["usuarios_dtf"])
    user_b = _create_user("dp_user_b2", ["usuarios_dtf"])
    tech_dp = _create_user("dp_tech", ["tecnico_responsable_s_dp"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_dp_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_dp_restringido=False,
    )
    DpMensaje.objects.create(autor=user_a, asunto="A-visible-2", mensaje="A")
    DpMensaje.objects.create(autor=user_b, asunto="B-visible-2", mensaje="B")

    client.force_login(tech_dp)
    _set_module(client)
    response = client.get(reverse("sigmadp:inbox"))

    assert response.status_code == 200
    content = response.content.decode("utf-8", errors="ignore")
    assert "A-visible-2" in content
    assert "B-visible-2" in content


@pytest.mark.django_db
def test_sigmadp_necesidades_scopes_for_user(client):
    user_a = _create_user("dp_user_a3", ["usuarios_dtf"])
    user_b = _create_user("dp_user_b3", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_dp_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_dp_restringido=False,
    )
    DpNecesidad.objects.create(
        titulo="Necesidad A",
        descripcion="A",
        fecha=date(2024, 1, 1),
        creado_por=user_a,
    )
    DpNecesidad.objects.create(
        titulo="Necesidad B",
        descripcion="B",
        fecha=date(2024, 1, 2),
        creado_por=user_b,
    )

    client.force_login(user_a)
    _set_module(client)
    response = client.get(reverse("sigmadp:necesidades"))

    assert response.status_code == 200
    content = response.content.decode("utf-8", errors="ignore")
    assert "Necesidad A" in content
    assert "Necesidad B" not in content


@pytest.mark.django_db
def test_sigmadp_restriction_blocks_inbox_and_necesidades(client):
    user = _create_user("dp_restricted", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=True,
        acceso_s_dp_restringido=True,
    )

    client.force_login(user)
    _set_module(client)

    inbox_response = client.get(reverse("sigmadp:inbox"))
    assert inbox_response.status_code == 302
    assert inbox_response.url == reverse("dtf:dashboard")

    necesidades_response = client.get(reverse("sigmadp:necesidades"))
    assert necesidades_response.status_code == 302
    assert necesidades_response.url == reverse("dtf:dashboard")


@pytest.mark.django_db
def test_sigmadp_info_importante_required_for_users(client):
    user = _create_user("dp_incomplete", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=False,
        acceso_s_dp_restringido=False,
    )

    client.force_login(user)
    _set_module(client)
    response = client.get(reverse("sigmadp:inbox"))

    assert response.status_code == 302
    assert response.url == reverse("dtf:info-importante")


@pytest.mark.django_db
def test_sigmadp_blocks_other_lab_techs(client):
    tech_mec = _create_user("dp_other_lab", ["tecnico_responsable_s_mec"])

    client.force_login(tech_mec)
    _set_module(client)
    response = client.get(reverse("sigmadp:inbox"))

    assert response.status_code == 403
