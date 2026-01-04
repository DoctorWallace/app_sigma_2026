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


@pytest.mark.django_db
def test_responsable_dashboard_sla_buckets(client):
    responsable = _create_user("resp_sla", ["responsables"])
    applicant = _create_user("sla_applicant", ["icts_users"])

    proposal_no_reviews = AccessProposal.objects.create(
        applicant=applicant,
        title="No reviews",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now(),
    )

    proposal_one_review = AccessProposal.objects.create(
        applicant=applicant,
        title="One review",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now(),
    )
    reviewer_one = _create_user("sla_reviewer_one", ["revisores"])
    reviewer_two = _create_user("sla_reviewer_two", ["revisores"])
    ProposalReview.objects.create(
        proposal=proposal_one_review,
        reviewer=reviewer_one,
        decision="approve",
        status="submitted",
    )
    ProposalReview.objects.create(
        proposal=proposal_one_review,
        reviewer=reviewer_two,
        decision="pending",
        status="draft",
    )

    proposal_overdue = AccessProposal.objects.create(
        applicant=applicant,
        title="Overdue",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now() - timedelta(days=11),
    )

    client.force_login(responsable)
    response = client.get(reverse("icts:responsable_dashboard"))

    stats = response.context["stats"]
    assert stats["submitted_no_reviews"] == 1
    assert stats["under_review"] == 1
    assert stats["ready_for_decision"] == 1

    pendientes = list(response.context["pendientes"])
    overdue_ctx = next(item for item in pendientes if item.pk == proposal_overdue.pk)
    assert overdue_ctx.urgency_level >= 10
