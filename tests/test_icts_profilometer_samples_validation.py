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
        "scope": "Scope text",
        "is_new_request": "on",
        "previous_access": "",
        "applicant_is_different": "",
        "organization": "",
        "contact_person": "",
        "email": "",
        "phone": "",
        "project_name": "Project A",
        "project_type": "national",
        "funding_source": "Grant A",
        "start_year": "2024",
        "end_year": "2024",
        "previous_experiments": "Previous experiments",
        "references": "Reference list",
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


def _add_attachment_mgmt(data, prefix: str):
    data.update({
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    })


def _build_profilometer_facility_data(overrides=None):
    payload = {
        "profilometer_num_samples": "2",
        "profilometer_range_um": "10",
        "profilometer_resolution_nm": "1",
        "profilometer_sample_0_id": "PROF-001",
        "profilometer_sample_0_name": "Sample 1",
        "profilometer_sample_0_details": "Details 1",
        "profilometer_sample_1_id": "PROF-002",
        "profilometer_sample_1_name": "Sample 2",
        "profilometer_sample_1_details": "Details 2",
    }
    if overrides:
        payload.update(overrides)
    return {"profilometer": payload}


def _post_profilometer_payload(client, user, facility_data):
    client.force_login(user)
    response = client.get(reverse("icts:proposal_create"))
    prefix = response.context["formset"].prefix
    attachment_prefix = response.context["attachment_formset"].prefix

    data = _base_proposal_payload("Profilometer Draft")
    data.update({
        "facility_profilometer": "on",
        "facility_data_json": json.dumps(facility_data),
    })
    _add_single_participant(data, prefix)
    _add_attachment_mgmt(data, attachment_prefix)
    return client.post(reverse("icts:proposal_create"), data)


@pytest.mark.django_db
def test_profilometer_missing_sample_name_blocks_submit(client):
    user = _create_icts_user("profilometer_missing", "profilometer_missing@example.com")
    facility_data = _build_profilometer_facility_data({"profilometer_sample_1_name": ""})
    response = _post_profilometer_payload(client, user, facility_data)
    assert response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    client.force_login(user)
    submit_response = client.post(
        reverse("icts:proposal_submit", args=[proposal.pk]),
        follow=True,
    )

    assert submit_response.status_code == 200
    content = submit_response.content.decode("utf-8", errors="ignore")
    assert "Profilometer: sample 2 requires ID and name." in content
    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_profilometer_submit_with_samples_succeeds(client):
    user = _create_icts_user("profilometer_ok", "profilometer_ok@example.com")
    facility_data = _build_profilometer_facility_data()
    response = _post_profilometer_payload(client, user, facility_data)
    assert response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    client.force_login(user)
    submit_response = client.post(
        reverse("icts:proposal_submit", args=[proposal.pk]),
        follow=True,
    )

    assert submit_response.status_code == 200
    proposal.refresh_from_db()
    assert proposal.status == "submitted"
    payload = proposal.facility_data["profilometer"]
    assert payload["profilometer_sample_0_id"] == "PROF-001"
    assert payload["profilometer_sample_0_name"] == "Sample 1"
    assert payload["profilometer_sample_1_id"] == "PROF-002"
    assert payload["profilometer_sample_1_name"] == "Sample 2"
