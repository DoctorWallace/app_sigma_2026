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
def test_responsable_dashboard_stats_use_approved_key(client):
    responsable = _create_user("resp_stats", ["responsables"])
    applicant = _create_user("stats_applicant", ["icts_users"])
    AccessProposal.objects.create(
        applicant=applicant,
        title="Accepted proposal",
        status="accepted",
        facility_sem=True,
    )

    client.force_login(responsable)
    response = client.get(reverse("icts:responsable_dashboard"))

    stats = response.context["stats"]
    assert stats["approved"] == 1


@pytest.mark.django_db
def test_responsable_dashboard_num_reviews_and_reviewers_done(client):
    responsable = _create_user("resp_reviews", ["responsables"])
    applicant = _create_user("reviews_applicant", ["icts_users"])
    reviewer_one = _create_user("reviewer_one", ["revisores"])
    reviewer_two = _create_user("reviewer_two", ["revisores"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Submitted proposal",
        status="submitted",
        facility_sem=True,
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_one,
        decision="approve",
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_two,
        decision="approve",
    )

    client.force_login(responsable)
    response = client.get(reverse("icts:responsable_dashboard"))
    pendientes = list(response.context["pendientes"])
    pending = next(item for item in pendientes if item.pk == proposal.pk)

    assert pending.num_reviews == 2
    assert reviewer_one.username in pending.reviewers_done
    assert reviewer_two.username in pending.reviewers_done
