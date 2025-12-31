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


def _build_vdg_samples_payload():
    return {
        "vdg_experiment_description": "Experiment description",
        "vdg_sample_0_code": "VDG-001",
        "vdg_sample_0_material": "Material A",
        "vdg_sample_0_electron_fluence": "1e12",
        "vdg_sample_0_temperature": "25",
        "vdg_sample_0_atmosphere": "Vacuum",
        "vdg_sample_0_sample_size": "10x10",
        "vdg_sample_0_sample_geometry": "Plate",
        "vdg_sample_1_code": "VDG-002",
        "vdg_sample_1_material": "Material B",
        "vdg_sample_1_electron_fluence": "2e12",
        "vdg_sample_1_temperature": "30",
        "vdg_sample_1_atmosphere": "Argon",
        "vdg_sample_1_sample_size": "5x5",
        "vdg_sample_1_sample_geometry": "Disk",
        "vdg_sample_2_code": "VDG-003",
        "vdg_sample_2_material": "Material C",
        "vdg_sample_2_electron_fluence": "3e12",
        "vdg_sample_2_temperature": "35",
        "vdg_sample_2_atmosphere": "Nitrogen",
        "vdg_sample_2_sample_size": "2x2",
        "vdg_sample_2_sample_geometry": "Cube",
    }


@pytest.mark.django_db
def test_vdg_samples_persist_on_edit(client):
    user = _create_icts_user("vdg_edit", "vdg_edit@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Draft",
        facility_vdg=True,
        status="draft",
    )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix

    data = _base_proposal_payload(proposal.title)
    data.update({
        "facility_vdg": "on",
        "facility_data_json": json.dumps({"vdg": _build_vdg_samples_payload()}),
    })
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert post_response.status_code == 302

    proposal.refresh_from_db()
    vdg_data = proposal.facility_data.get("vdg", {})
    assert vdg_data.get("vdg_sample_0_code") == "VDG-001"
    assert vdg_data.get("vdg_sample_2_code") == "VDG-003"

    edit_response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    content = edit_response.content.decode()
    assert "vdg_sample_2_code" in content
