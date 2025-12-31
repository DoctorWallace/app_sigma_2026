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
def test_submit_without_techniques_stays_draft(client):
    user = _create_user("no_tech_user", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="No techniques",
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))

    assert response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "draft"
    assert ProposalReview.objects.filter(proposal=proposal).count() == 0


@pytest.mark.django_db
def test_submit_olmat_only_allowed_without_reviews(client):
    user = _create_user("olmat_only_user", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="OLMAT only submit",
        facility_olmat=True,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))

    assert response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "submitted"
    assert ProposalReview.objects.filter(proposal=proposal).count() == 0


@pytest.mark.django_db
def test_submit_icts_creates_reviews(client):
    user = _create_user("icts_submit_user", ["icts_users"])
    reviewer = _create_user("submit_reviewer", ["revisores"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="ICTS submit",
        facility_sem=True,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))

    assert response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "submitted"
    assert ProposalReview.objects.filter(proposal=proposal).count() == 1


@pytest.mark.django_db
def test_submit_changes_requested_keeps_reviews(client):
    user = _create_user("changes_user", ["icts_users"])
    reviewer = _create_user("changes_reviewer", ["revisores"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Changes requested submit",
        status="changes_requested",
        facility_sem=True,
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        decision="reject",
        comments="Old review",
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))

    assert response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "submitted"
    reviews = ProposalReview.objects.filter(proposal=proposal, reviewer=reviewer)
    assert reviews.count() == 1
    assert reviews.first().decision == "reject"
