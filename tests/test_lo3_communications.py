import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from sigmaconf.models import LO3Conversation, MCFSession, MCFSampleRecord


def _create_user(username, groups=None):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups or []:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_icts_session(client):
    session = client.session
    session["module"] = "icts"
    session.save()


@pytest.mark.django_db
def test_lo3_communications_permissions(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_applicant_msg", ["icts_users"])
    technician = _create_user("lo3_tech_msg", ["confocal_technicians"])
    other_user = _create_user("lo3_other_msg", ["icts_users"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="LO3 Proposal",
        status="accepted",
        facility_confocal=True,
        access_code="ACC-LO3-003",
        facility_data={},
    )

    detail_url = reverse("sigmaconf:lo3_communications_detail", args=[proposal.pk])

    client.force_login(applicant)
    _set_icts_session(client)
    assert client.get(detail_url).status_code == 200

    client.force_login(technician)
    _set_icts_session(client)
    assert client.get(detail_url).status_code == 200

    client.force_login(other_user)
    _set_icts_session(client)
    assert client.get(detail_url).status_code == 403


@pytest.mark.django_db
def test_lo3_finish_session_creates_system_message(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_applicant_notice", ["icts_users"])
    technician = _create_user("lo3_tech_notice", ["confocal_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="LO3 Proposal",
        status="accepted",
        facility_confocal=True,
        access_code="ACC-LO3-004",
        facility_data={},
    )

    session = MCFSession.objects.create(access_proposal=proposal, technician=technician)
    MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        identification="S-001",
        analysis_date=timezone.now().date(),
        roughness=True,
    )

    client.force_login(technician)
    _set_icts_session(client)
    response = client.post(reverse("sigmaconf:mcf_finish_session", args=[session.pk]))
    assert response.status_code == 302

    conversation = LO3Conversation.objects.get(access_proposal=proposal)
    system_message = conversation.messages.filter(is_system=True).first()
    assert system_message is not None
    assert "Resultados" in system_message.body
    assert reverse("sigmaconf:lo3_results") in system_message.body
