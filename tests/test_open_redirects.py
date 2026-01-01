import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


def _create_user(username: str, password: str, groups):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password=password,
        email=f"{username}@example.com",
    )
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_login_icts_rejects_external_next(client):
    user = _create_user("icts_user", "safe-pass", ["icts_users"])
    url = reverse("accounts:login_icts") + "?next=https://evil.example"
    response = client.post(url, {"username": user.username, "password": "safe-pass"})

    assert response.status_code == 302
    assert not response["Location"].startswith("https://evil.example")


@pytest.mark.django_db
def test_login_dtf_rejects_external_next(client):
    user = _create_user("dtf_user", "safe-pass", ["usuarios_dtf"])
    url = reverse("accounts:login_dtf") + "?next=https://evil.example"
    response = client.post(url, {"username": user.username, "password": "safe-pass"})

    assert response.status_code == 302
    assert not response["Location"].startswith("https://evil.example")


@pytest.mark.django_db
def test_logout_rejects_external_next(client):
    url = reverse("accounts:logout") + "?next=https://evil.example"
    response = client.post(url)

    assert response.status_code == 302
    assert not response["Location"].startswith("https://evil.example")
