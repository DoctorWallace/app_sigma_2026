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


def _create_proposal(applicant, title):
    return AccessProposal.objects.create(
        applicant=applicant,
        title=title,
        status="submitted",
        facility_sem=True,
    )


@pytest.mark.django_db
def test_reviewer_save_draft_keeps_pending_in_inbox(client):
    reviewer = _create_user("reviewer_draft_keep", ["revisores"])
    applicant = _create_user("draft_keep_applicant", ["icts_users"])
    proposal = _create_proposal(applicant, "Draft keep proposal")
    review = ProposalReview.objects.create(
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
    review.refresh_from_db()
    assert review.status == "draft"
    assert review.submitted_at is None
    assert review.draft_saved_at is not None

    inbox = client.get(reverse("icts:reviewer_inbox"))
    pending = list(inbox.context["pending_reviews"])
    assert any(item.proposal_id == proposal.pk for item in pending)


@pytest.mark.django_db
def test_reviewer_submit_moves_to_completed_and_keeps_other_pending(client):
    reviewer_one = _create_user("reviewer_submit_one", ["revisores"])
    reviewer_two = _create_user("reviewer_submit_two", ["revisores"])
    applicant = _create_user("submit_applicant", ["icts_users"])
    proposal = _create_proposal(applicant, "Submit proposal")
    review_one = ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_one,
        status="draft",
    )
    ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer_two,
        status="draft",
    )

    client.force_login(reviewer_one)
    response = client.post(
        reverse("icts:review_start", args=[proposal.pk]),
        data={
            "action": "save_draft",
            "feasibility_ok": "True",
            "score_scientific_quality": "4",
            "score_need_infrastructure": "4",
            "score_industrial_potential": "4",
            "decision": "approve",
        },
    )
    assert response.status_code == 302
    review_one.refresh_from_db()
    assert review_one.draft_saved_at is not None

    response = client.post(
        reverse("icts:review_send", args=[proposal.pk]),
    )

    assert response.status_code == 302
    review_one.refresh_from_db()
    assert review_one.status == "submitted"
    assert review_one.submitted_at is not None

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
def test_reviewer_submit_locks_review(client):
    reviewer = _create_user("reviewer_lock", ["revisores"])
    applicant = _create_user("lock_applicant", ["icts_users"])
    proposal = _create_proposal(applicant, "Locked proposal")
    review = ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="submitted",
        decision="approve",
    )

    client.force_login(reviewer)
    response = client.post(
        reverse("icts:review_start", args=[proposal.pk]),
        data={
            "action": "save_draft",
            "comments": "Should not update",
        },
    )

    assert response.status_code == 403
    review.refresh_from_db()
    assert review.status == "submitted"
    assert review.decision == "approve"


@pytest.mark.django_db
def test_reviewer_request_modify_creates_pending_request(client):
    reviewer = _create_user("reviewer_changes", ["revisores"])
    applicant = _create_user("changes_applicant", ["icts_users"])
    proposal = _create_proposal(applicant, "Changes proposal")
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
        data={"message": "Necesito ajustar mi evaluación."},
    )

    assert response.status_code == 302
    assert ProposalReviewModificationRequest.objects.filter(
        review=review,
        status="pending",
    ).exists()
