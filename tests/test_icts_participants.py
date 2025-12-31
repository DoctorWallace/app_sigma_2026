import re

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal, Participant


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


@pytest.mark.django_db
def test_create_shows_single_participant_and_toggle_off(client):
    user = _create_icts_user("creator", "creator@example.com")
    client.force_login(user)

    response = client.get(reverse("icts:proposal_create"))
    assert response.status_code == 200

    formset = response.context["formset"]
    assert len(formset.forms) == 1
    assert response.context["participants_count"] == 1

    html = response.content.decode("utf-8")
    assert 'data-participants-count="1"' in html
    match = re.search(r'id="has-more-participants"[^>]*', html)
    assert match
    assert "checked" not in match.group(0)


@pytest.mark.django_db
def test_create_with_single_participant_creates_one_participant(client):
    user = _create_icts_user("submitter", "submitter@example.com")
    client.force_login(user)

    get_response = client.get(reverse("icts:proposal_create"))
    prefix = get_response.context["formset"].prefix
    attachment_prefix = get_response.context["attachment_formset"].prefix

    data = _base_proposal_payload("Propuesta simple")
    data.update({
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-name": "Solicitante Uno",
        f"{prefix}-0-center": "Centro Uno",
        f"{prefix}-0-address": "Direccion Uno",
        f"{attachment_prefix}-TOTAL_FORMS": "1",
        f"{attachment_prefix}-INITIAL_FORMS": "0",
        f"{attachment_prefix}-MIN_NUM_FORMS": "0",
        f"{attachment_prefix}-MAX_NUM_FORMS": "1000",
    })

    response = client.post(reverse("icts:proposal_create"), data)
    assert response.status_code == 302

    proposal = AccessProposal.objects.get(applicant=user)
    assert proposal.participants.count() == 1


@pytest.mark.django_db
def test_edit_toggle_off_deletes_extra_participants(client):
    user = _create_icts_user("editor", "editor@example.com")
    proposal = AccessProposal.objects.create(applicant=user, title="Draft")
    participant_1 = Participant.objects.create(
        proposal=proposal,
        name="Participante Uno",
        center="Centro Uno",
        address="Direccion Uno",
    )
    participant_2 = Participant.objects.create(
        proposal=proposal,
        name="Participante Dos",
        center="Centro Dos",
        address="Direccion Dos",
    )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert response.status_code == 200
    assert response.context["participants_count"] == 2

    prefix = response.context["formset"].prefix
    data = _base_proposal_payload(proposal.title)
    data.update({
        f"{prefix}-TOTAL_FORMS": "2",
        f"{prefix}-INITIAL_FORMS": "2",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-id": str(participant_1.pk),
        f"{prefix}-0-name": participant_1.name,
        f"{prefix}-0-center": participant_1.center,
        f"{prefix}-0-address": participant_1.address,
        f"{prefix}-1-id": str(participant_2.pk),
        f"{prefix}-1-name": participant_2.name,
        f"{prefix}-1-center": participant_2.center,
        f"{prefix}-1-address": participant_2.address,
        f"{prefix}-1-DELETE": "on",
    })

    post_response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert post_response.status_code in {200, 302}

    proposal.refresh_from_db()
    participants = list(proposal.participants.order_by("id"))
    assert len(participants) == 1
    assert participants[0].pk == participant_1.pk


@pytest.mark.django_db
def test_edit_updates_second_participant_without_duplicates(client):
    user = _create_icts_user("editor2", "editor2@example.com")
    proposal = AccessProposal.objects.create(applicant=user, title="Draft")
    participant_1 = Participant.objects.create(
        proposal=proposal,
        name="Participante Uno",
        center="Centro Uno",
        address="Direccion Uno",
    )
    participant_2 = Participant.objects.create(
        proposal=proposal,
        name="Participante Dos",
        center="Centro Dos",
        address="Direccion Dos",
    )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
    assert response.status_code == 200

    prefix = response.context["formset"].prefix
    data = _base_proposal_payload(proposal.title)
    data.update({
        f"{prefix}-TOTAL_FORMS": "2",
        f"{prefix}-INITIAL_FORMS": "2",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-id": str(participant_1.pk),
        f"{prefix}-0-name": participant_1.name,
        f"{prefix}-0-center": participant_1.center,
        f"{prefix}-0-address": participant_1.address,
        f"{prefix}-1-id": str(participant_2.pk),
        f"{prefix}-1-name": "Participante Dos Actualizado",
        f"{prefix}-1-center": participant_2.center,
        f"{prefix}-1-address": participant_2.address,
    })

    post_response = client.post(reverse("icts:proposal_edit", args=[proposal.pk]), data)
    assert post_response.status_code in {200, 302}

    proposal.refresh_from_db()
    participants = list(proposal.participants.order_by("id"))
    assert len(participants) == 2
    assert participants[1].pk == participant_2.pk
    assert participants[1].name == "Participante Dos Actualizado"
