import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

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


@pytest.mark.django_db
def test_review_start_submit_updates_decision(client):
    reviewer = _create_user("reviewer_submit", ["revisores"])
    applicant = _create_user("review_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Review proposal",
        status="submitted",
        facility_sem=True,
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="draft",
    )

    client.force_login(reviewer)
    response = client.post(
        reverse("icts:review_start", args=[proposal.pk]),
        data={
            "action": "submit_review",
            "feasibility_ok": "True",
            "decision": "approve",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("icts:reviewer_inbox")
    review = ProposalReview.objects.get(proposal=proposal, reviewer=reviewer)
    assert review.decision == "approve"
    assert review.status == "submitted"
    assert review.submitted_at is not None


@pytest.mark.django_db
def test_review_start_save_draft_allows_pending_decision(client):
    reviewer = _create_user("reviewer_draft", ["revisores"])
    applicant = _create_user("draft_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Draft proposal",
        status="submitted",
        facility_sem=True,
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="draft",
    )

    client.force_login(reviewer)
    response = client.post(
        reverse("icts:review_start", args=[proposal.pk]),
        data={"action": "save_draft"},
    )

    assert response.status_code == 302
    assert response.url == reverse("icts:reviewer_inbox")
    review = ProposalReview.objects.get(proposal=proposal, reviewer=reviewer)
    assert review.decision == "pending"
    assert review.status == "draft"


@pytest.mark.django_db
def test_review_start_redirects_responsable_without_creating_review(client):
    responsable = _create_user("responsable_only", ["responsables", "revisores"])
    applicant = _create_user("responsable_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Responsable proposal",
        status="submitted",
        facility_sem=True,
    )

    client.force_login(responsable)
    response = client.get(reverse("icts:review_start", args=[proposal.pk]))

    assert response.status_code == 302
    assert response.url == reverse("icts:responsable_dashboard")
    assert ProposalReview.objects.filter(proposal=proposal, reviewer=responsable).count() == 0
