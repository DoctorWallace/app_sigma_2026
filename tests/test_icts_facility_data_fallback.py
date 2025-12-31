import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


def _create_icts_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


def _base_proposal_payload(title: str):
    return {
        "title": title,
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
        "facility_sem": "",
        "facility_sem_fib": "",
        "facility_imp": "",
        "facility_sims": "",
        "facility_confocal": "",
        "facility_vdg": "",
        "facility_profilometer": "",
        "facility_olmat": "",
    }


def _add_single_participant(data, prefix: str):
    data.update({
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-name": "Solicitante Uno",
        f"{prefix}-0-center": "Centro Uno",
        f"{prefix}-0-address": "Direccion Uno",
    })


def _build_sem_payload(sample_id: str):
    return {
        "sem_sample_0_identification": sample_id,
        "sem_sample_0_name": "Sample SEM",
        "sem_sample_0_details": "Details SEM",
    }


def _build_sims_payload(sample_id: str):
    return {
        "sims_sample_0_identification": sample_id,
        "sims_sample_0_name": "Sample SIMS",
        "sims_sample_0_details": "Details SIMS",
    }


@pytest.mark.django_db
def test_create_fallback_uses_session_drafts_when_json_empty(client):
    user = _create_icts_user("fallback_new", "fallback_new@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix

    session = client.session
    session["technique_drafts"] = {
        "legacy": {
            "sem": _build_sem_payload("SEM-SESSION"),
            "sims": _build_sims_payload("SIMS-SESSION"),
        }
    }
    session.save()

    data = _base_proposal_payload("Draft")
    data.update({
        "facility_sem": "on",
        "facility_sims": "on",
        "facility_data_json": "{}",
    })
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_create"), data)
    assert post_response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    assert proposal.facility_data["sem"]["sem_sample_0_identification"] == "SEM-SESSION"
    assert proposal.facility_data["sims"]["sims_sample_0_identification"] == "SIMS-SESSION"


@pytest.mark.django_db
def test_edit_fallback_fills_missing_selected_techniques(client):
    user = _create_icts_user("fallback_edit", "fallback_edit@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Draft",
        facility_sem=True,
        facility_sims=True,
        status="draft",
    )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix

    session = client.session
    session["technique_drafts"] = {
        str(proposal.pk): {
            "sims": _build_sims_payload("SIMS-SESSION"),
        }
    }
    session.save()

    data = _base_proposal_payload(proposal.title)
    data.update({
        "facility_sem": "on",
        "facility_sims": "on",
        "facility_data_json": json.dumps({"sem": _build_sem_payload("SEM-JSON")}),
    })
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert post_response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.facility_data["sem"]["sem_sample_0_identification"] == "SEM-JSON"
    assert proposal.facility_data["sims"]["sims_sample_0_identification"] == "SIMS-SESSION"
