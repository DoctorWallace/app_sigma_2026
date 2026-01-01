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
def test_load_previous_allows_rejected(client):
    user = _create_user("previous_rejected", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Rejected",
        status="rejected",
        facility_sem=True,
        facility_data={"sem": {"sem_sample_0_identification": "S1"}},
    )

    client.force_login(user)
    url = reverse("icts:load_previous_proposal")
    response = client.get(f"{url}?proposal_id={proposal.pk}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
