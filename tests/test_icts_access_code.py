import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.forms import ParticipantFormSet
from icts.models import AccessProposal


ACK_DATA = {
    "ack_empty_scope": "on",
    "ack_empty_previous_experiments": "on",
    "ack_empty_references": "on",
}


def _create_icts_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_access_code_sequence_per_user(client):
    other = _create_icts_user("other", "other@example.com")
    AccessProposal.objects.create(applicant=other, title="Noise")

    user = _create_icts_user("alice", "alice@example.com")
    proposal1 = AccessProposal.objects.create(applicant=user, title="P1", facility_sem=True)
    proposal2 = AccessProposal.objects.create(applicant=user, title="P2", facility_sem=True)

    client.force_login(user)
    client.post(reverse("icts:proposal_submit", args=[proposal1.pk]), ACK_DATA)
    client.post(reverse("icts:proposal_submit", args=[proposal2.pk]), ACK_DATA)

    proposal1.refresh_from_db()
    proposal2.refresh_from_db()

    assert proposal1.user_sequence_number == 1
    assert proposal2.user_sequence_number == 2

    for proposal, seq in ((proposal1, 1), (proposal2, 2)):
        assert proposal.submitted_at is not None
        mm = proposal.submitted_at.strftime("%m")
        yy = proposal.submitted_at.strftime("%y")
        assert f"_{mm}_{yy}_{seq}" in proposal.access_code

    assert proposal1.pk != proposal1.user_sequence_number
    assert proposal1.access_code.endswith(f"_{proposal1.user_sequence_number}")
    assert not proposal1.access_code.endswith(f"_{proposal1.pk}")


@pytest.mark.django_db
def test_access_code_excludes_olmat(client):
    user = _create_icts_user("bob", "bob@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="OLMAT",
        facility_sem=True,
        facility_olmat=True,
    )

    client.force_login(user)
    client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)

    proposal.refresh_from_db()
    assert "OLMAT" not in (proposal.access_code or "")
    assert "SEM" in proposal.access_code


@pytest.mark.django_db
def test_edit_preserves_facility_data_on_invalid_json(client):
    user = _create_icts_user("carol", "carol@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Draft",
        facility_sem=True,
        facility_data={"sem": {"sem_sample_1_name": "M1"}},
    )

    formset = ParticipantFormSet(instance=proposal)
    prefix = formset.prefix

    data = {
        "title": proposal.title,
        "scope": "",
        "is_new_request": "on",
        "previous_access": "",
        "applicant_is_different": "",
        "organization": "",
        "contact_person": "",
        "email": "",
        "phone": "",
        "project_name": "",
        "project_type": "",
        "funding_source": "",
        "start_year": "",
        "end_year": "",
        "previous_experiments": "",
        "references": "",
        "facility_sem": "on",
        "facility_data_json": "{not-json",
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-name": "Carol Example",
        f"{prefix}-0-center": "",
        f"{prefix}-0-address": "",
    }

    client.force_login(user)
    response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert response.status_code in {200, 302}

    proposal.refresh_from_db()
    assert proposal.facility_data == {"sem": {"sem_sample_1_name": "M1"}}
