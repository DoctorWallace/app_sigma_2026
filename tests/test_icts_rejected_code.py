import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal, ProposalReview


ACK_DATA = {
    "ack_empty_scope": "on",
    "ack_empty_previous_experiments": "on",
    "ack_empty_references": "on",
}
REQUIRED_SUBMIT_FIELDS = {
    "project_name": "Project A",
    "project_type": "national",
    "funding_source": "Grant A",
    "start_year": 2024,
    "end_year": 2024,
    "previous_experiments": "Previous experiments",
    "references": "Reference list",
}


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
def test_rejected_decision_overwrites_access_code(client):
    applicant = _create_user("rejected_applicant", ["icts_users"])
    for idx in range(4):
        _create_user(f"reviewer_rejected_{idx}", ["revisores"])
    responsable = _create_user("responsable_rejected", ["responsables"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Rejected proposal",
        facility_sem=True,
        **REQUIRED_SUBMIT_FIELDS,
    )

    client.force_login(applicant)
    response = client.post(
        reverse("icts:proposal_submit", args=[proposal.pk]),
        ACK_DATA,
    )
    assert response.status_code == 302
    assert ProposalReview.objects.filter(proposal=proposal).count() == 4

    ProposalReview.objects.filter(proposal=proposal).update(decision="approve")

    client.force_login(responsable)
    response = client.post(
        reverse("icts:proposal_decide", args=[proposal.pk]),
        {"final_decision": "rejected"},
    )
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "rejected"
    assert proposal.access_code.startswith("rejected_")
    month = proposal.submitted_at.month
    year = proposal.submitted_at.year
    seq = proposal.user_sequence_number or 0
    assert f"_{month:02d}_{year}_{seq}" in proposal.access_code
