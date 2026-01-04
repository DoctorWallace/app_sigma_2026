import pytest
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


@pytest.mark.django_db
def test_responsable_dashboard_uses_completed_reviews_for_pending_list(client):
    responsable = _create_user("responsable_user", ["responsables"])
    applicant = _create_user("dashboard_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="ICTS proposal",
        status="submitted",
        facility_sem=True,
    )

    reviewers = []
    for idx in range(4):
        reviewer = _create_user(f"reviewer_{idx}", ["revisores"])
        reviewers.append(reviewer)
        ProposalReview.objects.create(
            proposal=proposal,
            reviewer=reviewer,
            decision="pending",
            status="draft",
        )

    client.force_login(responsable)
    response = client.get(reverse("icts:responsable_dashboard"))
    assert response.status_code == 200
    pendientes = list(response.context["pendientes"])
    assert proposal not in pendientes

    ProposalReview.objects.filter(proposal=proposal).update(
        decision="approve",
        status="submitted",
        submitted_at=timezone.now(),
    )
    response = client.get(reverse("icts:responsable_dashboard"))
    pendientes = list(response.context["pendientes"])
    assert proposal in pendientes
    pending = next(p for p in pendientes if p.pk == proposal.pk)
    assert pending.num_reviews == pending.completed_reviews


@pytest.mark.django_db
def test_responsable_dashboard_allows_decision_with_two_reviews(client):
    responsable = _create_user("responsable_two", ["responsables"])
    applicant = _create_user("applicant_two", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Two reviews proposal",
        status="submitted",
        facility_sem=True,
    )

    for idx in range(2):
        reviewer = _create_user(f"reviewer_two_{idx}", ["revisores"])
        ProposalReview.objects.create(
            proposal=proposal,
            reviewer=reviewer,
            decision="pending",
            status="draft",
        )

    client.force_login(responsable)
    response = client.get(reverse("icts:responsable_dashboard"))
    pendientes = list(response.context["pendientes"])
    assert proposal not in pendientes

    ProposalReview.objects.filter(proposal=proposal).update(
        decision="approve",
        status="submitted",
        submitted_at=timezone.now(),
    )
    response = client.get(reverse("icts:responsable_dashboard"))
    pendientes = list(response.context["pendientes"])
    assert proposal in pendientes
