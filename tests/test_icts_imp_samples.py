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


def _build_imp_samples_payload():
    return {
        "imp_species": ["he"],
        "imp_energy_keV": "20",
        "imp_fluence_ion_cm2": "1e15",
        "imp_temperature_C": "25",
        "imp_chamber": "small_area",
        "imp_sample_diameter_mm": "10",
        "imp_sample_thickness_mm": "1",
        "imp_sample_0_identification": "IMP-001",
        "imp_sample_0_name": "Sample A",
        "imp_sample_0_details": "Details A",
        "imp_sample_1_identification": "IMP-002",
        "imp_sample_1_name": "Sample B",
        "imp_sample_1_details": "Details B",
    }


@pytest.mark.django_db
def test_imp_samples_persist_on_edit(client):
    user = _create_icts_user("imp_edit", "imp_edit@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Draft",
        facility_imp=True,
        status="draft",
    )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix
    attachment_prefix = response.context["attachment_formset"].prefix

    data = _base_proposal_payload(proposal.title)
    data.update({
        "facility_imp": "on",
        "facility_data_json": json.dumps({"imp": _build_imp_samples_payload()}),
    })
    _add_single_participant(data, prefix)
    _add_attachment_mgmt(data, attachment_prefix)

    post_response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert post_response.status_code == 302

    proposal.refresh_from_db()
    imp_data = proposal.facility_data.get("imp", {})
    assert imp_data.get("imp_sample_0_identification") == "IMP-001"
    assert imp_data.get("imp_sample_1_identification") == "IMP-002"
