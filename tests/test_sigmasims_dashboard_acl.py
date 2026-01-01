import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


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
def test_sigmasims_dashboard_anonymous_redirects(client):
    response = client.get(reverse("icts:sigmasims:dashboard"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_sigmasims_dashboard_requires_group(client):
    user = _create_user("sims_plain", ["icts_users"])
    client.force_login(user)
    response = client.get(reverse("icts:sigmasims:dashboard"))
    assert response.status_code in {302, 403}


@pytest.mark.django_db
def test_sigmasims_dashboard_allows_sims_tech(client):
    user = _create_user("sims_tech", ["tecnicos_sims"])
    client.force_login(user)
    response = client.get(reverse("icts:sigmasims:dashboard"))
    assert response.status_code == 200
