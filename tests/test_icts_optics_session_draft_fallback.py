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


def _save_technique_draft(client, technique: str, form_data: dict, proposal_id=None):
    payload = {
        "technique": technique,
        "form_data": form_data,
        "proposal_id": proposal_id,
    }
    response = client.post(
        reverse("icts:save_technique_draft"),
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json().get("success") is True


@pytest.mark.django_db
def test_optics_session_draft_is_used_when_facility_data_json_is_broken(client):
    """If the frontend sends a broken facility_data_json, the backend must rehydrate from session."""
    user = _create_icts_user("optics_session", "optics_session@example.com")
    client.force_login(user)

    draft = {
        "optics_sample_0_identification": "OPT-SESSION-001",
        "optics_sample_0_name": "Sample Session",
        "optics_measurement_mode": "absorption",
        "optics_wavelength_min": "1000",
        "optics_wavelength_min_unit": "nm",
        "optics_wavelength_max": "4000",
        "optics_wavelength_max_unit": "nm",
        "optics_measurement_type": "ftir",
    }

    # Simula el modal guardando el draft en sesión para proposal_id=None -> bucket "legacy"
    _save_technique_draft(client, "optics", draft, proposal_id=None)

    # Prefijo real del ParticipantFormSet
    get_response = client.get(reverse("icts:proposal_create"))
    assert get_response.status_code == 200
    prefix = get_response.context["formset"].prefix

    data = {
        "title": "Optics session fallback",
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
        "facility_optics": "on",
        # Simula JS roto
        "facility_data_json": "{not-json",
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-name": "Solicitante Uno",
        f"{prefix}-0-center": "Centro Uno",
        f"{prefix}-0-address": "Direccion Uno",
    }

    post_response = client.post(reverse("icts:proposal_create"), data)
    assert post_response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user, title="Optics session fallback")
    assert proposal.facility_optics is True
    optics_data = proposal.facility_data.get("optics", {})
    assert optics_data.get("optics_sample_0_identification") == "OPT-SESSION-001"
    assert optics_data.get("optics_measurement_type") == "ftir"
