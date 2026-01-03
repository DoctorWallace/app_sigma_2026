import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client as DjangoClient
from django.urls import reverse

from dtf.models import DTFUserProfile


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


def _create_pending_user(username="pending_user", email="pending@ciemat.es"):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=email,
        is_active=False,
        first_name="Pend",
        last_name="User",
    )
    DTFUserProfile.objects.create(
        user=user,
        is_ciemat=True,
        matricula=username,
        departamento="LNF",
        division_unidad="X",
    )
    return user


@pytest.mark.django_db
def test_register_dtf_creates_inactive_user(client):
    response = client.post(
        reverse("accounts:register_dtf"),
        {
            "username": "12345",
            "email": "alguien@ciemat.es",
            "first_name": "A",
            "last_name": "B",
            "password1": "SafePass12345!",
            "password2": "SafePass12345!",
            "departamento": "LNF",
            "division_unidad": "X",
            "telefono_interno": "1234",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:login_dtf")

    User = get_user_model()
    user = User.objects.get(username="12345")
    assert user.is_active is False
    assert not user.groups.filter(name="usuarios_dtf").exists()
    assert user.dtf_profile.matricula == "12345"
    assert user.dtf_profile.is_ciemat is True


@pytest.mark.django_db
def test_pending_users_forbidden_for_non_tech(client):
    user = _create_user("dtf_user", ["usuarios_dtf"])

    client.force_login(user)
    _set_module(client)
    response = client.get(reverse("dtf:pending_users"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_pending_users_visible_for_tech(client):
    tech = _create_user("dtf_tech", ["tecnico_responsable_s_lab"])
    pending = _create_pending_user("pending_tech", "pending_tech@ciemat.es")

    client.force_login(tech)
    _set_module(client)
    response = client.get(reverse("dtf:pending_users"))

    assert response.status_code == 200
    assert pending.username in response.content.decode()


@pytest.mark.django_db
def test_approve_reject_require_post_and_csrf(client):
    tech = _create_user("dtf_tech_post", ["tecnico_responsable_s_lab"])
    pending = _create_pending_user("pending_post", "pending_post@ciemat.es")

    client.force_login(tech)
    _set_module(client)
    response = client.get(reverse("dtf:approve_user", args=[pending.pk]))
    assert response.status_code == 405

    response = client.get(reverse("dtf:reject_user", args=[pending.pk]))
    assert response.status_code == 405

    csrf_client = DjangoClient(enforce_csrf_checks=True)
    csrf_client.force_login(tech)
    _set_module(csrf_client)
    response = csrf_client.post(reverse("dtf:approve_user", args=[pending.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_approve_forbidden_for_non_tech(client):
    user = _create_user("dtf_user_noadmin", ["usuarios_dtf"])
    pending = _create_pending_user("pending_noadmin", "pending_noadmin@ciemat.es")

    client.force_login(user)
    _set_module(client)
    response = client.post(reverse("dtf:approve_user", args=[pending.pk]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_approve_activates_user_and_adds_group(client):
    tech = _create_user("dtf_tech_ok", ["tecnico_responsable_s_lab"])
    pending = _create_pending_user("pending_ok", "pending_ok@ciemat.es")

    client.force_login(tech)
    _set_module(client)
    response = client.post(reverse("dtf:approve_user", args=[pending.pk]))

    assert response.status_code == 302
    pending.refresh_from_db()
    assert pending.is_active is True
    assert pending.groups.filter(name="usuarios_dtf").exists()


@pytest.mark.django_db
def test_reject_deletes_user(client):
    tech = _create_user("dtf_tech_reject", ["tecnico_responsable_s_lab"])
    pending = _create_pending_user("pending_reject", "pending_reject@ciemat.es")

    client.force_login(tech)
    _set_module(client)
    response = client.post(reverse("dtf:reject_user", args=[pending.pk]))

    assert response.status_code == 302
    User = get_user_model()
    with pytest.raises(User.DoesNotExist):
        User.objects.get(pk=pending.pk)
