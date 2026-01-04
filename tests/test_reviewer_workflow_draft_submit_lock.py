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

    inbox = client.get(reverse("icts:reviewer_inbox"))
    pending = list(inbox.context["pending"])
    assert proposal in pending


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
            "action": "submit_review",
            "feasibility_ok": "True",
            "decision": "approve",
        },
    )

    assert response.status_code == 302
    review_one.refresh_from_db()
    assert review_one.status == "submitted"
    assert review_one.submitted_at is not None

    inbox = client.get(reverse("icts:reviewer_inbox"))
    pending = list(inbox.context["pending"])
    completed = list(inbox.context["completed"])
    assert proposal not in pending
    assert any(item.proposal_id == proposal.pk for item in completed)

    client.force_login(reviewer_two)
    inbox_other = client.get(reverse("icts:reviewer_inbox"))
    pending_other = list(inbox_other.context["pending"])
    assert proposal in pending_other


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
def test_reviewer_request_changes_stays_draft(client):
    reviewer = _create_user("reviewer_changes", ["revisores"])
    applicant = _create_user("changes_applicant", ["icts_users"])
    proposal = _create_proposal(applicant, "Changes proposal")
    review = ProposalReview.objects.create(
        proposal=proposal,
        reviewer=reviewer,
        status="draft",
    )

    client.force_login(reviewer)
    response = client.post(
        reverse("icts:review_start", args=[proposal.pk]),
        data={
            "action": "request_changes",
            "change_request_text": "Faltan detalles sobre el plan de trabajo.",
        },
    )

    assert response.status_code == 302
    review.refresh_from_db()
    assert review.change_request_text == "Faltan detalles sobre el plan de trabajo."
    assert review.change_request_at is not None
    assert review.status == "draft"
