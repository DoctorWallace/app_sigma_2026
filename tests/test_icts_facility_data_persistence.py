import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.forms import ParticipantFormSet
from icts.models import AccessProposal


def _create_icts_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_proposal_create_has_single_participant_form(client):
    user = _create_icts_user("creator", "creator@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))

    assert response.status_code == 200
    formset = response.context["formset"]
    assert formset.total_form_count() == 1
    assert response.context["participants_count"] == 1


@pytest.mark.django_db
def test_proposal_edit_allows_clearing_facility_data(client):
    user = _create_icts_user("editor", "editor@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Draft",
        facility_sem=True,
        facility_data={"sem": {"sem_sample_1_name": "M1"}},
    )

    formset = ParticipantFormSet(instance=proposal)
    prefix = formset.prefix

    client.force_login(user)
    get_response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert get_response.status_code == 200
    attachment_prefix = get_response.context["attachment_formset"].prefix

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
        "facility_data_json": "{}",
        "facilities": [],
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-name": "Editor Example",
        f"{prefix}-0-center": "",
        f"{prefix}-0-address": "",
        f"{attachment_prefix}-TOTAL_FORMS": "1",
        f"{attachment_prefix}-INITIAL_FORMS": "0",
        f"{attachment_prefix}-MIN_NUM_FORMS": "0",
        f"{attachment_prefix}-MAX_NUM_FORMS": "1000",
    }
    response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert response.status_code in {200, 302}

    proposal.refresh_from_db()
    assert proposal.facility_data == {}


@pytest.mark.django_db
def test_proposal_detail_handles_olmat_arrays(client):
    user = _create_icts_user("olmatuser", "olmat@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="OLMAT Only",
        facility_olmat=True,
        facility_data={
            "olmat": {
                "olmat_diagnostics": ["diag-a", "diag-b"],
                "olmat_sample_prep": ["prep-a"],
                "olmat_beam_usage": ["beam-a"],
            }
        },
    )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_detail", args=[proposal.pk]))

    assert response.status_code == 200
    assert response.context["facility_data_view"] == []
    assert "olmat" in (response.context["facility_data_raw"] or "")
