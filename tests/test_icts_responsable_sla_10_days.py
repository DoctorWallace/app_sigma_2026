import pytest
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal, ProposalReview


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


def _create_pending_reviews(proposal, count):
    for idx in range(count):
        reviewer = _create_user(f"sla_reviewer_{proposal.pk}_{idx}", ["revisores"])
        ProposalReview.objects.create(
            proposal=proposal,
            reviewer=reviewer,
            decision="pending",
        )


@pytest.mark.django_db
def test_responsable_cannot_decide_before_10_days_without_enough_reviews(client):
    responsable = _create_user("sla_responsable_early", ["responsables"])
    applicant = _create_user("sla_applicant_early", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Early SLA",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now() - timedelta(days=5),
    )
    _create_pending_reviews(proposal, 4)

    client.force_login(responsable)
    response = client.post(
        reverse("icts:proposal_decide", args=[proposal.pk]),
        {"final_decision": "accepted"},
    )
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "submitted"


@pytest.mark.django_db
def test_responsable_can_decide_after_10_days_without_enough_reviews(client):
    responsable = _create_user("sla_responsable_late", ["responsables"])
    applicant = _create_user("sla_applicant_late", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Late SLA",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now() - timedelta(days=11),
    )
    _create_pending_reviews(proposal, 4)

    client.force_login(responsable)
    response = client.post(
        reverse("icts:proposal_decide", args=[proposal.pk]),
        {"final_decision": "accepted"},
    )
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "accepted"
