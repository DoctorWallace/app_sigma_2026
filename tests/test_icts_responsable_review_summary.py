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
def test_proposal_detail_responsable_review_summary(client):
    applicant = _create_user("summary_applicant", ["icts_users"])
    reviewer_one = _create_user("reviewer_one", ["revisores"])
    reviewer_two = _create_user("reviewer_two", ["revisores"])
    reviewer_pending = _create_user("reviewer_pending", ["revisores"])
    responsable = _create_user("responsable_user", ["responsables"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Proposal summary",
        status="submitted",
        facility_sem=True,
    )

    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_one,
        decision="approve",
        comments="Looks good",
        score_scientific_quality=4,
        score_need_infrastructure=3,
        score_industrial_potential=5,
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_two,
        decision="reject",
        comments="Needs work",
        score_scientific_quality=2,
        score_need_infrastructure=3,
        score_industrial_potential=1,
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_pending,
        decision="pending",
    )

    client.force_login(responsable)
    response = client.get(reverse("icts:proposal_detail", args=[proposal.pk]))

    assert response.status_code == 200
    summary = response.context["review_summary"]
    assert summary["completed_count"] == 2
    assert summary["avg_scientific"] == 3.0
    assert summary["avg_infrastructure"] == 3.0
    assert summary["avg_industrial"] == 3.0
    comments = response.context["review_summary_comments"]
    assert len(comments) == 2
    content = response.content.decode()
    assert "reviewer_one" in content
    assert "reviewer_two" in content
