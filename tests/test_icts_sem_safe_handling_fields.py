import json
import re

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


def _assert_checkbox(content: str, name: str):
    checkbox_pattern = re.compile(
        r'<input(?=[^>]*\bname="%s")(?=[^>]*\btype="checkbox")[^>]*>'
        % re.escape(name),
        re.IGNORECASE,
    )
    text_pattern = re.compile(
        r'<input(?=[^>]*\bname="%s")(?=[^>]*\btype="text")[^>]*>'
        % re.escape(name),
        re.IGNORECASE,
    )
    assert checkbox_pattern.search(content), f"Expected checkbox for {name}"
    assert not text_pattern.search(content), f"Did not expect text input for {name}"


@pytest.mark.django_db
def test_sem_safe_handling_fields_are_checkboxes(client):
    user = _create_icts_user("sem_checkboxes", "sem_checkboxes@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))

    assert response.status_code == 200
    content = response.content.decode("utf-8", errors="ignore")
    _assert_checkbox(content, "sem_toxic")
    _assert_checkbox(content, "sem_corrosive")
    _assert_checkbox(content, "sem_irritating")
    _assert_checkbox(content, "sem_radioactive")


@pytest.mark.django_db
def test_sem_safe_handling_values_persist(client):
    user = _create_icts_user("sem_persist", "sem_persist@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))
    prefix = response.context["formset"].prefix
    attachment_prefix = response.context["attachment_formset"].prefix

    facility_data = {
        "sem": {
            "sem_toxic": True,
            "sem_corrosive": True,
            "sem_irritating": False,
            "sem_radioactive": True,
        },
    }

    data = _base_proposal_payload("SEM Safe Handling Draft")
    data.update({
        "facility_sem": "on",
        "facility_data_json": json.dumps(facility_data),
    })
    _add_single_participant(data, prefix)
    _add_attachment_mgmt(data, attachment_prefix)

    post_response = client.post(reverse("icts:proposal_create"), data)
    assert post_response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    payload = proposal.facility_data["sem"]
    assert payload["sem_toxic"] is True
    assert payload["sem_corrosive"] is True
    assert payload["sem_irritating"] is False
    assert payload["sem_radioactive"] is True
