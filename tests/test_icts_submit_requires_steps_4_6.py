import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal, ProposalReview


def _create_user(username: str, groups):
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
def test_submit_fails_if_step4_missing_even_with_techniques(client):
    applicant = _create_user("step4_applicant", ["icts_users"])
    _create_user("step4_reviewer", ["revisores"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Missing step 4",
        facility_sem=True,
        scope="Scope",
        project_name="",
        project_type="national",
        funding_source="Grant A",
        start_year=2024,
        end_year=2024,
        previous_experiments="Previous experiments",
        references="Reference list",
    )

    client.force_login(applicant)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"
    assert ProposalReview.objects.filter(proposal=proposal).count() == 0


@pytest.mark.django_db
def test_submit_fails_if_step6_missing_even_with_techniques(client):
    applicant = _create_user("step6_applicant", ["icts_users"])
    _create_user("step6_reviewer", ["revisores"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Missing step 6",
        facility_sem=True,
        scope="Scope",
        project_name="Project A",
        project_type="national",
        funding_source="Grant A",
        start_year=2024,
        end_year=2024,
        previous_experiments="",
        references="Reference list",
    )

    client.force_login(applicant)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"
    assert ProposalReview.objects.filter(proposal=proposal).count() == 0
