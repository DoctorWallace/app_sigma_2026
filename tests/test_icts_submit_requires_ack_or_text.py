import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


ACK_DATA = {
    "ack_empty_scope": "on",
    "ack_empty_previous_experiments": "on",
    "ack_empty_references": "on",
}


def _create_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_submit_requires_ack_or_text(client):
    user = _create_user("ack_user", "ack_user@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Needs ack",
        facility_sem=True,
        scope="",
        project_name="Project A",
        project_type="national",
        funding_source="Grant A",
        start_year=2024,
        end_year=2024,
        previous_experiments="Previous experiments",
        references="Reference list",
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"

    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "submitted"
