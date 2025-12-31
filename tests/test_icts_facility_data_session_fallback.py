# tests/test_icts_facility_data_session_fallback.py
import hashlib
import json

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


def _slug(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


def _create_icts_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


def _base_proposal_payload(title: str):
    # Payload mínimo que tu AccessProposalForm + ParticipantFormSet aceptan
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
    body = response.json()
    assert body.get("success") is True


# Casos con: (tech_key, field_checkbox_propuesta, draft, sample_key, sample_value, checkbox_key_a_proteger)
TECH_CASES = [
    (
        "sem",
        "facility_sem",
        {
            "sem_sample_0_identification": "SEM-001",
            "sem_sample_0_name": "Sample A",
            "sem_sample_0_details": "Details A",
            "sem_analysis_request": True,  # checkbox crítico (solicitud)
        },
        "sem_sample_0_identification",
        "SEM-001",
        "sem_analysis_request",
    ),
    (
        "fib",
        "facility_sem_fib",
        {
            "fib_sample_0_identification": "FIB-001",
            "fib_sample_0_name": "Sample A",
            "fib_sample_0_details": "Details A",
            "fib_specific_area": True,  # checkbox crítico
        },
        "fib_sample_0_identification",
        "FIB-001",
        "fib_specific_area",
    ),
    (
        "sims",
        "facility_sims",
        {
            "sims_sample_0_identification": "SIMS-001",
            "sims_sample_0_name": "Sample A",
            "sims_sample_0_details": "Details A",
            "sims_surface_analysis": True,  # checkbox crítico
        },
        "sims_sample_0_identification",
        "SIMS-001",
        "sims_surface_analysis",
    ),
    (
        "confocal",
        "facility_confocal",
        {
            "confocal_sample_0_identification": "CONF-001",
            "confocal_sample_0_name": "Sample A",
            "confocal_sample_0_details": "Details A",
            "confocal_2d_analysis": True,  # checkbox crítico
        },
        "confocal_sample_0_identification",
        "CONF-001",
        "confocal_2d_analysis",
    ),
]


@pytest.mark.django_db
@pytest.mark.parametrize("tech,facility_field,draft,sample_key,sample_value,checkbox_key", TECH_CASES)
@pytest.mark.parametrize("bad_facility_json", ["{}", "", "undefined"])
def test_proposal_create_uses_session_draft_when_facility_data_json_is_unusable(
    client,
    tech,
    facility_field,
    draft,
    sample_key,
    sample_value,
    checkbox_key,
    bad_facility_json,
):
    """
    Flujo real:
    1) Usuario guarda técnica (Add Technique) -> /save-technique-draft/ (session)
    2) Al guardar la propuesta, facility_data_json llega roto/vacío

    Requisito: backend debe recuperar el draft de sesión y persistirlo en AccessProposal.facility_data.
    """
    username = f"{tech}_create_{_slug(bad_facility_json)}"
    user = _create_icts_user(username, f"{username}@example.com")
    client.force_login(user)

    # Simula create: la UI manda proposal_id=None -> bucket "legacy"
    _save_technique_draft(client, tech, draft, proposal_id=None)

    # Prefijo real del formset (no asumir "participant_set")
    get_response = client.get(reverse("icts:proposal_create"))
    assert get_response.status_code == 200
    prefix = get_response.context["formset"].prefix

    title = f"Draft {tech} session fallback ({bad_facility_json})"
    data = _base_proposal_payload(title)
    data.update(
        {
            facility_field: "on",
            "facility_data_json": bad_facility_json,  # simula JS roto
        }
    )
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_create"), data)
    assert post_response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user, title=title)
    tech_data = proposal.facility_data.get(tech, {})
    assert tech_data.get(sample_key) == sample_value
    assert tech_data.get(checkbox_key) is True


@pytest.mark.django_db
@pytest.mark.parametrize("tech,facility_field,draft,sample_key,sample_value,checkbox_key", TECH_CASES)
def test_proposal_edit_prefers_session_draft_over_client_payload_for_checkboxes(
    client,
    tech,
    facility_field,
    draft,
    sample_key,
    sample_value,
    checkbox_key,
):
    """
    Reproduce el bug “mezcla con defaults del modal”:

    - draft en sesión: checkbox_key=True
    - facility_data_json recibido: checkbox_key=False

    Requisito: si existe draft de sesión para esa técnica, DEBE prevalecer (evitar pérdida silenciosa).
    """
    username = f"{tech}_edit_{_slug(checkbox_key)}"
    user = _create_icts_user(username, f"{username}@example.com")

    proposal_kwargs = {
        "applicant": user,
        "title": "Draft",
        "status": "draft",
        facility_field: True,
    }
    proposal = AccessProposal.objects.create(**proposal_kwargs)

    client.force_login(user)

    # Draft correcto en sesión bajo el bucket de proposal_id
    _save_technique_draft(client, tech, draft, proposal_id=proposal.pk)

    # Prefijo real del formset
    response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert response.status_code == 200
    prefix = response.context["formset"].prefix

    data = _base_proposal_payload(proposal.title)
    data.update(
        {
            facility_field: "on",
            # Simula payload defectuoso: viene False aunque el draft guardado es True
            "facility_data_json": json.dumps(
                {
                    tech: {
                        sample_key: sample_value,
                        checkbox_key: False,
                    }
                }
            ),
        }
    )
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert post_response.status_code == 302

    proposal.refresh_from_db()
    tech_data = proposal.facility_data.get(tech, {})
    assert tech_data.get(sample_key) == sample_value
    assert tech_data.get(checkbox_key) is True


@pytest.mark.django_db
def test_session_draft_is_not_restored_if_technique_unchecked(client):
    """
    Garantiza que la solución NO reinyecta datos si el usuario desmarca la técnica.
    (Importante para poder "quitar" una técnica sin que el draft de sesión la resucite.)
    """
    user = _create_icts_user("sem_unchecked", "sem_unchecked@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Draft",
        facility_sem=True,
        status="draft",
        facility_data={"sem": {"sem_sample_0_identification": "OLD"}},
    )
    client.force_login(user)

    # Hay draft en sesión, pero el usuario desmarca la técnica al guardar
    _save_technique_draft(
        client,
        "sem",
        {"sem_sample_0_identification": "SEM-NEW", "sem_analysis_request": True},
        proposal_id=proposal.pk,
    )

    response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    prefix = response.context["formset"].prefix

    data = _base_proposal_payload(proposal.title)
    data.update(
        {
            # Importante: NO marcamos facility_sem -> queda desmarcada
            "facility_data_json": "{}",
        }
    )
    _add_single_participant(data, prefix)

    post_response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert post_response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.facility_sem is False
    assert proposal.facility_data == {}
