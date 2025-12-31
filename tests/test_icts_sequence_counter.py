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


def _create_icts_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_next_seq_preview_uses_historical_submissions(client):
    user = _create_icts_user("history", "history@example.com")
    for idx in range(4):
        AccessProposal.objects.create(
            applicant=user,
            title=f"Old {idx}",
            status="submitted",
        )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_create"))

    assert response.status_code == 200
    assert response.context["next_seq_preview"] == 5


@pytest.mark.django_db
def test_submit_uses_historical_count_for_sequence(client):
    user = _create_icts_user("history2", "history2@example.com")
    for idx in range(4):
        AccessProposal.objects.create(
            applicant=user,
            title=f"Old {idx}",
            status="submitted",
        )

    proposal = AccessProposal.objects.create(
        applicant=user,
        title="New Draft",
        facility_sem=True,
    )

    client.force_login(user)
    client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)

    proposal.refresh_from_db()
    assert proposal.user_sequence_number == 5
