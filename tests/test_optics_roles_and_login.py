import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from core import roles as core_roles


@pytest.mark.django_db
def test_optics_technician_is_allowed_in_icts():
    """Optics technicians must be considered ICTS users (not forced to DTF)."""
    User = get_user_model()
    user = User.objects.create_user(
        username="optics_tech",
        password="safe-pass",
        email="optics_tech@example.com",
    )
    group, _ = Group.objects.get_or_create(name="tecnico_responsable_s_optics")
    user.groups.add(group)

    # Expected behavior after the migration:
    # - Optics technicians must be able to access SIGMA ICTS.
    assert core_roles.user_can_access_icts(user) is True
    assert core_roles.is_icts_user(user) is True


@pytest.mark.django_db
def test_login_icts_allows_optics_technician(client):
    """Regression test: optics technicians should not be bounced to /accounts/login/dtf/."""
    User = get_user_model()
    user = User.objects.create_user(
        username="optics_login",
        password="safe-pass",
        email="optics_login@example.com",
    )
    group, _ = Group.objects.get_or_create(name="tecnico_responsable_s_optics")
    user.groups.add(group)

    response = client.post(
        reverse("accounts:login_icts"),
        data={"username": "optics_login", "password": "safe-pass"},
        follow=False,
    )

    assert response.status_code == 302
    # The current bug is a redirect to the DTF login. The correct behavior is to stay in ICTS.
    assert "login/dtf" not in (response.url or "")
    assert client.session.get("module") == "icts"
    assert "_auth_user_id" in client.session
