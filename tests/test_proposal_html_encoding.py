import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


def _create_icts_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_proposal_form_has_no_oacute_entity(client):
    user = _create_icts_user("proposal_utf8", "proposal_utf8@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "&oacute;" not in content
