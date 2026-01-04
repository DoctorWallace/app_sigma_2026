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


def _add_reviews(proposal, reviewers, completed_count):
    for idx, reviewer in enumerate(reviewers):
        decision = "approve" if idx < completed_count else "pending"
        status = "submitted" if decision != "pending" else "draft"
        submitted_at = timezone.now() if status == "submitted" else None
        ProposalReview.objects.create(
            proposal=proposal,
            reviewer=reviewer,
            decision=decision,
            status=status,
            submitted_at=submitted_at,
        )


@pytest.mark.django_db
def test_responsable_dashboard_counters(client):
    responsable = _create_user("resp_counters", ["responsables"])
    applicant = _create_user("counters_applicant", ["icts_users"])

    reviewers = [
        _create_user(f"reviewer_{idx}", ["revisores"])
        for idx in range(4)
    ]

    proposal_enviada = AccessProposal.objects.create(
        applicant=applicant,
        title="Enviada",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now(),
    )
    _add_reviews(proposal_enviada, reviewers[:2], completed_count=0)

    proposal_en_revision = AccessProposal.objects.create(
        applicant=applicant,
        title="En revision",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now(),
    )
    _add_reviews(proposal_en_revision, reviewers[:2], completed_count=1)

    proposal_pendiente = AccessProposal.objects.create(
        applicant=applicant,
        title="Pendiente por reviews",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now(),
    )
    _add_reviews(proposal_pendiente, reviewers, completed_count=4)

    proposal_pendiente_sla = AccessProposal.objects.create(
        applicant=applicant,
        title="Pendiente por SLA",
        status="submitted",
        facility_sem=True,
        submitted_at=timezone.now() - timedelta(days=11),
    )
    _add_reviews(proposal_pendiente_sla, reviewers[:2], completed_count=0)

    client.force_login(responsable)
    response = client.get(reverse("icts:responsable_dashboard"))
    stats = response.context["stats"]

    assert stats["submitted_no_reviews"] == 1
    assert stats["under_review"] == 1
    assert stats["ready_for_decision"] == 2
