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
def test_reviewer_dashboard_new_loads_for_reviewer(client):
    reviewer = _create_user("reviewer_dash", ["revisores"])
    client.force_login(reviewer)

    response = client.get(reverse("icts:reviewer_dashboard_new"))
    assert response.status_code == 200
