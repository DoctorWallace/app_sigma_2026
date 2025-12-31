import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass")
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_module(client, module):
    session = client.session
    session["module"] = module
    session.save()


def _assert_forbidden_or_redirect(response):
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_login_dtf_rejects_non_dtf_user(client):
    user = _create_user("icts_only", ["icts_users"])

    response = client.post(
        reverse("accounts:login_dtf"),
        {"username": user.username, "password": "safe-pass"},
    )

    assert response.status_code == 302
    assert reverse("accounts:login_icts") in response.url
    assert client.session.get("module") != "dtf"

    follow_up = client.get(reverse("dtf:dashboard"))
    assert follow_up.status_code == 302
    assert reverse("accounts:login_dtf") in follow_up.url


@pytest.mark.django_db
def test_dtf_routes_require_dtf_module(client):
    user = _create_user("dtf_user", ["usuarios_dtf"])
    client.force_login(user)
    _set_module(client, "icts")

    response = client.get(reverse("dtf:dashboard"))
    assert response.status_code == 302
    assert reverse("accounts:login_dtf") in response.url


@pytest.mark.parametrize(
    ("group_name", "url_name"),
    [
        ("tecnico_responsable_s_mec", "sigmalab:panel-tecnico"),
        ("tecnico_responsable_s_lab", "mec:panel_tecnico"),
        ("tecnico_responsable_s_dp", "sigmaoptics:panel_tecnico"),
        ("tecnico_responsable_s_optics", "sigmadp:panel_tecnico"),
    ],
)
@pytest.mark.django_db
def test_cross_lab_tech_access_forbidden(client, group_name, url_name):
    user = _create_user(f"user_{group_name}", [group_name])
    client.force_login(user)
    _set_module(client, "dtf")

    response = client.get(reverse(url_name))
    _assert_forbidden_or_redirect(response)
