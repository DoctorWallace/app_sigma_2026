import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


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
def test_messages_visible_after_incomplete_submit(client):
    user = _create_user("icts_msg_user", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Missing steps proposal",
        facility_sem=True,
    )

    client.force_login(user)
    response = client.post(
        reverse("icts:proposal_submit", args=[proposal.pk]),
        follow=True,
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8", errors="ignore")
    assert "Faltan campos requeridos" in content


@pytest.mark.django_db
def test_messages_consumed_before_reviewer_login(client):
    user = _create_user("icts_msg_user2", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Missing steps proposal 2",
        facility_sem=True,
    )

    client.force_login(user)
    response = client.post(
        reverse("icts:proposal_submit", args=[proposal.pk]),
        follow=True,
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8", errors="ignore")
    assert "Faltan campos requeridos" in content

    client.logout()
    reviewer = _create_user("icts_reviewer", ["revisores"])
    client.force_login(reviewer)
    inbox_response = client.get(reverse("icts:reviewer_inbox"))

    assert inbox_response.status_code == 200
    inbox_content = inbox_response.content.decode("utf-8", errors="ignore")
    assert "Faltan campos requeridos" not in inbox_content
