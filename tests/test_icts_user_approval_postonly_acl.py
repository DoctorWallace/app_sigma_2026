import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client as DjangoClient
from django.urls import reverse

from icts.models import ICTSUserProfile


def _create_user(username, email, group_names, is_active=True):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=email,
        is_active=is_active,
    )
    for name in group_names:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _create_pending_user(username="pending_user"):
    user = _create_user(username, f"{username}@example.com", ["icts_users"], is_active=False)
    ICTSUserProfile.objects.create(user=user, center="X")
    return user


@pytest.mark.django_db
def test_approve_user_get_returns_405_for_responsable(client):
    responsable = _create_user("resp_get", "resp_get@example.com", ["responsables"])
    pending_user = _create_pending_user("pending_get_approve")
    client.force_login(responsable)

    response = client.get(reverse("icts:approve_user", args=[pending_user.id]))
    assert response.status_code == 405


@pytest.mark.django_db
def test_approve_user_post_redirects_anonymous(client):
    pending_user = _create_pending_user("pending_anon_approve")
    response = client.post(reverse("icts:approve_user", args=[pending_user.id]))

    assert response.status_code == 302
    assert "/accounts/login/icts/" in response.url


@pytest.mark.django_db
def test_approve_user_post_forbids_manager(client):
    manager = _create_user("manager_approve", "manager_approve@example.com", ["managers"])
    pending_user = _create_pending_user("pending_manager_approve")
    client.force_login(manager)

    response = client.post(reverse("icts:approve_user", args=[pending_user.id]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_approve_user_post_activates_pending_user(client):
    responsable = _create_user("resp_approve", "resp_approve@example.com", ["responsables"])
    pending_user = _create_pending_user("pending_approve")
    client.force_login(responsable)

    response = client.post(reverse("icts:approve_user", args=[pending_user.id]))
    assert response.status_code == 302
    assert response.url == reverse("icts:pending_users")

    pending_user.refresh_from_db()
    assert pending_user.is_active is True
    assert pending_user.icts_profile.validated is True


@pytest.mark.django_db
def test_reject_user_get_returns_405_for_responsable(client):
    responsable = _create_user("resp_reject_get", "resp_reject_get@example.com", ["responsables"])
    pending_user = _create_pending_user("pending_get_reject")
    client.force_login(responsable)

    response = client.get(reverse("icts:reject_user", args=[pending_user.id]))
    assert response.status_code == 405


@pytest.mark.django_db
def test_reject_user_post_forbids_manager(client):
    manager = _create_user("manager_reject", "manager_reject@example.com", ["managers"])
    pending_user = _create_pending_user("pending_manager_reject")
    client.force_login(manager)

    response = client.post(reverse("icts:reject_user", args=[pending_user.id]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_reject_user_post_deletes_user(client):
    responsable = _create_user("resp_reject", "resp_reject@example.com", ["responsables"])
    pending_user = _create_pending_user("pending_reject")
    client.force_login(responsable)

    response = client.post(reverse("icts:reject_user", args=[pending_user.id]))
    assert response.status_code == 302
    assert response.url == reverse("icts:pending_users")

    User = get_user_model()
    with pytest.raises(User.DoesNotExist):
        User.objects.get(id=pending_user.id)


@pytest.mark.django_db
def test_approve_user_requires_csrf_token():
    responsable = _create_user("resp_csrf", "resp_csrf@example.com", ["responsables"])
    pending_user = _create_pending_user("pending_csrf")

    csrf_client = DjangoClient(enforce_csrf_checks=True)
    csrf_client.force_login(responsable)
    response = csrf_client.post(reverse("icts:approve_user", args=[pending_user.id]))

    assert response.status_code == 403
