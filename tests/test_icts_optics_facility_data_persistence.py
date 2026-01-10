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
        "facility_optics": "",
        "facility_vdg": "",
        "facility_profilometer": "",
        "facility_olmat": "",
    }


def _add_single_participant(data, prefix: str):
    data.update(
        {
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-name": "Solicitante Uno",
            f"{prefix}-0-center": "Centro Uno",
            f"{prefix}-0-address": "Direccion Uno",
        }
    )


def _build_optics_payload():
    """Payload mínimo coherente con PT-DTF-07 para persistencia (no para submit)."""
    return {
        "optics_sample_0_identification": "OPT-001",
        "optics_sample_0_name": "Sample A",
        "optics_sample_0_observations": "Surface OK",
        "optics_measurement_mode": "absorption",
        "optics_wavelength_min": "1000",
        "optics_wavelength_min_unit": "nm",
        "optics_wavelength_max": "4000",
        "optics_wavelength_max_unit": "nm",
        "optics_measurement_type": "ftir",
        "optics_comments": "Test",
    }


@pytest.mark.django_db
def test_create_optics_persists_facility_data_and_renders_on_edit(client):
    user = _create_icts_user("optics_creator", "optics_creator@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix

    data = _base_proposal_payload("Optics draft")
    data.update(
        {
            "facility_optics": "on",
            "facility_data_json": json.dumps({"optics": _build_optics_payload()}),
        }
    )
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_create"), data)
    assert post_response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    assert proposal.facility_optics is True
    assert proposal.facility_data.get("optics", {}).get("optics_sample_0_identification") == "OPT-001"
    assert proposal.facility_data.get("optics", {}).get("optics_measurement_type") == "ftir"

    edit_response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert edit_response.status_code == 200
    html = edit_response.content.decode()
    assert "optics_sample_0_identification" in html
    assert "optics_wavelength_min" in html


@pytest.mark.django_db
def test_create_filters_out_optics_payload_when_optics_not_selected(client):
    """If the user did not tick Optics, any optics JSON in facility_data_json must be ignored."""
    user = _create_icts_user("optics_filter", "optics_filter@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix

    data = _base_proposal_payload("No optics")
    data.update(
        {
            # IMPORTANT: do NOT set facility_optics
            "facility_data_json": json.dumps({"optics": _build_optics_payload()}),
        }
    )
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_create"), data)
    assert post_response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    assert proposal.facility_optics is False
    assert "optics" not in (proposal.facility_data or {})
