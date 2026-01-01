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
def test_sigmasims_docs_requires_login(client):
    response = client.get(reverse("icts:sigmasims:docs_list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_sigmasims_docs_allows_sims_tech(client):
    user = _create_user("sims_docs", ["tecnicos_sims"])
    client.force_login(user)
    response = client.get(reverse("icts:sigmasims:docs_list"))
    assert response.status_code == 200
