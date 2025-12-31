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


def _build_sem_payload():
    return {
        "sem_sample_0_identification": "SEM-001",
        "sem_sample_0_name": "Sample A",
        "sem_sample_0_details": "Details A",
        "sem_sample_1_identification": "SEM-002",
        "sem_sample_1_name": "Sample B",
        "sem_sample_1_details": "Details B",
        "sem_analysis_request": True,
    }


def _build_fib_payload():
    return {
        "fib_sample_0_identification": "FIB-001",
        "fib_sample_0_name": "Sample F",
        "fib_sample_0_details": "Details F",
        "fib_sample_conductive": True,
    }


@pytest.mark.django_db
def test_create_multi_technique_samples_rehydrate(client):
    user = _create_icts_user("multi_tech", "multi_tech@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix

    data = _base_proposal_payload("Multi Tech Draft")
    data.update({
        "facility_sem": "on",
        "facility_sem_fib": "on",
        "facility_data_json": json.dumps({
            "sem": _build_sem_payload(),
            "fib": _build_fib_payload(),
        }),
    })
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_create"), data)
    assert post_response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    assert proposal.facility_data["sem"]["sem_sample_1_identification"] == "SEM-002"
    assert proposal.facility_data["fib"]["fib_sample_0_identification"] == "FIB-001"
    assert proposal.facility_data["sem"]["sem_analysis_request"] is True
    assert proposal.facility_data["fib"]["fib_sample_conductive"] is True

    edit_response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    content = edit_response.content.decode()
    assert "sem_sample_1_identification" in content
    assert "fib_sample_0_identification" in content
