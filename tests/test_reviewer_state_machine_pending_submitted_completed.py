import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import (
    AccessProposal,
    ProposalReview,
    ProposalReviewModificationRequest,
)


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


def _create_proposal(applicant, title, status="submitted"):
    return AccessProposal.objects.create(
        applicant=applicant,
        title=title,
        status=status,
        facility_sem=True,
    )


@pytest.mark.django_db
def test_pending_inbox_no_send_without_draft_saved(client):
    reviewer = _create_user("reviewer_pending", ["revisores"])
    reviewer_two = _create_user("reviewer_pending_two", ["revisores"])
    applicant = _create_user("applicant_pending", ["icts_users"])
    proposal = _create_proposal(applicant, "Pending proposal")
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="draft",
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_two,
        status="draft",
    )

    client.force_login(reviewer)
    response = client.get(reverse("icts:reviewer_inbox"))
    pending = list(response.context["pending_reviews"])
    assert any(item.proposal_id == proposal.pk for item in pending)

    content = response.content.decode("utf-8", errors="ignore")
    assert reverse("icts:review_send", args=[proposal.pk]) not in content


@pytest.mark.django_db
def test_send_moves_to_submitted_and_is_scoped_per_reviewer(client):
    reviewer = _create_user("reviewer_send", ["revisores"])
    reviewer_two = _create_user("reviewer_send_two", ["revisores"])
    applicant = _create_user("applicant_send", ["icts_users"])
    proposal = _create_proposal(applicant, "Send proposal")
    review = ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="draft",
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_two,
        status="draft",
    )

    client.force_login(reviewer)
    response = client.post(
        reverse("icts:review_start", args=[proposal.pk]),
        data={
            "action": "save_draft",
            "feasibility_ok": "True",
            "score_scientific_quality": "4",
            "score_need_infrastructure": "4",
            "score_industrial_potential": "4",
            "decision": "approve",
            "comments": "Ready to send.",
        },
    )
    assert response.status_code == 302

    review.refresh_from_db()
    assert review.status == "draft"
    assert review.draft_saved_at is not None

    response = client.get(reverse("icts:reviewer_inbox"))
    content = response.content.decode("utf-8", errors="ignore")
    assert reverse("icts:review_send", args=[proposal.pk]) in content

    response = client.post(reverse("icts:review_send", args=[proposal.pk]))
    assert response.status_code == 302

    review.refresh_from_db()
    assert review.status == "submitted"
    assert review.submitted_at is not None

    inbox = client.get(reverse("icts:reviewer_inbox"))
    pending = list(inbox.context["pending_reviews"])
    submitted = list(inbox.context["submitted_reviews"])
    assert all(item.proposal_id != proposal.pk for item in pending)
    assert any(item.proposal_id == proposal.pk for item in submitted)

    client.force_login(reviewer_two)
    inbox_other = client.get(reverse("icts:reviewer_inbox"))
    pending_other = list(inbox_other.context["pending_reviews"])
    assert any(item.proposal_id == proposal.pk for item in pending_other)


@pytest.mark.django_db
def test_completed_bucket_after_final_decision(client):
    reviewer = _create_user("reviewer_completed", ["revisores"])
    applicant = _create_user("applicant_completed", ["icts_users"])
    proposal = _create_proposal(applicant, "Completed proposal")
    review = ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="submitted",
        decision="approve",
        submitted_at=timezone.now(),
    )

    client.force_login(reviewer)
    inbox = client.get(reverse("icts:reviewer_inbox"))
    submitted = list(inbox.context["submitted_reviews"])
    assert any(item.proposal_id == proposal.pk for item in submitted)

    proposal.status = "accepted"
    proposal.save(update_fields=["status"])

    inbox = client.get(reverse("icts:reviewer_inbox"))
    submitted = list(inbox.context["submitted_reviews"])
    completed = list(inbox.context["completed_reviews"])
    assert all(item.proposal_id != proposal.pk for item in submitted)
    assert any(item.proposal_id == proposal.pk for item in completed)


@pytest.mark.django_db
def test_modify_request_approval_reopens_review(client):
    reviewer = _create_user("reviewer_modify", ["revisores"])
    responsable = _create_user("responsable_modify", ["responsables"])
    applicant = _create_user("applicant_modify", ["icts_users"])
    proposal = _create_proposal(applicant, "Modify proposal")
    review = ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="submitted",
        decision="approve",
        submitted_at=timezone.now(),
        draft_saved_at=timezone.now(),
    )

    client.force_login(reviewer)
    response = client.post(
        reverse("icts:review_request_modify", args=[proposal.pk]),
        data={"message": "Necesito corregir datos."},
    )
    assert response.status_code == 302

    mod_request = ProposalReviewModificationRequest.objects.get(review=review)
    assert mod_request.status == "pending"

    client.force_login(responsable)
    inbox = client.get(reverse("icts:responsable_review_messages"))
    assert inbox.status_code == 200

    response = client.post(
        reverse("icts:approve_review_mod_request", args=[mod_request.pk]),
    )
    assert response.status_code == 302

    review.refresh_from_db()
    assert review.status == "draft"
    assert review.submitted_at is None
    assert review.reopened_at is not None
    assert review.draft_saved_at is None

    client.force_login(reviewer)
    reviewer_inbox = client.get(reverse("icts:reviewer_inbox"))
    pending = list(reviewer_inbox.context["pending_reviews"])
    assert any(item.proposal_id == proposal.pk for item in pending)
    content = reviewer_inbox.content.decode("utf-8", errors="ignore")
    assert reverse("icts:review_send", args=[proposal.pk]) not in content
