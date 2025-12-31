import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal, OLMATRequest, ProposalReview


def _create_user(username, email, group_names):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    for name in group_names:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_olmat_only_does_not_create_reviews(client):
    user = _create_user("olmat_applicant", "olmat_applicant@example.com", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="OLMAT only",
        facility_olmat=True,
    )

    client.force_login(user)
    client.post(reverse("icts:proposal_submit", args=[proposal.pk]))

    assert ProposalReview.objects.filter(proposal=proposal).count() == 0


@pytest.mark.django_db
def test_reviewer_inbox_excludes_olmat_only(client):
    applicant = _create_user("applicant", "applicant@example.com", ["icts_users"])
    reviewer = _create_user("reviewer", "reviewer@example.com", ["revisores"])

    olmat_only = AccessProposal.objects.create(
        applicant=applicant,
        title="OLMAT only",
        status="submitted",
        facility_olmat=True,
    )
    icts_proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="ICTS proposal",
        status="submitted",
        facility_sem=True,
    )

    client.force_login(reviewer)
    response = client.get(reverse("icts:reviewer_inbox"))

    pending = list(response.context["pending"])
    assert olmat_only not in pending
    assert icts_proposal in pending


@pytest.mark.django_db
def test_review_start_blocked_for_olmat_only(client):
    reviewer = _create_user("reviewer2", "reviewer2@example.com", ["revisores"])
    proposal = AccessProposal.objects.create(
        applicant=reviewer,
        title="OLMAT only",
        status="submitted",
        facility_olmat=True,
    )

    client.force_login(reviewer)
    response = client.get(reverse("icts:review_start", args=[proposal.pk]))
    assert response.status_code in {302, 403}
    assert ProposalReview.objects.filter(proposal=proposal, reviewer=reviewer).count() == 0


@pytest.mark.django_db
def test_olmat_tech_can_view_request_detail(client):
    applicant = _create_user("olmat_owner", "olmat_owner@example.com", ["icts_users"])
    tech = _create_user("olmat_tech", "olmat_tech@example.com", ["olmat"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="OLMAT request",
        facility_olmat=True,
    )
    olmat_request = OLMATRequest.objects.create(
        proposal=proposal,
        service_type="technical",
    )

    client.force_login(tech)
    response = client.get(reverse("icts:olmat_request_detail", args=[olmat_request.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_olmat_request_created_from_facility_data(client):
    user = _create_user("olmat_data", "olmat_data@example.com", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="OLMAT data",
        facility_olmat=True,
        facility_data={
            "olmat": {
                "olmat_service_type": "research",
                "olmat_activity_description": "Activity details",
                "olmat_irradiation_requirements": "Irradiation",
                "olmat_diagnostics": ["thermocouples", "fast_camera"],
                "olmat_sample_prep": ["other"],
                "olmat_sample_prep_notes": "Special prep",
                "olmat_beam_usage": ["laser"],
                "olmat_preferred_dates": "2026-01-10 to 2026-01-12",
                "olmat_flexibility": "high",
                "olmat_additional_requirements": "Extra notes",
            }
        },
    )

    client.force_login(user)
    client.post(reverse("icts:proposal_submit", args=[proposal.pk]))

    olmat_request = OLMATRequest.objects.get(proposal=proposal)
    assert olmat_request.service_type == "research"
    assert olmat_request.diagnostics_needed == ["thermocouples", "fast_camera"]
    assert olmat_request.sample_preparation == ["other"]
    assert olmat_request.beam_usage == ["laser"]
    assert "Prep (otros): Special prep" in (olmat_request.additional_requirements or "")
