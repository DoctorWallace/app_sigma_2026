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


def _add_attachment_mgmt(data, prefix: str):
    data.update({
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    })


def _build_imp_facility_data(overrides=None):
    payload = {
        "imp_species": ["he", "d"],
        "imp_energy_keV": "20",
        "imp_fluence_ion_cm2": "1e15",
        "imp_temperature_C": "25",
        "imp_chamber": "small_area",
        "imp_sample_diameter_mm": "10",
        "imp_sample_thickness_mm": "1",
        "imp_sample_0_identification": "IMP-001",
        "imp_sample_0_name": "Sample A",
        "imp_sample_0_details": "Details",
    }
    if overrides:
        payload.update(overrides)
    return {"imp": payload}


def _post_imp_payload(client, user, facility_data):
    client.force_login(user)
    response = client.get(reverse("icts:proposal_create"))
    prefix = response.context["formset"].prefix
    attachment_prefix = response.context["attachment_formset"].prefix

    data = _base_proposal_payload("Imp test")
    data.update({
        "facility_imp": "on",
        "facility_data_json": json.dumps(facility_data),
    })
    _add_single_participant(data, prefix)
    _add_attachment_mgmt(data, attachment_prefix)
    return client.post(reverse("icts:proposal_create"), data)


@pytest.mark.django_db
def test_imp_species_persisted_on_create(client):
    user = _create_icts_user("imp_user", "imp_user@example.com")
    response = _post_imp_payload(client, user, _build_imp_facility_data())
    assert response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    assert proposal.facility_imp is True
    assert proposal.facility_data["imp"]["imp_species"] == ["he", "d"]


@pytest.mark.django_db
def test_imp_requires_species(client):
    user = _create_icts_user("imp_missing", "imp_missing@example.com")
    facility_data = _build_imp_facility_data({"imp_species": []})
    response = _post_imp_payload(client, user, facility_data)

    assert response.status_code == 302
    proposal = AccessProposal.objects.get(applicant=user)
    client.force_login(user)
    submit_response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))
    assert submit_response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_imp_requires_sample_identification(client):
    user = _create_icts_user("imp_sample_missing", "imp_sample_missing@example.com")
    facility_data = _build_imp_facility_data({"imp_sample_0_identification": ""})
    response = _post_imp_payload(client, user, facility_data)

    assert response.status_code == 302
    proposal = AccessProposal.objects.get(applicant=user)
    client.force_login(user)
    submit_response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))
    assert submit_response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_imp_temperature_out_of_range(client):
    user = _create_icts_user("imp_temp", "imp_temp@example.com")
    facility_data = _build_imp_facility_data({"imp_temperature_C": "650"})
    response = _post_imp_payload(client, user, facility_data)

    assert response.status_code == 302
    proposal = AccessProposal.objects.get(applicant=user)
    client.force_login(user)
    submit_response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))
    assert submit_response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_imp_large_area_requires_room_temperature(client):
    user = _create_icts_user("imp_large", "imp_large@example.com")
    facility_data = _build_imp_facility_data({
        "imp_chamber": "large_area",
        "imp_temperature_C": "45",
    })
    response = _post_imp_payload(client, user, facility_data)

    assert response.status_code == 302
    proposal = AccessProposal.objects.get(applicant=user)
    client.force_login(user)
    submit_response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]))
    assert submit_response.status_code == 302
    proposal.refresh_from_db()
    assert proposal.status == "draft"
